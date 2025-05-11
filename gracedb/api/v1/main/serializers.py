from __future__ import absolute_import
import logging

from django.conf import settings
from django.contrib.auth import get_user_model

from ligoauth.utils import get_pipeline_perms_for_user
from rest_framework import fields, serializers

# Set up user model
UserModel = get_user_model()

# Set up logger
logger = logging.getLogger(__name__)


class UserSerializer(serializers.ModelSerializer):
    is_internal_user = fields.SerializerMethodField(read_only=True)
    upload_to_pipeline = fields.SerializerMethodField(read_only=True)
    #permissions = fields.SerializerMethodField(read_only=True)

    class Meta:
        model = UserModel
        # Add permissions later.  It will just be confusing now because
        # they are not implemented properly for the events app.
        fields = ('username', 'first_name', 'last_name', 'email',
            'is_internal_user', 'upload_to_pipeline')

    def get_is_internal_user(self, obj):
        # Is the user in the LVC?
        return obj.groups.filter(name=settings.LVC_GROUP).exists()

    def get_upload_to_pipeline(self, obj):
        return [pipe.name for pipe in get_pipeline_perms_for_user(obj)]
