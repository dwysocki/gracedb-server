import datetime
import ldap

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from ligoauth.models import LigoLdapUser, X509Cert, AuthGroup

UserModel = get_user_model()


# Classes for processing LDAP results into user accounts ----------------------
class LdapPersonResultProcessor(object):
    stdout = None

    def __init__(self, ldap_dn, ldap_result, ldap_connection=None,
        verbose=True, stdout=None, *args, **kwargs):
        super(LdapPersonResultProcessor, self).__init__(*args, **kwargs)
        self.ldap_dn = ldap_dn
        self.ldap_result = ldap_result
        self.verbose = verbose
        self.ldap_connection = ldap_connection
        self.stdout = stdout

    def write(self, message):
        if self.stdout:
            self.stdout.write(message)
        else:
            print(message)

    def extract_user_attributes(self):
        if self.ldap_connection is None:
            raise RuntimeError('LDAP connection not configured')
        self.user_data = {
            'first_name': unicode(self.ldap_result['givenName'][0], 'utf-8'),
            'last_name': unicode(self.ldap_result['sn'][0], 'utf-8'),
            'email': self.ldap_result['mail'][0],
            'is_active': self.ldap_connection.lvc_group.ldap_name in
                self.ldap_result.get('isMemberOf', []),
            'username': self.ldap_result['krbPrincipalName'][0],
        }

    def check_situation(self, user_exists, l_user_exists):
        pass

    def get_or_create_user(self):
        if not hasattr(self, 'user_data'):
            self.extract_user_attributes()

        # Determine if users exist
        user_exists = UserModel.objects.filter(username=
            self.user_data['username']).exists()
        l_user_exists = LigoLdapUser.objects.filter(
            ldap_dn=self.ldap_dn).exists()

        # Run any necessary checks at this point
        self.check_situation(user_exists, l_user_exists)

        # Handle different cases
        self.user_created = False
        if l_user_exists:
            # LigoLdapUser exists already (and thus, User object exists too)
            l_user = LigoLdapUser.objects.get(ldap_dn=self.ldap_dn)
            user = l_user.user_ptr
        else:
            # LigoLdapUser doesn't exist
            if user_exists:
                # User object exists, though, so we have to carefully create
                # the LigoLdapUser object
                user = UserModel.objects.get(username=
                    self.user_data['username'])
                l_user = LigoLdapUser(ldap_dn=self.ldap_dn, user_ptr=user)
                l_user.__dict__.update(user.__dict__)
                l_user.save()
                if self.verbose:
                    self.write("Created ligoldapuser for {0}".format(
                        user.username))
            else:
                # No User object either, so we do a simple creation
                l_user = LigoLdapUser.objects.create(ldap_dn=self.ldap_dn,
                    **self.user_data)
                user = l_user.user_ptr
                if self.verbose:
                    self.write("Created user and ligoldapuser for {0}".format(
                    l_user.username))
                self.user_created = True

        self.ligoldapuser = l_user
        self.user = user

        self.check_user_accounts()

    def check_user_accounts(self):
        if not (hasattr(self, 'user_data') or hasattr(self, 'user')):
            raise RuntimeError('User data or user object missing')
        if (self.user.username != self.user_data['username'] and
            self.user_exists):
            self.write(('ERROR: requires manual investigation. LDAP '
                'username: {0}, ligoldapuser.user_ptr.username: {1}')
                .format(self.user_data['username'],
                self.ligoldapuser.user_ptr.username))
            raise UserConfigError('User configuration error')

    def update_user(self):
        if not hasattr(self, 'user'):
            raise RuntimeError('User object missing')
        self.update_user_attributes()
        self.update_user_groups()
        self.update_user_certificates()

    def get_attributes_to_update(self):
        attributes_to_update = [k for k,v in self.user_data.items()
            if v != getattr(self.ligoldapuser, k)]
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
            setattr(self.ligoldapuser, k, self.user_data[k])

        # Revoke staff/superuser if not active.
        if ((self.ligoldapuser.is_staff or self.ligoldapuser.is_superuser)
            and not self.user_data['is_active']):
            self.ligoldapuser.is_staff = self.ligoldapuser.is_superuser = False
            self.user_changed = True

        if self.user_changed and self.verbose:
            self.write("User {0} updated".format(self.ligoldapuser.username))

    def update_user_groups(self):
        # Get list of group names that the user belongs to from the LDAP result
        memberships = self.ldap_result.get('isMemberOf', [])

        # Get groups which are listed for the user in the LDAP and whose
        # membership is controlled by the LDAP
        ldap_groups_to_add = self.ldap_connection.groups.filter(ldap_name__in=
            memberships).exclude(pk__in=self.ligoldapuser.groups.all())

        # Add the user to these groups
        if self.verbose and ldap_groups_to_add.exists():
            self.write("Adding {0} to {1}".format(self.ligoldapuser.username,
                " and ".join(list(ldap_groups_to_add.values_list(
                'name', flat=True)))))
        self.ligoldapuser.groups.add(*ldap_groups_to_add)

        # Get groups which are *not* listed for the user in the LDAP and whose
        # membership is controlled by the LDAP
        ldap_groups_to_remove = self.ligoldapuser.groups.filter(pk__in=
            self.ldap_connection.groups.exclude(ldap_name__in=memberships))

        # Remove the user from these groups
        if self.verbose and ldap_groups_to_remove.exists():
            self.write("Removing {0} from {1}".format(
                self.ligoldapuser.username,
                " and ".join(list(ldap_groups_to_remove.values_list(
                'name', flat=True)))))
        self.ligoldapuser.groups.remove(*ldap_groups_to_remove)

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
                        cert.user, self.ligoldapuser.username)
                    self.write(msg)
                cert.user = self.ligoldapuser
                cert.save()
            else:
                if self.verbose:
                    self.write('Creating certificate with subject {0} for {1}'
                        .format(subject, self.ligoldapuser.username))
                cert, _ = X509Cert.objects.get_or_create(subject=subject,
                    user=self.ligoldapuser)

    def remove_certs(self, certs):
        # Remove old certificates from user
        # NOTE: we just delete these certs. They will be created again
        # if another user adds them.  This helps to keep random certificates
        # from floating around without a user.
        for subject in certs:
            if self.verbose:
                self.write('Deleting certificate with subject {0} for {1}'
                    .format(subject, self.ligoldapuser.username))
            cert = self.ligoldapuser.x509cert_set.get(subject=subject)
            cert.delete()

    def update_user_certificates(self):
        # Get two lists of subjects as sets
        db_x509_subjects = set(list(self.ligoldapuser.x509cert_set.values_list(
            'subject', flat=True)))
        ldap_x509_subjects = set(self.ldap_result.get('gridX509subject', []))

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


class LdapRobotResultProcessor(LdapPersonResultProcessor):

    def extract_user_attributes(self):
        if self.ldap_connection is None:
            raise RuntimeError('LDAP connection not configured')
        self.user_data = {
            'last_name': unicode(self.ldap_result['x-LIGO-TWikiName'][0],
                'utf-8'),
            'email': self.ldap_result['mail'][0],
            'is_active': self.ldap_connection.groups.get(
                name='robot_accounts').name in self.ldap_result.get(
                'isMemberOf', []),
            'username': self.ldap_result['cn'][0],
        }

    def check_situation(self, user_exists, l_user_exists):
        if (not (user_exists or l_user_exists) and not self.user_data['is_active']):
            err_msg = 'User {0} should not be added to the DB'.format(
                self.user_data['username'])
            self.write(err_msg)
            raise self.UnacceptableUserError(err_msg)

    def get_attributes_to_update(self):
        attributes_to_update = [k for k in ['email', 'is_active']
            if self.user_data[k] != getattr(self.ligoldapuser, k)]
        return attributes_to_update

    def remove_certs(self, certs):
        pass
        # NOTE: for now (2019) we don't remove any robot certificates since
        # there arestill some old LIGO CA certificates in use that aren't in
        # the LDAP


# Classes for handling LDAP connections and queries ---------------------------
class LigoPeopleLdap(object):
    name = 'people'
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
        super(LigoPeopleLdap, self).__init__(*args, **kwargs)
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
        self.ldap_object.protocol_version = self.ldap_protocol_version

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


class LigoRobotsLdap(LigoPeopleLdap):
    name = 'robots'
    base_dn = "ou=keytab,ou=robot,dc=ligo,dc=org"
    search_filter = "(cn=*)"
    search_scope = ldap.SCOPE_SUBTREE
    attribute_list = [
        'cn',
        'uid',
        'gridX509subject',
        'mail',
        'isMemberOf',
        'x-LIGO-TWikiName',
    ]
    group_names = ['internal_users', 'robot_accounts']
    user_processor_class = LdapRobotResultProcessor


# Dict of LDAP classes with names as keys
# NOTE: not using robot OU right now since we are waiting
# for some auth infrastructure changes to be able to properly group
# certificates into a user account
#LDAP_CLASSES = {l.name: l for l in (LigoPeopleLdap, LigoRobotsLdap)}
LDAP_CLASSES = {l.name: l for l in (LigoPeopleLdap,)}


class Command(BaseCommand):
    help="Get updated user data from LIGO LDAP"

    def add_arguments(self, parser):
        parser.add_argument('ldap', choices=list(LDAP_CLASSES),
            help="Name of LDAP to use")
        parser.add_argument('-q', '--quiet', action='store_true',
            default=False, help='Suppress output')

    def handle(self, *args, **options):
        if options['ldap'] == 'robots':
            raise ValueError('Not properly set up for robot OU')
        verbose = not options['quiet']
        if verbose:
            self.stdout.write('Refreshing users from LIGO LDAP at {0}' \
                .format(datetime.datetime.utcnow()))

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
