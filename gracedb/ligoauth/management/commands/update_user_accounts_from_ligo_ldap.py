from builtins import str
import datetime
import ldap
import pytz
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ligoauth.models import X509Cert, AuthGroup, \
                            AuthorizedLdapMember, GenericLdapUser

from events.models import Event, EventLog
from superevents.models import Log
from alerts.models import Notification

# Turn on x-ray tracing for improved performance in AWS
try:
    from aws_xray_sdk.core import xray_recorder
    xray_recorder.begin_segment("ldap-user-account-segment")
except ModuleNotFoundError:
    print("aws_xray_sdk not found, skipping.")

UserModel = get_user_model()


# Classes for processing LDAP results into user accounts ----------------------
class LdapPersonResultProcessor:
    stdout = None

    def __init__(self, ldap_dn, ldap_result, ldap_connection=None,
        verbose=True, stdout=None, 
        ldap_member_name='Communities:LSCVirgoLIGOGroupMembers', 
        *args, **kwargs):
        self.ldap_dn = ldap_dn
        self.ldap_result = ldap_result
        self.verbose = verbose
        self.ldap_connection = ldap_connection
        self.stdout = stdout

        # the LVC authorized ldap membership:
        self.ldap_member_name = ldap_member_name
        self.ldap_authmember = AuthorizedLdapMember.objects.get(ldap_gname=ldap_member_name)

        # Get the set of AuthGroups that do not have a null set of AuthorizedLdapMember
        # objects, i.e., ones that get that identity from an ldap request.
        self.validauthgroup_set = AuthGroup.objects.exclude(authorizedldapmember__isnull=True)


    def write(self, message):
        if self.stdout:
            self.stdout.write(message)
        else:
            print(message)

    def extract_user_attributes(self):
        if self.ldap_connection is None:
            raise RuntimeError('LDAP connection not configured')
        memberships = [group_name.decode('utf-8') for group_name in
            self.ldap_result.get('isMemberOf', [])]
        self.ldap_memberships = AuthorizedLdapMember.objects.filter(ldap_gname__in=
                    memberships)
        self.user_data = {
            'first_name': self.ldap_result['givenName'][0].decode('utf-8'),
            'last_name': self.ldap_result['sn'][0].decode('utf-8'),
            'email': self.ldap_result['mail'][0].decode('utf-8'),
            'is_active': bool(self.ldap_connection.lvc_group.authorizedldapmember_set.all() &
                              self.ldap_memberships),
            'username': self.ldap_result['krbPrincipalName'][0].decode('utf-8').lower(),
        }

    def check_situation(self, user_exists, l_user_exists):
        pass

    def get_or_create_user(self):

        if not hasattr(self, 'user_data'):
            self.extract_user_attributes()

        # Kagra members used to use the the 'mail' ldap attribute as a username, 
        # to be consistent with LIGO members. However, for scitokens, a kagra user's
        # eppn is used in the same field as a ligo member's @ligo.org email. So, 
        # if the eppn attribute exists from the ldap data (which is only polled for
        # kagra, not ligo), check for a user with the email, if it exists, then change
        # the user's username. If not, then do nothing to the user, but change the 'username'
        # user_data attribute either way. This is kind of hacky, but in theory this should 
        # only actually run once. 

        # This loop is only for kagra folks, as it's set up:
        if 'eduPersonPrincipalName' in self.ldap_result.keys():
            # Check for an existing user whose username is their email:
            kagra_user = UserModel.objects.filter(username=
                    self.user_data['email'])
            # If there are results, pick the first and only one (since it has to be
            # unique by definition)
            if kagra_user.exists():
                kagra_user = kagra_user.first()
                # Now, is that person a member of kagra? and are we sure we're dealing with
                # KAGRA? 

                # Three conditions: 
                #  1) Is the user a kagra genericldapuser?
                #  2) Is that they only a kagra genericldapuser?
                #  3) Are we in fact dealing with the KAGRA ldap (sanity check)

                if (kagra_user.genericldapuser_set.filter(ldap_member=self.ldap_authmember) and
                   not kagra_user.genericldapuser_set.exclude(ldap_member=self.ldap_authmember) and
                   self.ldap_authmember.name=='KAGRA'):

                    # Now, check if the name should be changed, and if so, change it
                    if kagra_user.username != self.user_data['username']:
                        print("changing username of {} to {}".format(
                            kagra_user.username, self.user_data['username']))
                        kagra_user.username = self.user_data['username']
                        kagra_user.save()

        # Determine if users exist
        user_exists = UserModel.objects.filter(username=
            self.user_data['username'].lower()).exists()
        l_user_exists = GenericLdapUser.objects.filter(
            ldap_dn=self.ldap_dn).exists()


        # Run any necessary checks at this point
        self.check_situation(user_exists, l_user_exists)

        # Handle different cases
        self.user_created = False
        if l_user_exists:
            # GenericLdapUser exists already (and thus, User object exists too)
            l_user = GenericLdapUser.objects.get(ldap_dn=self.ldap_dn)
            user = l_user.user
        else:
            # GenericLdapUser doesn't exist
            if user_exists:
                # User object exists, though, so we have to carefully create
                # the GenericLdapUser object
                user = UserModel.objects.get(username=
                    self.user_data['username'].lower())
                l_user, created = GenericLdapUser.objects.get_or_create(ldap_dn=self.ldap_dn,
                                         ldap_member=self.ldap_authmember,
                                         user=user)
                if (created and self.verbose):
                    self.write("Created genericldapuser for {0}".format(
                        user.username))
            else:
                # No User object either, so we do a simple creation
                user = UserModel(**self.user_data)
                user.save()
                l_user, created = GenericLdapUser.objects.get_or_create(ldap_dn=self.ldap_dn,
                                         ldap_member=self.ldap_authmember,
                                         user=user)
                if (created and self.verbose):
                    self.write("Created user and ligoldapuser for {0}".format(
                    user.username))
                self.user_created = True

        # Attach some information to this instance
        self.ligoldapuser = l_user
        self.user = user
        self.l_user_exists = l_user_exists
        self.user_exists = user_exists

        self.check_user_accounts()

    def check_user_accounts(self):
        if not (hasattr(self, 'user_data') or hasattr(self, 'user')):
            raise RuntimeError('User data or user object missing')
        # Ran into problems with case of emails and usernames, ex:
        # "...@LIGO.org" vs "...@ligo.org". This performs a case-insensitive
        # comparison to compare the DB entry and the user_data from the ldap.
        # Note this is legit because gracedb ignores case for usernames specifically. 
        if (self.user.username.lower() != self.user_data['username'].lower() and
            self.user_exists):
            self.write(('ERROR: requires manual investigation. LDAP '
                'username: {0}, ligoldapuser.user_ptr.username: {1}')
                .format(self.user_data['username'],
                self.ligoldapuser.user.username))
            raise self.UserConfigError('User configuration error')

    def update_user(self):
        if not hasattr(self, 'user'):
            raise RuntimeError('User object missing')
        self.update_user_attributes()
        self.update_user_groups()
        self.update_user_certificates()

    def get_attributes_to_update(self):
        attributes_to_update = [k for k,v in self.user_data.items()
            if v != getattr(self.ligoldapuser.user, k)]
        return attributes_to_update

    def update_user_attributes(self):
        self.user_changed = False

        # Don't do anything if the user was just created
        if self.user_created:
            return

        # Update attributes
        attributes_to_update = self.get_attributes_to_update()
        if attributes_to_update:
            self.user_changed = True
        for k in attributes_to_update:
            setattr(self.ligoldapuser.user, k, self.user_data[k])

        # Revoke staff/superuser if not active.
        if ((self.ligoldapuser.user.is_staff or self.ligoldapuser.user.is_superuser)
            and not self.user_data['is_active']):
            self.ligoldapuser.user.is_staff = self.ligoldapuser.user.is_superuser = False
            self.user_changed = True

        if self.user_changed and self.verbose:
            self.write("User {0} updated".format(self.ligoldapuser.user.username))

        # Add tzinfo to native datetimes for last_login:
        if self.ligoldapuser.user.last_login:
            if not self.ligoldapuser.user.last_login.tzinfo:
                self.ligoldapuser.user.last_login = pytz.utc.localize(
                        self.ligoldapuser.user.last_login)

        # Add tzinfo to native datetimes for date_joined:
        if self.ligoldapuser.user.date_joined:
            if not self.ligoldapuser.user.date_joined.tzinfo:
                self.ligoldapuser.user.date_joined = pytz.utc.localize(
                        self.ligoldapuser.user.date_joined)

        self.ligoldapuser.user.save()

    def update_user_groups(self):
        # Get list of group names that the user belongs to from the LDAP result
        memberships = [group_name.decode('utf-8') for group_name in
            self.ldap_result.get('isMemberOf', [])]

        # Get groups which are listed for the user in the LDAP and whose
        # membership is controlled by the LDAP
        ldap_group_ids = self.ldap_memberships.values_list('id')
        session_groups = self.validauthgroup_set.filter(authorizedldapmember__in=ldap_group_ids)

        # Add the user to these groups
        if self.verbose and session_groups.exclude(id__in=self.ligoldapuser.user.groups.all()).exists():
            self.write("Adding {0} to {1}".format(self.ligoldapuser.user.username,
                " and ".join(list(session_groups.values_list(
                'name', flat=True)))))
        self.user.groups.add(*session_groups)

        # Get groups which are *not* listed for the user in the LDAP and whose
        # membership is controlled by the LDAP. First, get the set of groups that 
        # are ldap-controlled and currently in the user's group set. In other words, 
        # don't consider non-ldap groups like 'executives'.

        # Note: this has to be updated to exclude groups from other ldaps. So that 
        # updating from kagra doesn't take out em_advocates, for instance. 

        ldap_groups_in_user_set = self.validauthgroup_set.filter(id__in=self.ligoldapuser.user.groups.all())

        # Next get a list of groups to remove. So, the list of ldap groups in the set 
        # that are not currently in session_groups.

        ldap_groups_to_remove = ldap_groups_in_user_set.exclude(id__in=session_groups)

       # Remove the user from these groups
        if self.verbose and ldap_groups_to_remove.exists():
            self.write("Removing {0} from {1}".format(
                self.ligoldapuser.user.username,
                " and ".join(list(ldap_groups_to_remove.values_list(
                'name', flat=True)))))
        self.ligoldapuser.user.groups.remove(*ldap_groups_to_remove)

    def add_certs(self, certs):
        # Add new certificates to user
        for subject in certs:
            # Check if certificate already exists (sometimes certificates
            # are assigned to different users); if so, we just change the
            # user rather than creating a new certificate
            cert = X509Cert.objects.filter(subject=subject)
            if cert.exists():
                cert = cert.first()
                if self.verbose:
                    msg = ('Reassigning certificate with subject {0} from '
                           '{1} to {2}').format(subject,
                        cert.user, self.ligoldapuser.user)
                    self.write(msg)
                cert.user = self.ligoldapuser.user
                cert.ldap_user = self.ligoldapuser
                cert.save()
            else:
                if self.verbose:
                    self.write('Creating certificate with subject {0} for {1}'
                        .format(subject, self.ligoldapuser.user.username))
                cert, _ = X509Cert.objects.get_or_create(subject=subject,
                    user=self.ligoldapuser.user,
                    ldap_user=self.ligoldapuser)
                cert.save()

    def remove_certs(self, certs):
        # Remove old certificates from user
        # NOTE: we just delete these certs. They will be created again
        # if another user adds them.  This helps to keep random certificates
        # from floating around without a user.
        for subject in certs:
            cert = self.ligoldapuser.x509cert_set.filter(subject=subject, ldap_user=self.ligoldapuser)
            if cert.exists():
                if self.verbose:
                    self.write('Deleting certificate with subject {0} for {1}'
                        .format(subject, self.ligoldapuser.user.username))
                cert.delete()

    def assign_genericldapuser_to_cert(self, certs_to_add):
        # If a user's certs are missing a genericldapuser field, then assign
        # one. Note, it's assumed that every cert, regardless of ldap, is unique.
        # Meaning, the same user will get two different cert subjects from two different
        # ldaps. Since the current unique subject is coming from the current ldap, 
        # then the genericldapuser for the current cert must be the current ldap user. 

        for cert in certs_to_add:
             # Get a certificate object based off the current certificate subject AND
             # the current user (not ldapuser). If either:
             #  1) the certificate exists, but for a different user, or 
             #  2) the certificate does not exist, then 
             # Do nothing! because then add_certs() will either create with, or assign, a
             # cert with the correct ownership.

             current_cert = X509Cert.objects.filter(subject=cert)

             if current_cert.exists():
                 if current_cert.exclude(ldap_user=self.ligoldapuser).exists():
                     cert=current_cert.first()
                     if self.verbose:
                          msg = 'Assigning cert with subject {} to ldapuser {}'.format(cert.subject,
                                                                                  self.ligoldapuser)
                          self.write(msg)
                          cert.ldap_user = self.ligoldapuser
                          cert.save()


    def update_user_certificates(self):

        # Get a set of certificate subjects from the ldap query:
        ldap_x509_subjects = set([x.decode('utf-8') for x in
                                  self.ldap_result.get('gridX509subject', [])])

        # For the current user (not ligoldapuser), get the set of certificate subjects
        # that are in the database, but not assigned to an ldap_user yet. 

        unassigned_db_subjects = set(list(self.ligoldapuser.user.x509cert_set.filter(ldap_user=None).values_list(
                    'subject', flat=True)))

        # Clean up certs' ldap ownership. Most of the time, this function does 
        # nothing, but it will be run a lot the first time after adding the genericldapuser
        # field. 

        self.assign_genericldapuser_to_cert(unassigned_db_subjects)

        # Now that the unassigned certs have been linked to the current genericldapuser,
        # go through and perform the usual check. Get the list of certificate subjects
        # that are attached to the current ldap user. Note that the current *user*
        # account might have certs from other ldaps, but this checks for certs from the
        # current ldap, for the current ldap user. 

        db_x509_subjects = set(list(self.ligoldapuser.x509cert_set.values_list(
            'subject', flat=True)))

        
        # Get certs to add and remove
        certs_to_add = ldap_x509_subjects.difference(db_x509_subjects)
        certs_to_remove = db_x509_subjects.difference(ldap_x509_subjects)

        # Add and remove certificates
        self.add_certs(certs_to_add)
        self.remove_certs(certs_to_remove)

    def save_user(self):
        if self.user_created or self.user_changed:
            try:
                self.ligoldapuser.save()
            except Exception as e:
                self.write("Failed to save user '{0}': {1}.".format(
                    self.ligoldapuser.username, e))

    class UserConfigError(Exception):
        pass

    class UnacceptableUserError(Exception):
        pass


class LdapSciTokenRobotResultProcessor(LdapPersonResultProcessor):

    def __init__(self, ldap_dn, ldap_result, ldap_connection=None,
        verbose=True, stdout=None,
        ldap_member_name='Services:GraceDB:SciTokens:scopes:read:authorized',
        *args, **kwargs):
        super().__init__(
            ldap_dn, ldap_result, ldap_connection=ldap_connection,
            verbose=verbose, stdout=stdout,
            ldap_member_name=ldap_member_name,
            *args, **kwargs)

    def extract_user_attributes(self):
        if self.ldap_connection is None:
            raise RuntimeError('LDAP connection not configured')
        memberships = [group_name.decode('utf-8') for group_name in
            self.ldap_result.get('isMemberOf', [])]
        self.ldap_memberships = AuthorizedLdapMember.objects.filter(ldap_gname__in=
                    memberships)
        self.user_data = {
            'first_name': self.ldap_result['uid'][0].decode('utf-8'),
            'last_name': 'robot',
            'email': self.ldap_result['mail'][0].decode('utf-8'),
            'is_active': bool(self.ldap_connection.lvc_group.authorizedldapmember_set.all() &
                              self.ldap_memberships),
            'username': self.ldap_result['uid'][0].decode('utf-8').lower(),
        }

    def get_or_create_user(self):

        if not hasattr(self, 'user_data'):
            self.extract_user_attributes()

        # Determine if users exist
        user_exists = UserModel.objects.filter(username=
            self.user_data['username'].lower()).exists()
        l_user_exists = GenericLdapUser.objects.filter(
            ldap_dn=self.ldap_dn).exists()

        # Determine if robot has gracedb.read scope
        has_read_scope = self.ldap_authmember in self.ldap_memberships

        # Run any necessary checks at this point
        self.check_situation(user_exists, l_user_exists)

        # Handle different cases
        self.user_created = False
        if l_user_exists:
            # GenericLdapUser exists already (and thus, User object exists too)
            l_user = GenericLdapUser.objects.get(ldap_dn=self.ldap_dn)
            user = l_user.user
        else:
            # Robot has gracedb.read scope
            if has_read_scope:
                # GenericLdapUser doesn't exist
                if user_exists:
                    # User object exists, though, so we have to carefully create
                    # the GenericLdapUser object
                    user = UserModel.objects.get(username=
                        self.user_data['username'].lower())
                    l_user, created = GenericLdapUser.objects.get_or_create(ldap_dn=self.ldap_dn,
                                             ldap_member=self.ldap_authmember,
                                             user=user)
                    if (created and self.verbose):
                        self.write("Created genericldapuser for {0}".format(
                            user.username))
                else:
                    # No User object either, so we do a simple creation
                    user = UserModel(**self.user_data)
                    user.save()
                    l_user, created = GenericLdapUser.objects.get_or_create(ldap_dn=self.ldap_dn,
                                             ldap_member=self.ldap_authmember,
                                             user=user)
                    if (created and self.verbose):
                        self.write("Created user and ligoldapuser for {0}".format(
                        user.username))
                    self.user_created = True

            else:
                raise self.UnacceptableUserError('User dose not have gracedb.read scope')

        # Attach some information to this instance
        self.ligoldapuser = l_user
        self.user = user
        self.l_user_exists = l_user_exists
        self.user_exists = user_exists

        self.check_user_accounts()

    def update_user(self):
        if not hasattr(self, 'user'):
            raise RuntimeError('User object missing')
        self.update_user_attributes()
        self.update_user_groups()

    def update_user_groups(self):
        # Get list of group names that the user belongs to from the LDAP result
        memberships = [group_name.decode('utf-8') for group_name in
            self.ldap_result.get('isMemberOf', [])]

        # Get groups which are listed for the user in the LDAP and whose
        # membership is controlled by the LDAP
        ldap_group_ids = self.ldap_memberships.values_list('id')
        session_groups = self.validauthgroup_set.filter(authorizedldapmember__in=ldap_group_ids)

        # Determine if robot has gracedb.read scope
        has_read_scope = self.ldap_authmember in self.ldap_memberships

        # Robot has gracedb.read scope
        if has_read_scope:
            # Add the user to these groups
            if self.verbose and session_groups.exclude(id__in=self.ligoldapuser.user.groups.all()).exists():
                self.write("Adding {0} to {1}".format(self.ligoldapuser.user.username,
                    " and ".join(list(session_groups.values_list(
                    'name', flat=True)))))
            self.user.groups.add(*session_groups)

            # Get groups which are *not* listed for the user in the LDAP and whose
            # membership is controlled by the LDAP. First, get the set of groups that
            # are ldap-controlled and currently in the user's group set. In other words,
            # don't consider non-ldap groups like 'executives'.

            # Note: this has to be updated to exclude groups from other ldaps. So that
            # updating from kagra doesn't take out em_advocates, for instance.

            ldap_groups_in_user_set = self.validauthgroup_set.filter(id__in=self.ligoldapuser.user.groups.all())

            # Next get a list of groups to remove. So, the list of ldap groups in the set
            # that are not currently in session_groups.

            ldap_groups_to_remove = ldap_groups_in_user_set.exclude(id__in=session_groups)

            # Remove the user from these groups
            if self.verbose and ldap_groups_to_remove.exists():
                self.write("Removing {0} from {1}".format(
                    self.ligoldapuser.user.username,
                    " and ".join(list(ldap_groups_to_remove.values_list(
                    'name', flat=True)))))
            self.ligoldapuser.user.groups.remove(*ldap_groups_to_remove)
        else:
            ldap_groups_in_user_set = self.validauthgroup_set.filter(id__in=self.ligoldapuser.user.groups.all())
            ldap_groups_to_remove = ldap_groups_in_user_set.exclude(id__in=session_groups)

            # Remove the user from these groups
            if self.verbose and ldap_groups_to_remove.exists():
                self.write("Removing {0} from {1}".format(
                    self.ligoldapuser.user.username,
                    " and ".join(list(ldap_groups_to_remove.values_list(
                    'name', flat=True)))))
            self.ligoldapuser.user.groups.remove(*ldap_groups_to_remove)


class LdapKagraResultProcessor(LdapPersonResultProcessor):

    def __init__(self, ldap_dn, ldap_result, ldap_connection=None,
        verbose=True, stdout=None, 
        ldap_member_name='gw-astronomy:KAGRA-LIGO:members', 
        *args, **kwargs):
        super().__init__(
            ldap_dn, ldap_result, ldap_connection=ldap_connection,
            verbose=verbose, stdout=stdout,
            ldap_member_name=ldap_member_name,
            *args, **kwargs)

    def extract_user_attributes(self):
        if self.ldap_connection is None:
            raise RuntimeError('LDAP connection not configured')
        memberships = [group_name.decode('utf-8') for group_name in
            self.ldap_result.get('isMemberOf', [])]

        # Now that we have a list of memberships, find the corresponding 
        # session groups via the AuthorizedLdapMembers object. I (Alex) set
        # this up in 12/2019 as a many-to-one relation between ldap memberships
        # and internal group memberships. The 'ldap_gname' parameter is the LDAP 
        # membership parameter that links it to an internal group, for kagra members it's 
        # "gw-astronomy:KAGRA-LIGO:members".

        self.ldap_memberships = AuthorizedLdapMember.objects.filter(ldap_gname__in=
                    memberships)

        # Determine if user's ldap_memberships are part of the 
        self.user_data = {
            'first_name': self.ldap_result['givenName'][0].decode('utf-8'),
            'last_name': self.ldap_result['sn'][0].decode('utf-8'),
            'email': self.ldap_result['mail'][0].decode('utf-8'),
            'is_active': bool(self.ldap_connection.lvc_group.authorizedldapmember_set.all() & 
                              self.ldap_memberships),
            'username': self.ldap_result['eduPersonPrincipalName'][0].decode('utf-8').lower(),
        }

    def update_user(self):
        re_prefix = 'voPersonCertificateDN;.'
        if not hasattr(self, 'user'):
            raise RuntimeError('User object missing')
        self.update_user_attributes()
        self.update_user_groups()
        if  any(re.match(re_prefix, key) for key in self.ldap_result.keys()):
            self.update_user_certificates(re_prefix)

    def update_user_certificates(self, re_prefix):

        # Get two lists of subjects as sets. Then convert to lowercase. 
        db_x509_subjects = set(list(self.ligoldapuser.user.x509cert_set.values_list(
            'subject', flat=True)))
        db_x509_subjects = {str.casefold(x) for x in db_x509_subjects}

        ldap_x509_subjects = [self.ldap_result[key] for key in
                                  self.ldap_result.keys() if re.match(re_prefix, key)]
        ldap_x509_subjects = set(self.dekagrafy_subject(item.decode('utf-8')) for st in ldap_x509_subjects for item in st)
        ldap_x509_subjects = {str.casefold(x) for x in ldap_x509_subjects}

        # Clean up certs' ldap ownership. Most of the time, this function does 
        # nothing, but it'll be run a lot the first time after adding the genericldapuser
        # field. 

        self.assign_genericldapuser_to_cert(ldap_x509_subjects)

        # Get certs to add and remove
        certs_to_add = ldap_x509_subjects - db_x509_subjects
        certs_to_remove = db_x509_subjects - ldap_x509_subjects

        # Add and remove certificates
        self.add_certs(certs_to_add)
        self.remove_certs(certs_to_remove)

    def dekagrafy_subject(self, string):
         cert = string.split(',')
         cert.reverse()
         return '/'+'/'.join(cert)


# Classes for handling LDAP connections and queries ---------------------------
class LigoPeopleLdap:
    name = 'ligo'
    ldap_host = "ldaps://ldap.ligo.org"
    ldap_port = 636
    ldap_protocol_version = ldap.VERSION3
    base_dn = "ou=people,dc=ligo,dc=org"
    search_filter = "(employeeNumber=*)"
    search_scope = ldap.SCOPE_SUBTREE
    attribute_list = [
        "krbPrincipalName",
        "gridX509subject",
        "givenName",
        "sn",
        "mail",
        "isMemberOf",
    ]
    group_names = ['internal_users', 'em_advocates']
    user_processor_class = LdapPersonResultProcessor

    def __init__(self, verbose=True, *args, **kwargs):
        # Check configuration
        if not self.base_dn:
            raise ValueError('self.base_dn must be set')
        #if not self.attribute_list:
        #    raise ValueError('self.attribute_list must be set')

        # Set up groups
        self.groups = AuthGroup.objects.filter(name__in=self.group_names)
        self.lvc_group = AuthGroup.objects.get(name=settings.LVC_GROUP)

        self.verbose = verbose

    def initialize(self):
        ldap_address = '{host}:{port}'.format(host=self.ldap_host,
            port=self.ldap_port)
        self.ldap_object = ldap.initialize(ldap_address)
        self.ldap_object.set_option(ldap.OPT_X_SASL_NOCANON, ldap.OPT_ON)
        self.ldap_object.protocol_version = self.ldap_protocol_version

        # Start SASL secure connection:
        sasl_auth = ldap.sasl.sasl({} ,'GSSAPI')
        self.ldap_object.sasl_interactive_bind_s("", sasl_auth)

    def initialize_user_processor(self, *args, **kwargs):
        self.user_processor = self.user_processor_class(*args, **kwargs)
        self.user_processor.ldap_connection = self
        return self.user_processor

    def perform_query(self):
        ldap_result_id = self.ldap_object.search(self.base_dn,
            self.search_scope, filterstr=self.search_filter,
            attrlist=self.attribute_list)
        result_type, result_data = self.ldap_object.result(ldap_result_id,
            all=1, timeout=30)

        if not result_type == ldap.RES_SEARCH_RESULT:
            err_msg = 'Unexpected result type ({rt}) from LDAP query'.format(
                rt=result_type)
            raise TypeError(err_msg)

        return result_data


class LigoSciTokenRobotsLdap(LigoPeopleLdap):
    name = 'robots'
    base_dn = "ou=scitoken,ou=robot,dc=ligo,dc=org"
    search_filter = "(isMemberOf=Services:GraceDB:SciTokens:scopes:read:authorized)"
    search_scope = ldap.SCOPE_SUBTREE
    attribute_list = [
        "uid",
        "mail",
        "isMemberOf",
    ]
    group_names = ['internal_users']
    user_processor_class = LdapSciTokenRobotResultProcessor

    def __init__(self, verbose=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Check configuration
        if not self.base_dn:
            raise ValueError('self.base_dn must be set')
        #if not self.attribute_list:
        #    raise ValueError('self.attribute_list must be set')


class KagraPeopleLdap(LigoPeopleLdap):
    name = 'kagra'
    base_dn = "ou=people,o=KAGRA,dc=igwn,dc=org"
    ldap_host = "ldaps://ldap.igwn.org"
    ldap_port = 636
    search_filter = "(cn=*)"
    search_scope = ldap.SCOPE_SUBTREE
    attribute_list = [
        'cn',
        'sn',
        'givenName',
        'uid',
        'voPersonCertificateDN',
        'mail',
        'isMemberOf',
        'eduPersonPrincipalName',
    ]
    group_names = ['internal_users']
    user_processor_class = LdapKagraResultProcessor

    # Extra stuff for KAGRA attributes:
    kagra_dn_key_substring = "voPersonCertificateDN;scope"

    # In the test queries I (Alex) had performed, not all users had a value for 
    # voPersonCertificateDN, which is the kagra ldap equivalent (formatting aside)
    # of gridX509subject. So, this function will scan through the results of the ldap
    # query, and then return a subset of users that have that key. Note: some users
    # may have multiple occurances of that key, so the function takes *all* the keys, 
    # flattens them to one big string, and then looks for at least one occurance of the 
    # search key string (kagra_dn_key_substring). This prevents a user's info from
    # getting added to the db more than once. 

    def get_kagra_users_with_dns(self, result_data):
        filtered_results = []
        for val in result_data:
            if (self.kagra_dn_key_substring in ''.join(val[1].keys())):
                filtered_results.append(val)
        return filtered_results

    def perform_query(self):
        ldap_result_id = self.ldap_object.search(self.base_dn,
            self.search_scope, filterstr=self.search_filter,
            attrlist=self.attribute_list)
        result_type, result_data = self.ldap_object.result(ldap_result_id,
            all=1, timeout=30)

        if not result_type == ldap.RES_SEARCH_RESULT:
            err_msg = 'Unexpected result type ({rt}) from LDAP query'.format(
                rt=result_type)
            raise TypeError(err_msg)

        # Return result data that has been filtered with DNs:
        return result_data
    

# Dict of LDAP classes with names as keys
LDAP_CLASSES = {l.name: l for l in (LigoPeopleLdap, LigoSciTokenRobotsLdap, KagraPeopleLdap,)}


class Command(BaseCommand):
    help="Get updated user data from LIGO/gw-astronomy LDAP"

    def add_arguments(self, parser):
        parser.add_argument('ldap', choices=list(LDAP_CLASSES),
            help="Name of LDAP to use")
        parser.add_argument('-q', '--quiet', action='store_true',
            default=False, help='Suppress output')

    def handle(self, *args, **options):
        verbose = not options['quiet']
        if verbose:
            self.stdout.write('Refreshing users from {0} LDAP at {1}' \
                .format(options['ldap'], datetime.datetime.utcnow()))

        # Set up ldap connection
        ldap_connection = LDAP_CLASSES[options['ldap']](verbose=verbose)
        ldap_connection.initialize()

        # Perform query and get all results
        result_data = ldap_connection.perform_query()

        # Loop over results
        for ldap_dn, ldap_result in result_data:
            # Set up user processor
            user_processor = ldap_connection.initialize_user_processor(ldap_dn,
                ldap_result, verbose=verbose, stdout=self.stdout)

            # Get or create user - if an error occurs, continue.
            # Details should already be written to the log.
            try:
                user_processor.extract_user_attributes()
                user_processor.get_or_create_user()
            except user_processor.UserConfigError as e:
                continue
            except user_processor.UnacceptableUserError as e:
                # Indicates that the user shouldn't be added
                continue

            # Update user based on LDAP information - this includes
            # attributes, group memberships, X509 certificates, etc.
            user_processor.update_user()

            # Try to save user
            user_processor.save_user()

        # Extra stuff
        if (ldap_connection.name == 'robots'):
            pass
            # NOTE: eventually (i.e., once all of the old LIGO.ORG certificates
            # are expired), we will want to remove any robot certificates which
            # aren't found in this LDAP query (effectively deactivating any
            # accounts which have no certificates attached to them).
