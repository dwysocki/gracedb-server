#from guardian import backends
from django.contrib.auth import backends

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
