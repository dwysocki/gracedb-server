from django.conf import settings
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group

# Silence the annoying xray warnings:
if getattr(settings, 'ENABLE_AWS_XRAY', None):
    try:
        from aws_xray_sdk.core import xray_recorder
        xray_recorder.begin_segment("update-access-managers")
    except ModuleNotFoundError:
        print("aws_xray_sdk not found, skipping.")

# Define group names:
EM_GROUP = 'emfollow_devs'
SM_GROUP = 'superevent_managers'
ACCESS_GROUP = 'access_managers'


class Command(BaseCommand):
    help = "Add users from superevent_managers and emfollow_devs groups " \
           "to the access_managers group."

    def handle(self, *args, **options):

        print('Updating access_managers with superevent_managers and emfollow_devs users')

        # Get the access_managers group
        try:
            access_managers = Group.objects.get(name=ACCESS_GROUP)
        except Group.DoesNotExist:
            print(f"Error: '{ACCESS_GROUP}' group does not exist.")
            return

        # Get the set of users in the emfollow_devs and superevent_managers groups
        users_to_add = set()

        try:
            em_devs = Group.objects.get(name=EM_GROUP).user_set.all()
            users_to_add.update(em_devs)
            print(f"Found {em_devs.count()} users in {EM_GROUP}")
        except Group.DoesNotExist:
            print(f"Warning: '{EM_GROUP}' group does not exist, skipping.")

        try:
            sm_users = Group.objects.get(name=SM_GROUP).user_set.all()
            users_to_add.update(sm_users)
            print(f"Found {sm_users.count()} users in {SM_GROUP}")
        except Group.DoesNotExist:
            print(f"Warning: '{SM_GROUP}' group does not exist, skipping.")

        # Add users to access_managers group
        added_count = 0
        for user in users_to_add:
            if not access_managers.user_set.filter(pk=user.pk).exists():
                access_managers.user_set.add(user)
                print(f"  Added {user.username} to {ACCESS_GROUP}")
                added_count += 1

        print(f"Done. Added {added_count} users to {ACCESS_GROUP}.")
