from django.core.management.base import BaseCommand, CommandError

import datetime
from ligoauth.models import LigoLdapUser, X509Cert, AlternateEmail
from django.conf import settings
from django.contrib.auth.models import User, Group
import ldap

# Variables for LDAP search
BASE_DN = "ou=people,dc=ligo,dc=org"
SEARCH_SCOPE = ldap.SCOPE_SUBTREE
SEARCH_FILTER = "(employeeNumber=*)"
RETRIEVE_ATTRIBUTES = [
    "krbPrincipalName",
    "gridX509subject",
    "givenName",
    "sn",
    "mail",
    "isMemberOf",
    "mailAlternateAddress",
    "mailForwardingAddress"
]
LDAP_ADDRESS = "ldap.ligo.org"
LDAP_PORT = 636

class Command(BaseCommand):
    help="Get updated user data from LIGO LDAP"

    def add_arguments(self, parser):
        parser.add_argument('-q', '--quiet', action='store_true',
            default=False, help='Suppress output')

    def handle(self, *args, **options):
        verbose = not options['quiet']
        if verbose:
            self.stdout.write('Refreshing users from LIGO LDAP at {0}' \
                .format(datetime.datetime.utcnow()))

        # Get LVC group
        lvc_group = Group.objects.get(name=settings.LVC_GROUP)

        # Open connection to LDAP and run a search
        l = ldap.initialize("ldaps://{address}:{port}".format(
            address=LDAP_ADDRESS, port=LDAP_PORT))
        l.protocol_version = ldap.VERSION3
        ldap_result_id = l.search(BASE_DN, SEARCH_SCOPE, SEARCH_FILTER,
            RETRIEVE_ATTRIBUTES)
    
        # Get all results
        result_data = True
        while result_data:
            result_type, result_data = l.result(ldap_result_id, 0)
    
            if result_type == ldap.RES_SEARCH_ENTRY:
                for (ldap_dn, ldap_result) in result_data:
                    first_name = unicode(ldap_result['givenName'][0], 'utf-8')
                    last_name = unicode(ldap_result['sn'][0], 'utf-8')
                    email = ldap_result['mail'][0]
                    new_dns = set(ldap_result.get('gridX509subject', []))
                    memberships = ldap_result.get('isMemberOf', [])
                    is_active = lvc_group.name in memberships
                    principal = ldap_result['krbPrincipalName'][0]
    
                    # Update/Create LigoLdapUser entry
                    defaults = {
                        'first_name': first_name,
                        'last_name': last_name,
                        'email': email,
                        'username': principal,
                        'is_active': is_active,
                    }
    
                    # Determine if base user and ligoldapuser objects exist
                    user_exists = User.objects.filter(username=
                        defaults['username']).exists()
                    l_user_exists = LigoLdapUser.objects.filter(
                        ldap_dn=ldap_dn).exists()
    
                    # Handle different cases
                    created = False
                    if l_user_exists:
                        l_user = LigoLdapUser.objects.get(ldap_dn=ldap_dn)
                        user = l_user.user_ptr
                    else:
                        if user_exists:
                            user = User.objects.get(username=
                                defaults['username'])
                            l_user = LigoLdapUser.objects.create(
                                ldap_dn=ldap_dn, user_ptr=user)
                            l_user.__dict__.update(user.__dict__)
                            if verbose:
                                self.stdout.write(("Created ligoldapuser "
                                    "for {0}").format(user.username))
                        else:
                            l_user = LigoLdapUser.objects.create(
                                ldap_dn=ldap_dn, **defaults)
                            user = l_user.user_ptr
                            if verbose:
                                self.stdout.write(("Created user and "
                                    "ligoldapuser for {0}").format(
                                    l_user.username))
                            created = True
    
                    # Typically a case where the person's username was changed
                    # and there are now two user accounts in GraceDB
                    if user.username != defaults['username'] and user_exists:
                        self.stdout.write(('ERROR: requires manual '
                            'investigation. LDAP username: {0}, '
                            'ligoldapuser.user_ptr.username: {1}').format(
                            defaults['username'], l_user.user_ptr.username))
                        continue
    
                    # Update user attributes from LDAP
                    changed = False
                    if not created:
                        for k in defaults:
                            if (defaults[k] != getattr(user, k)):
                                setattr(l_user, k, defaults[k])
                                changed = True
                    if changed and verbose:
                        self.stdout.write("User {0} updated".format(
                            l_user.username))
    
                    # Revoke staff/superuser if not active.
                    if ((l_user.is_staff or l_user.is_superuser)
                        and not is_active):
                        l_user.is_staff = l_user.is_superuser = False
                        changed = True
    
                    # Try to save user.
                    if created or changed:
                        try:
                            l_user.save()
                        except Exception as e:
                            self.stdout.write(("Failed to save user '{0}': "
                                "{1}.").format(l_user.username, e))
                            continue
    
                    # Update X509 certs for user
                    current_dns = set([c.subject for c in
                        user.x509cert_set.all()])
                    if current_dns != new_dns:
                        for dn in new_dns - current_dns:
                            cert, created = X509Cert.objects.get_or_create(
                                subject=dn)
                            cert.users.add(l_user)
    
                    # Update group information - we do this only for groups
                    # that already exist in GraceDB
                    for g in Group.objects.all():
                        # Add the user to the group if they aren't a member
                        if (g.name in memberships and g not in
                            l_user.groups.all()):

                            g.user_set.add(l_user)
                            if verbose:
                                self.stdout.write("Adding {0} to {1}".format(
                                    l_user.username, g.name))
    
                    # Remove the user from the LVC group if they are no longer
                    # a member. This is the only group in GraceDB which is
                    # populated from the LIGO LDAP.
                    if (lvc_group.name not in memberships and
                        lvc_group in l_user.groups.all()):
    
                        l_user.groups.remove(lvc_group)
                        if verbose:
                            self.stdout.write("Removing {user} from {group}" \
                                .format(user=l_user.username,
                                group=lvc_group.name))
    
                    # Get alternate email addresses (for some reason...)
                    try:
                        mailForwardingAddress = unicode(ldap_result['mailForwardingAddress'][0])
                    except:
                        mailForwardingAddress = None
                    mailAlternateAddresses = ldap_result.get('mailAlternateAddress', [])
    
                    # Finally, deal with alternate emails.
                    if mailForwardingAddress:
                        try:
                            AlternateEmail.objects.get_or_create(l_user=user,
                                email=mailForwardingAddress)
                        except:
                            pass
    
                    if len(mailAlternateAddresses) > 0:
                        for email in mailAlternateAddresses:
                            try:
                                AlternateEmail.objects.get_or_create(
                                    l_user=user, email=email)
                            except:
                                pass
