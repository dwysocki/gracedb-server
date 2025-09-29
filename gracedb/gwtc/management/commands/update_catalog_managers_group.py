from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from guardian.models import UserObjectPermission

from events.models import Pipeline

# Silence the annoying xray warnings:
if getattr(settings, 'ENABLE_AWS_XRAY', None):
    try:
        from aws_xray_sdk.core import xray_recorder
        xray_recorder.begin_segment("update-catalog-managers")
    except ModuleNotFoundError:
        print("aws_xray_sdk not found, skipping.")

# Define some stuff:
CM_GROUP = 'catalog_managers'
P_PERM = 'populate_pipeline'


class Command(BaseCommand):
    help="Add users with a populate_pipeline permission to the " \
         "catalog_managers group."

    def handle(self, *args, **options):

        print('Adding pipeline uploaders to catalog_managers group.')
    
        # Get the set of GW pipelines (exclude external pipelines):
        gw_pipelines = Pipeline.objects.exclude(
                           pipeline_type=Pipeline.PIPELINE_TYPE_EXTERNAL)
    
        # Get the list of integer pipeline id's to filter the UserObjectPermission
        # objects. NOTE: the object_pk type conversion: 
        # https://git.ligo.org/computing/gracedb/server/-/issues/346
        # Needs to happen before this gets run. 
        gw_ids = gw_pipelines.values_list('pk', flat=True)
    
        # Get the catalog managers group, and the set of the current user id's:
        cm = Group.objects.get(name=CM_GROUP)
        cm_user_ids = cm.user_set.values_list('id', flat=True)
    
        # get the pipeline content_type:
        ctype = ContentType.objects.get(app_label='events', model='pipeline')
    
        # get the populate_pipeline permission:
        p_perm = Permission.objects.get(codename=P_PERM)
    
        # Now get the UserObjectPermission set associated with the pipelines
        # and permissions. Check to see the type object_pk, and convert between
        # strings and integers as need be. ANNOYING.
        object_pk_type = type(UserObjectPermission.objects.filter(permission=p_perm,
                                 content_type=ctype).first().object_pk)

        if not isinstance(gw_ids[0], object_pk_type):
            gw_ids = [object_pk_type(s) for s in gw_ids]

        pipeline_perms = UserObjectPermission.objects.filter(permission=p_perm,
                             content_type=ctype, object_pk__in=gw_ids)
    
        # Now get a distinct list of the user ids associated with those perms:
        perm_user_ids = pipeline_perms.values_list('user__id', flat=True).distinct()
    
        # Now get the difference between the uploaders and the catalog managers:
        users_to_add = perm_user_ids.difference(cm_user_ids)

    
        # loop over and add the users:
        for uid in users_to_add:
            this_user = User.objects.get(id=uid)
            print(f'Adding {this_user} to catalog_managers')
            cm.user_set.add(this_user)
