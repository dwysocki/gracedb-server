from django.contrib.auth import get_user_model
from django.db import models

# Generic python stuff:
import logging
from django.core.validators import RegexValidator

# Import GraceDB stuff:
from api.utils import api_reverse
from core.models import AutoIncrementModel
from events.models import Event, Pipeline
from superevents.models import Superevent

# permissions stuff:
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

# Other setup
UserModel = get_user_model()
logger = logging.getLogger(__name__)

# Modify SlugField to allow for dots:
dot_slug_validator = RegexValidator(
    regex=r'^[a-zA-Z0-9._-]+$',
    message='Only letters, numbers, dots, underscores, and hyphens are allowed.'
)


class gwtc_catalog(AutoIncrementModel):
    # Catalog versioning fields:
    number = models.CharField(
        max_length=25,
        validators=[dot_slug_validator]
    )

    version = models.PositiveIntegerField(null=False)

    AUTO_FIELD = 'version'
    AUTO_CONSTRAINTS = ('number',)

    # Book-keeping fields:
    submitter = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    # Field for analyst comments:
    comment = models.TextField(blank=True)

    def __str__(self):
        return f'GWTC{self.number}, version {self.version}' 

    # Return the api url:
    @property
    def url(self):
        return api_reverse('gwtc:gwtc-version-detail',
                   args=(self.number, self.version))

    class Meta:
        ordering = ["-id"]
        unique_together = (
            ('number', 'version'),
        )
        indexes = [models.Index(fields=['number', ]), 
                   models.Index(fields=['version', ]),]

        default_permissions = ('add', 'view', 'delete')

class gwtc_superevent(models.Model):
    superevent = models.ForeignKey(Superevent, on_delete=models.CASCADE)
    gwtc_catalog = models.ForeignKey(gwtc_catalog, on_delete=models.CASCADE)
    far = models.FloatField(null=True)
    pastro = models.JSONField(null=True)

    def __str__(self):
        return f'{self.superevent.superevent_id} in ' \
               f'GWTC{self.gwtc_catalog.number}, version {self.gwtc_catalog.version}'

    class Meta:
        ordering = ["-id"]
        unique_together = (
            ('superevent', 'gwtc_catalog'),
        )
        # TODO: create custom index when we decide on pastro
        # key names
        indexes = [models.Index(fields=['far', ]), ]
        default_permissions = ('add', 'view', 'delete')

class gwtc_gevent(models.Model):
    gwtc_catalog = models.ForeignKey(gwtc_catalog, on_delete=models.CASCADE)
    gwtc_superevent = models.ForeignKey(gwtc_superevent, on_delete=models.CASCADE)
    gevent = models.ForeignKey(Event, on_delete=models.CASCADE)
    pipeline = models.ForeignKey(Pipeline, on_delete=models.CASCADE)

    def __str__(self):
        return f'{self.gevent.graceid} in ' \
               f'GWTC{self.gwtc_catalog.number}, version {self.gwtc_catalog.version}'

    class Meta:
        ordering = ["-id"]
        unique_together = (
            ('gwtc_superevent', 'gevent', 'pipeline'),
        )
        default_permissions = ('add', 'view', 'delete')

class gwtc_catalog_groupobjectpermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(gwtc_catalog, on_delete=models.CASCADE)

    class Meta(GroupObjectPermissionBase.Meta):

        default_permissions = ('add', 'view', 'delete')

        permissions = (
            ('view_gwtc_cataloggroupobjectpermission',
                'Can view gwtc_cataloggroupobjectpermission'),
        )

class gwtc_catalog_userobjectpermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(gwtc_catalog, on_delete=models.CASCADE)

