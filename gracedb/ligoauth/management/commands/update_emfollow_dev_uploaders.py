from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group, Permission
from django.contrib.contenttypes.models import ContentType
from guardian.models import UserObjectPermission

from events.models import Pipeline
from ligoauth.utils import add_user_to_pipeline_uploaders, get_pipeline_uploaders

# Silence the annoying xray warnings:
if getattr(settings, 'ENABLE_AWS_XRAY', None):
    try:
        from aws_xray_sdk.core import xray_recorder
        xray_recorder.begin_segment("update-catalog-managers")
    except ModuleNotFoundError:
        print("aws_xray_sdk not found, skipping.")

# Define some stuff:
EM_GROUP = 'emfollow_devs'
SM_GROUP = 'superevent_managers'

class Command(BaseCommand):
    help="Grant pipeline upload permission to users in the " \
         "emfollow_dev group."

    def handle(self, *args, **options):

        print('Updating pipeline uploaders with emfollow_dev users')

        # Get the set of users in the emfollow_dev and
        # superevent_managers groups:
        em_devs = Group.objects.get(name=EM_GROUP).user_set.all() | \
                  Group.objects.get(name=SM_GROUP).user_set.all()

        for pipe in Pipeline.objects.all():

            # Get the current list of pipeline uploader:
            p_uploaders = get_pipeline_uploaders(pipe)

            for u in em_devs.difference(p_uploaders):
                add_user_to_pipeline_uploaders(u, pipe)
