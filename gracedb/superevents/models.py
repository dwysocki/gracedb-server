from django.db import models, IntegrityError
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from core.models import CleanSaveModel, AutoIncrementModel
from core.models import LogBase, m2mThroughBase
from core.models import ModelToDictMixin
from core.time_utils import posixToGpsTime, gpsToUtc
from events.models import Event, SignoffBase, VOEventBase, EMObservationBase, \
    EMFootprintBase
from core.utils import int_to_letters

from cStringIO import StringIO
from hashlib import sha1
import os

import logging

# Other setup
UserModel = get_user_model()
logger = logging.getLogger(__name__)


class Superevent(CleanSaveModel, ModelToDictMixin):
    ID_PREFIX = 'S'

    # Fields ------------------------------------------------------------------
    submitter = models.ForeignKey(UserModel)
    date_created = models.DateTimeField(auto_now_add=True)

    # One-to-one relationship with preferred event - an event can only be
    # preferred for a single superevent and a superevent can only have
    # one preferred event. Ideally, this wouldn't be nullable, but it makes
    # the logic a lot easier to handle.  We will just have to check whether
    # self.preferred_event is None in some cases.
    preferred_event = models.OneToOneField(Event, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='superevent_preferred_for')

    # Labels
    labels = models.ManyToManyField('events.label', through='Labelling')

    # Event time attributes
    t_start = models.DecimalField(max_digits=16, decimal_places=6, null=False,
        blank=False)
    t_0 = models.DecimalField(max_digits=16, decimal_places=6, null=False,
        blank=False)
    t_end = models.DecimalField(max_digits=16, decimal_places=6, null=False,
        blank=False)

    # Meta class --------------------------------------------------------------
    class Meta:
        ordering = ["-id"]

        # Extra permissions beyond the standard add, change, delete perms
        permissions = (('view_superevent', 'Can view superevent'),)

    # Class method overrides --------------------------------------------------
    def clean(self, *args, **kwargs):

        # External events can't be set as preferred events
        if (self.preferred_event and self.preferred_event.group.name ==
            settings.EXTERNAL_ANALYSIS_GROUP):
            raise ValidationError({'preferred_event':
                _('External event cannot be set as preferred')})

        super(Superevent, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        """Custom save method for handling date_id and preferred event"""

        # Only modify date_id if pk is not already set (i.e. this is an INSERT)
        #pk_set = self._get_pk_val() is not None
        #if not pk_set:
        #    if self.date_id:
        #        raise Exception('ERROR')

        #    # Find an attached event with a gpstime to get the date;
        #    # try preferred event first, of course.
        #    if self.preferred_event:
        #        
        #    else:
        #        # Get other superevents from this date to increment id

        # Do base class save
        super(Superevent, self).save(*args, **kwargs)

        # Have to do this after save because the superevent needs a pk
        # to be used as a foreign key in the event table
        if (self.preferred_event and
            self.preferred_event not in self.events.all()):
            self.events.add(self.preferred_event)

    def get_absolute_url(self):
        return self.get_web_url()

    def list_files(self, absolute_paths=True):
        if absolute_paths:
            file_list = [os.path.join(dir_name, file_name) for (dir_name, _,
                file_names) in os.walk(self.datadir) for file_name in
                file_names]
        else:
            file_list = [os.path.relpath(os.path.join(dir_name, file_name),
                self.datadir) for (dir_name, _, file_names) in os.walk(
                self.datadir) for file_name in file_names]
        return file_list

    def default_dict_mapping(self):
        # Used by ModelToDictMixin to generate dict from model
        mapping = {
            'submitter': self.submitter.username,
            'preferred_event': self.preferred_event.graceid(),
            'gw_events': {
                self.QS_KEY: self.get_internal_events(),
                self.QS_PROP_KEY: 'graceid',
            },
            'em_events': {
                self.QS_KEY: self.get_external_events(),
                self.QS_PROP_KEY: 'graceid',
            },
            'labels': {
                self.QS_KEY: self.labels.all(),
                self.QS_PROP_KEY: 'name',
            },
        }
        return mapping

    # Properties --------------------------------------------------------------
    @property
    def datadir(self):
        """
        Mostly taken from events.models.Event.datadir
        """
        # Create a file-like object which is the SHA-1 hexdigest of the
        # object's primary key. We prepend 'superevent' so as to not
        # have collisions with Event files
        hash_input = 'superevent' + str(self.id)
        hdf = StringIO(sha1(hash_input).hexdigest())

        # Build up the nodes of the directory structure
        nodes = [hdf.read(i) for i in settings.GRACEDB_DIR_DIGITS]

        # Read whatever is left over. This is the 'leaf' directory.
        nodes.append(hdf.read())
        return os.path.join(settings.GRACEDB_DATA_DIR, *nodes)

    @property
    def superevent_id(self):
        return self.superevent_basic_id
        # Really, really temporary and not good at all
        # Plan:
        #   Convert event gpstimes to datetime fields
        #   store gpstime as a property
        #   Use datetime field to determine number for the day in question
        #filter_dict = {
        #    'date_created__year': self.date_created.year,
        #    'date_created__month': self.date_created.month,
        #    'date_created__day': self.date_created.day,
        #}
        #obj_set = self.__class__.objects.filter(**filter_dict).order_by('date_created')
        #day_number = list(obj_set).index(self)
        #suffix = int_to_letters(day_number+1)
        #event_time_UTC = gpsToUtc(self.preferred_event.gpstime)
        #return self.ID_PREFIX + event_time_UTC.strftime('%y%m%d') + suffix

    @property
    def superevent_basic_id(self):
        return self.ID_PREFIX + '{0:0>4}'.format(self.id)

    # Custom methods ----------------------------------------------------------
    def get_external_events(self):
        """Returns a queryset of external events"""
        return self.events.filter(group__name=settings.EXTERNAL_ANALYSIS_GROUP)

    def get_internal_events(self):
        """Returns a queryset of internal events"""
        return self.events.exclude(group__name=
            settings.EXTERNAL_ANALYSIS_GROUP)

    #def get_by_superevent_id(self):
    #    pass

    def get_web_url(self):
        return reverse('superevents:view', args=[self.superevent_id])

    def get_api_url(self):
        raise NotImplemented
        #return reverse('')

    def __unicode__(self):
        return self.superevent_id


class Log(CleanSaveModel, LogBase, AutoIncrementModel):
    """
    Log message object attached to a Superevent. Uses the AutoIncrementModel
    to handle log enumeration on a per-Superevent basis.
    """
    AUTO_FIELD = 'N'
    AUTO_FK = 'superevent'
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)
    tags = models.ManyToManyField('events.Tag', related_name='superevent_logs')

    class Meta(LogBase.Meta):
        unique_together = (('superevent', 'N'),)

    def get_full_file_path(self):
        # TODO: add file_version?
        return os.path.join(self.superevent.datadir, self.filename)

    def fileurl(self):
        # TODO: implement this
        super(Log, self).fileurl()


class Labelling(m2mThroughBase):
    """
    Model which provides the 'through' relationship between Superevents and
    Labels.

    We use the Label model from the events app since it's set up already and 
    provides exactly what we need, so no reason to create a redundant model.
    """
    class Meta:
        unique_together = (('superevent', 'label'),)

    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)

    # Labels are connected to Events and Superevents.  Currently,
    # Label.labelling_set points to the Labelling object which connects the
    # Label to an Event.  So we need a different name for this Labelling object
    # which connects a Label to a Superevent.
    label = models.ForeignKey('events.Label', null=False,
        related_name='%(app_label)s_%(class)s_set',
        on_delete=models.CASCADE)


class Signoff(CleanSaveModel, SignoffBase):
    """Class for superevent signoffs"""
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)

    class Meta:
        unique_together = (('superevent', 'instrument'),)

    def __unicode__(self):
        return "{superevent_id} | {instrument} | {status}".format(
            superevent_id=self.superevent.superevent_id,
            instrument=self.instrument, status=self.status)


class VOEvent(CleanSaveModel, VOEventBase, AutoIncrementModel):
    """VOEvent class for superevents"""
    AUTO_FIELD = 'N'
    AUTO_FK = 'superevent'
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)

    class Meta(VOEventBase.Meta):
        unique_together = (('superevent', 'N'),)

    def fileurl(self):
        # TODO: implement this
        super(Log, self).fileurl()


class EMObservation(CleanSaveModel, EMObservationBase, AutoIncrementModel):
    """EMObservation class for superevents"""
    AUTO_FIELD = 'N'
    AUTO_FK = 'superevent'
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)

    class Meta(EMObservationBase.Meta):
        unique_together = (('superevent', 'N'),)

    def __unicode__(self):
        return "{superevent_id} | {group} | {N}".format(
            superevent_id=self.superevent.superevent_id,
            group=self.group.name, N=self.N)

    def calculateCoveringRegion(self):
        footprints = self.emfootprint_set.all()
        super(EMObservation, self).calculateCoveringRegion(footprints)


class EMFootprint(CleanSaveModel, EMFootprintBase, AutoIncrementModel):
    """EMFootprint class for superevent EMObservations"""
    AUTO_FIELD = 'N'
    AUTO_FK = 'observation'
    observation = models.ForeignKey(EMObservation, null=False,
        on_delete=models.CASCADE)

    class Meta(EMFootprintBase.Meta):
        unique_together = (('observation', 'N'),)
