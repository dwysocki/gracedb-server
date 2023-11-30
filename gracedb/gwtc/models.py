from django.contrib.auth import get_user_model
from django.db import models

# Generic python stuff:
import logging

# Import GraceDB stuff:
from core.models import AutoIncrementModel
from events.models import Event, Pipeline
from superevents.models import Superevent

# permissions stuff:
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

# Other setup
UserModel = get_user_model()
logger = logging.getLogger(__name__)



class gwtc_catalog(AutoIncrementModel):
    # Catalog versioning fields:
    number = models.SlugField(null=False, max_length=50)
    version = models.PositiveIntegerField(null=False)

    AUTO_FIELD = 'version'
    AUTO_CONSTRAINTS = ('number',)

    # Book-keeping fields:
    submitter = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'GWTC{self.number}, version {self.version}' 

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

    def __str__(self):
        return f'{self.superevent.superevent_id} in ' \
               f'GWTC{self.gwtc_catalog.number}, version {self.gwtc_catalog.version}'

    class Meta:
        ordering = ["-id"]
        unique_together = (
            ('superevent', 'gwtc_catalog'),
        )
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

