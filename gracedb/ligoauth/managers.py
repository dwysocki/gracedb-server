from django.db import models

# Custom managers for the AuthGroup model
class LdapGroupManager(models.Manager):
    """Groups whose membership is managed through an LDAP"""
    def get_queryset(self):
        return super(LdapGroupManager, self).get_queryset().filter(
            ldap_name__isnull=False)


class TagGroupManager(models.Manager):
    """Groups who have an associated tag for allowing log viewing"""
    def get_queryset(self):
        return super(TagGroupManager, self).get_queryset().filter(
            tag__isnull=False)
