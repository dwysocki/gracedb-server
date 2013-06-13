
from __future__ import unicode_literals

from django.db import models
from django.contrib.auth.models import User

# There seems to be a LOT of duplication here and I don't know
# if that is good or bad.  Normally, that seems bad...
#
# The thing is, LigoLdapUser and LocalUser (and whatever we might add later)
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


class LocalUser(User):
    pass

class X509Cert(models.Model):
    subject = models.CharField(max_length=200)
    users = models.ManyToManyField(User)


def shibid_to_user(shibid):
    try:
        return User.objects.get(username=shibid)
    except User.DoesNotExist:
        return None

def certdn_to_user(dn, username=None):
    try:
        possible_users = X509Cert.objects.get(subject=dn).users
    except:
        return None

    if username:
        possible_users.filter(username=username)

    try:
        return possible_users.all()[0]
    except IndexError:
        return None

