
from django.core.management.base import NoArgsCommand

from ligoauth.models import LigoLdapUser, X509Cert

import ldap

baseDN = "ou=people,dc=ligo,dc=org"
searchScope = ldap.SCOPE_SUBTREE
searchFilter = "(employeeNumber=*)"
retrieveAttributes = ["krbPrincipalName",
                      "gridX509subject",
                      "givenName",
                      "sn",
                      "mail",
                      "isMemberOf"]

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
                        is_active = "Communities:LSCVirgoLIGOGroupMembers" \
                                    in ldap_result.get('isMemberOf',[])
                        principal = ldap_result['krbPrincipalName'][0]

                        # Update/Create LigoLdapUser entry
                        user, created = LigoLdapUser.objects.get_or_create(ldap_dn=ldap_dn)

                        changed = created \
                                or (user.first_name != first_name) \
                                or (user.last_name != last_name) \
                                or (user.email != email) \
                                or (user.username != principal) \
                                or (user.is_active != is_active)

                        if changed:
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

                        # update X509 certs for user
                        current_dns = set([ cert.subject for cert in user.x509cert_set.all() ])

                        if current_dns != new_dns:
                            for dn in current_dns - new_dns:
                                X509Cert.objects.get(subject=dn).delete()
                            for dn in new_dns - current_dns:
                                cert, created = X509Cert.objects.get_or_create(subject=dn)
                                if created:
                                    cert.save()
                                cert.users.add(user)
