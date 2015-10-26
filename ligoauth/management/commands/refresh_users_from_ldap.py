
from django.core.management.base import NoArgsCommand

from ligoauth.models import LigoLdapUser, X509Cert, AlternateEmail

from django.contrib.auth.models import User, Group

from django.db.utils import IntegrityError

import ldap

baseDN = "ou=people,dc=ligo,dc=org"
searchScope = ldap.SCOPE_SUBTREE
searchFilter = "(employeeNumber=*)"
retrieveAttributes = ["krbPrincipalName",
                      "gridX509subject",
                      "givenName",
                      "sn",
                      "mail",
                      "isMemberOf", 
                      "mailAlternateAddress",
                      "mailForwardingAddress"]

class Command(NoArgsCommand):
    help = "Update ligoauth.models.LigoUser and django.contrib.auth.models.User from LIGO LDAP"

    def handle_noargs(self, **options):
        l = ldap.open("ldap.ligo.org")
        l.protocol_version = ldap.VERSION3
        ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
        while 1:
            result_type, result_data = l.result(ldap_result_id, 0)
            if (result_data == []):
                break
            else:
                if result_type == ldap.RES_SEARCH_ENTRY:
                    for (ldap_dn, ldap_result) in result_data:

                        first_name = unicode(ldap_result['givenName'][0], 'utf-8')
                        last_name = unicode(ldap_result['sn'][0], 'utf-8')
                        email = ldap_result['mail'][0]
                        new_dns = set(ldap_result.get('gridX509subject',[]))
                        memberships = ldap_result.get('isMemberOf',[])
                        is_active = "Communities:LSCVirgoLIGOGroupMembers" in memberships
                        principal = ldap_result['krbPrincipalName'][0]
                        #mailForwardingAddress = ldap_result.get('mailForwardingAddress', None)
                        try:
                            mailForwardingAddress = unicode(ldap_result['mailForwardingAddress'][0])
                        except:
                            mailForwardingAddress = None
                        mailAlternateAddresses = ldap_result.get('mailAlternateAddress', [])

                        # Update/Create LigoLdapUser entry
                        # This is breaking. XXX Do we need to pass in default values for the underlying User object?
                        defaults = {
                            'first_name' : first_name,
                            'last_name'  : last_name,
                            'email'      : email,
                            'username'   : principal,
                            'is_active'  : is_active
                        }

                        # Sometimes the user will have been created by the auth middleware as the
                        # result of a new user arriving with a shib session. So we must try to 
                        # look up the user first.
                        try:
                            user = LigoLdapUser.objects.get(username=defaults['username'])
                            created = False
                        except User.DoesNotExist:
                            try:
                                user, created = LigoLdapUser.objects.get_or_create(ldap_dn=ldap_dn, defaults=defaults)
                            except IntegrityError:
                                # This actually should not happen. 
                                print "Problem for %s" % ldap_dn
                                continue

                        # Now we allow for a change in the ldap_dn, since the ldap_dn will be an 
                        # empty string if the user is created based off of a shib session (which will
                        # not have the ldap_dn).
                        changed = created \
                                or (user.ldap_dn != ldap_dn) \
                                or (user.first_name != first_name) \
                                or (user.last_name != last_name) \
                                or (user.email != email) \
                                or (user.username != principal) \
                                or (user.is_active != is_active)

                        if changed:
                            user.ldap_dn = ldap_dn
                            user.first_name = first_name
                            user.last_name = last_name
                            user.email = email
                            user.username = principal
                            user.is_active = is_active
                            # revoke staff/superuser if not active.
                            user.is_staff = user.is_staff and is_active
                            user.is_superuser = user.is_superuser and is_active
                            try:
                                user.save()
                            except Exception, e:
                                print "Failed to save user '%s'.  (%s)" % (ldap_dn, first_name+" "+last_name)
                                print "Reason: %s" % str(e)

                        # update X509 certs for user
                        current_dns = set([ cert.subject for cert in user.x509cert_set.all() ])

                        if current_dns != new_dns:
# XXX Some certs put in by hand are getting blow away. I don't think this feature is really needed anyway.
#                            for dn in current_dns - new_dns:
#                                X509Cert.objects.get(subject=dn).delete()
                            for dn in new_dns - current_dns:
                                cert, created = X509Cert.objects.get_or_create(subject=dn)
                                if created:
                                    cert.save()
                                cert.users.add(user)

                        # update group information
                        # We do this only for groups that already exist in the GraceDB database
                        for g in Group.objects.all():
                            if g.name in memberships:
                                # Add the user to the group. First get the User object.
                                u = User.objects.get(username = user.username)
                                print "Adding %s to %s" % (user.username,g.name)
                                g.user_set.add(u)

                        # Finally, deail with alternate emails.
                        if mailForwardingAddress:
                            try:
                                AlternateEmail.objects.get_or_create(user=user, 
                                    email=mailForwardingAddress)
                            except:
                                pass

                        if len(mailAlternateAddresses) > 0:
                            for email in mailAlternateAddresses:
                                try:
                                    AlternateEmail.objects.get_or_create(user=user,
                                        email=email)
                                except:
                                    pass
