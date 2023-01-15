from django.db import models
from django.contrib.auth.models import User, Group

from .managers import LdapGroupManager, TagGroupManager


class LigoLdapUser(User):
    ldap_dn = models.CharField(max_length=100, null=False, unique=True)

#   def _get_or_create_auth_user(self):
#       return User.get_or_create(username=self.principal)

    def name(self):
        # XXX I really don't freaking understand WHY THIS SEEMS NECESSARY.
        # print(user.name()) gives an idiotic ascii coding error otherwise. WHY!?
        return u"{0} {1}".format(self.first_name, self.last_name).encode('utf-8')

class AuthGroup(Group):
    """Enhanced version of Django Group model"""
    # Description of the group
    description = models.TextField(blank=False)
    # The group's name in some LDAP (likely the LIGO LDAP). This will be used
    # to correlated group memberships in the LDAP as retrieved from an LDAP
    # query or from a Shibboleth session to groups in this service
    # If this is null, the group is manually managed and does not inherit its
    # membership from an LDAP.
    ldap_name = models.CharField(max_length=50, unique=True, null=True)
    # Tag used to expose access to log messages for group; if null, there is no
    # such tag and access is not granted via this mechanism
    tag = models.ForeignKey('events.Tag', null=True, on_delete=models.CASCADE)

    # Add custom managers, must manually define objects as well
    objects = models.Manager()
    ldap_objects = LdapGroupManager()
    tag_objects = TagGroupManager()

class AuthorizedLdapMember(models.Model):
    """Model for authorized ldap membership"""
    # Group membership in ldap. This is analogous to the `ldap_name` in the 
    # AuthGroup class:
    ldap_gname = models.CharField(max_length=100, unique=True, null=True)

    # Add support for authorized membership:
    ldap_authgroup = models.ForeignKey(AuthGroup, null=True, on_delete=models.CASCADE)

    # Give it a name:
    name = models.CharField(max_length=50, unique=True, null=True)

    def __str__(self):
        return self.name

# Set up a model for a generic ldap user. This arose out when kagra's ldap was added
# and there were multiple users across the ligo and kagra ldap. In practice, i don't 
# know how many users like that there will actually be in practice, but this is a safeguard
# from having certs overwritten each time the ldap is polled. Also, modify the X509Cert
# object to use this as a foreign key as well. 

class GenericLdapUser(models.Model):
    ldap_dn = models.CharField(max_length=255, null=False, unique=True)
    #ldap_source = models.CharField(max_length=100, null=False) # 'ligo', 'kagra', 'etc'
    # scratch this, change it to AUthorizedldapMembership
    ldap_member = models.ForeignKey(AuthorizedLdapMember, null=False, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return "{}- {}".format(self.ldap_member.name,self.user.username)

class X509Cert(models.Model):
    """Model for storing X.509 certificate subjects for API access"""
    subject = models.CharField(max_length=255, unique=True, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ldap_user = models.ForeignKey(GenericLdapUser, null=True, on_delete=models.CASCADE)

    class Meta:
        indexes = [models.Index(fields=['subject', ]), ]

