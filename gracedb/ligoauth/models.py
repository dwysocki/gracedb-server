from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User, Group

from .managers import LdapGroupManager, TagGroupManager


# There seems to be a LOT of duplication here and I don't know
# if that is good or bad.  Normally, that seems bad...
#
# The thing is, LigoLdapUser and RobotUser (and whatever we might add later)
# are actual entities that we want synched with the Django User, so they *are*
# separate could conceivably have different first_name's, say, yet still refer
# to the same (abstract) user entity.  Not likely, and not initially, but
# conceivably.
#
# Whatever.  Just am not fully pleased with this.

#from exceptions import NotImplementedError

#class MetaUser(models.Model):
    #class Meta:
        #abstract = True

    #first_name = models.CharField(max_length=50, blank=False, null=False, unique=True)
    #last_name = models.CharField(max_length=50, blank=False, null=False, unique=True)
    #email = models.EmailField()
    #username = models.CharField(max_length=100, unique=True)
    #is_active = models.BooleanField(default=True)
    #auth_user = models.ForeignKey(User, null=False)

    #def _get_or_create_auth_user(self):
        #raise NotImplementedError(str(self.__class__) + " _get_auth_user")

    #def save(self):
        #user, created = self._get_auth_user()
        #changed = created \
                #or (user.first_name != self.first_name) \
                #or (user.last_name != self.last_name) \
                #or (user.email != self.email) \
                #or (user.is_active == self.is_active)
        #if changed:
            #user.first_name = self.first_name
            #user.last_name = self.last_name
            #user.email = self.email
            #user.is_active = self.is_active
            #user.save()
        #models.Model.save(self)

class LigoLdapUser(User):
    ldap_dn = models.CharField(max_length=100, null=False, unique=True)

#   def _get_or_create_auth_user(self):
#       return User.get_or_create(username=self.principal)

    def name(self):
        # XXX I really don't freaking understand WHY THIS SEEMS NECESSARY.
        # print user.name()  gives an idiotic ascii coding error otherwise. WHY!?
        return u"{0} {1}".format(self.first_name, self.last_name).encode('utf-8')


# Class for robot accounts
class RobotUser(User):
    pass


class X509Cert(models.Model):
    """Model for storing X.509 certificate subjects for API access"""
    subject = models.CharField(max_length=300)
    users = models.ManyToManyField(User)


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
    tag = models.ForeignKey('events.Tag', null=True)

    # Add custom managers, must manually define objects as well
    objects = models.Manager()
    ldap_objects = LdapGroupManager()
    tag_objects = TagGroupManager()
