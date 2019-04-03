import logging

from django.contrib.auth import backends
from django.contrib.auth import authenticate, get_user_model
from django.conf import settings

# User model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)

# Mapping from Shibboleth attributes to User object attributes
DEFAULT_SHIB_ATTRIBUTES = {
    'email': 'mail',
    'first_name': 'givenName',
    'last_name': 'sn',
}


class ModelPermissionsForObjectBackend(backends.ModelBackend):
    """
    Establishes a hierarchy for permissions: model/table-level
    permissions are accepted in lieu of object/row-level permissions.
    """
    def has_perm(self, user_obj, perm, obj=None):
        # If an object is passed, Django's ModelBackend returns set() as the
        # user's permissions.  Otherwise, it returns the actual set of
        # permissions that the user has.  So we just run the check with obj set
        # to None. This change just adjusts the logic:
        #   Previously, it was:
        #     No object: check for table-level permissions
        #     With object: return False
        #   Now, logic is: check for table-level permissions in either case
        return super(ModelPermissionsForObjectBackend, self).has_perm(user_obj,
            perm, obj=None)


class ShibbolethRemoteUserBackend(backends.RemoteUserBackend):
    """
    Almost completely taken from Django's RemoteUserBackend, but we have to
    make very small customizations so that we can extract extra parameters from
    the Shibboleth session and use them in self.update_user.
    """
    create_unknown_user = True
    attribute_map = getattr(settings, 'SHIB_ATTRIBUTE_MAP',
        DEFAULT_SHIB_ATTRIBUTES)
    attribute_delimiter = ';'

    def authenticate(self, request, remote_user):

        if not remote_user:
            return
        user = None
        username = self.clean_username(remote_user)

        # Note that this could be accomplished in one try-except clause, but
        # instead we use get_or_create when creating unknown users since it has
        # built-in safeguards for multiple threads.
        if self.create_unknown_user:
            user, created = UserModel._default_manager.get_or_create(**{
                UserModel.USERNAME_FIELD: username
            })
            if created:
                user = self.configure_user(user)
                user.save()
        else:
            try:
                user = UserModel._default_manager.get_by_natural_key(username)
            except UserModel.DoesNotExist:
                pass

        # Update user
        if request:
            user = self.update_user(request, user, save=True)

        # Return
        return user if self.user_can_authenticate(user) else None

    def configure_user(request, user):
        """Basic configuration for new user accounts"""
        # Set unusable password - LV-EM members can override this on the
        # managePassword page
        user.set_unusable_password()

        return user

    @classmethod
    def update_user(cls, request, user, save=True):
        """Updates a user with information from the Shibboleth session"""

        # Extract user data from shib session
        shib_user_attr = {}
        for user_attr, header in cls.attribute_map.items():
            value = request.META.get(header, None)
            if value:
                # Check if there are multiple entries; if so, take the first
                value = value.split(cls.attribute_delimiter)[0]
                shib_user_attr[user_attr] = value

        # Update user with attributes from the shib session only if there are
        # changes to the user's attributes
        if shib_user_attr and not min([getattr(user, k) == v for k, v in
            shib_user_attr.items()]):

            user.__dict__.update(**shib_user_attr)
            if save:
                user.save()

        return user
