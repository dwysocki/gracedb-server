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
from core.utils import int_to_letters, letters_to_int
from events.models import Event, SignoffBase, VOEventBase, EMObservationBase, \
    EMFootprintBase
from core.utils import int_to_letters

import datetime
from cStringIO import StringIO
from hashlib import sha1
import os
import re

import logging

# Other setup
UserModel = get_user_model()
logger = logging.getLogger(__name__)


class Superevent(CleanSaveModel, ModelToDictMixin, AutoIncrementModel):
    """

    Superevent date-based IDs:
        Initially, a superevent has an ID like 'Syymmdd' (S180101)
        If there are multiple superevents on the same date, a letter prefix is
            added: S180101a, S180101b, etc., based on how many other
            superevents exist for the given date.
        Once a superevent is confirmed as a GW, its prefix is changed to 'GW'
            and its suffix is recalculated in terms of how many confirmed GWs
            exist for the given date. Ex: S180101b -> GW180101A
    """
    DEFAULT_ID_PREFIX = 'S'
    GW_ID_PREFIX = 'GW'
    ID_REGEX = r'(({0})(\d+)([a-z]*)|({1})(\d+)([A-Z]*))'.format(
        DEFAULT_ID_PREFIX, GW_ID_PREFIX)
    DATE_STR_FMT = '%y%m%d'
    AUTO_FIELD = 'base_date_number'
    AUTO_CONSTRAINT = 't_0_date'

    # Fields ------------------------------------------------------------------
    submitter = models.ForeignKey(UserModel)
    date_created = models.DateTimeField(auto_now_add=True)

    # One-to-one relationship with preferred event - an event can only be
    # preferred for a single superevent and a superevent can only have
    # one preferred event.
    preferred_event = models.OneToOneField(Event, null=False,
        on_delete=models.PROTECT, related_name='superevent_preferred_for')

    # Labels
    labels = models.ManyToManyField('events.label', through='Labelling')

    # Event time attributes
    t_start = models.DecimalField(max_digits=16, decimal_places=6, null=False,
        blank=False)
    t_0 = models.DecimalField(max_digits=16, decimal_places=6, null=False,
        blank=False)
    t_end = models.DecimalField(max_digits=16, decimal_places=6, null=False,
        blank=False)

    # Fields for handling date-based IDs
    t_0_date = models.DateField(null=False, editable=False)
    base_date_number = models.PositiveIntegerField(null=False, editable=False)
    base_letter_suffix = models.CharField(max_length=10, null=True,
        editable=False)
    gw_date_number = models.PositiveIntegerField(null=True, editable=False)
    gw_letter_suffix = models.CharField(max_length=10, null=True,
        editable=False)

    # Booleans
    is_gw = models.BooleanField(default=False)

    # Meta class --------------------------------------------------------------
    class Meta:
        ordering = ["-id"]
        unique_together = (('t_0_date', 'base_date_number'),
            ('t_0_date', 'gw_date_number'), ('t_0_date', 'base_letter_suffix'),
            ('t_0_date', 'gw_letter_suffix'),)

        # Extra permissions beyond the standard add, change, delete perms
        permissions = (
            ('view_superevent', 'Can view superevent'),
            ('confirm_gw_superevent', 'Can confirm as a superevent as a GW'),
        )

    # Class method overrides --------------------------------------------------
    def clean(self, *args, **kwargs):

        # External events can't be set as preferred events
        if (self.preferred_event and self.preferred_event.group.name ==
            settings.EXTERNAL_ANALYSIS_GROUP):
            raise ValidationError({'preferred_event':
                _('External event cannot be set as preferred')})

        super(Superevent, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Custom save method for handling autoincrement numbers and
        adding events
        """

        # Determine whether this is an insert or update - will be used for
        # deciding whether we need to calculate t_0_date and letter suffix
        pk_set = self._get_pk_val() is not None

        # Set t_0_date on insert
        if not pk_set:
            self.t_0_date = gpsToUtc(self.t_0).date()

        # Will do either base save (for updates) or auto_increment_insert
        # for new entries, to calculate base_date_number within the database
        super(Superevent, self).save(*args, **kwargs)

        # Update letter suffix from date number
        if not pk_set:
            if self.base_date_number == 1:
                # No letter suffix for only one superevent on a given date
                self.base_letter_suffix = ""
            else:
                self.base_letter_suffix = int_to_letters(self.base_date_number)
            self.save(update_fields=['base_letter_suffix'])

            # If a second superevent is found on a given date, update the first
            # one from that date to now use a letter suffix for the ID.
            if self.base_date_number == 2:
                first_for_date = self.__class__.objects.get(
                    t_0_date=self.t_0_date, base_date_number=1)
                first_for_date.base_letter_suffix = int_to_letters(
                    first_for_date.base_date_number)
                first_for_date.save(update_fields=['base_letter_suffix'])

        # Add preferred event to events list. Have to do this after base save
        # because the superevent needs a pk to be used as a foreign key in the
        # event table
        if (self.preferred_event and
            self.preferred_event not in self.events.all()):
            self.events.add(self.preferred_event)

    def confirm_as_gw(self):
        """
        Sets is_gw to True, calculates the gw_date_number in the database, and
        the gw_letter_suffix afterward.
        """
        # Set is_gw bool to True
        self.is_gw = True

        # Prep for custom autoincrement update
        meta = self._meta
        constraint_fields = ['t_0_date', 'is_gw']

        # Do the update
        self.auto_increment_update('gw_date_number', constraint_fields)

        # Update gw_letter_suffix from gw_date_number
        if self.gw_date_number == 1:
            # No letter suffix for only one confirmed GW on a given date
            self.gw_letter_suffix = ""
        else:
            self.gw_letter_suffix = int_to_letters(self.gw_date_number).upper()

        # Save the fields which have changed
        self.save(update_fields=['is_gw', 'gw_letter_suffix'])

        # If a second confirmed GW is found for a given date, update the first
        # one from that date to now use a letter suffix for the ID.
        if self.gw_date_number == 2:
            first_for_date = self.__class__.objects.get(is_gw=True,
                t_0_date=self.t_0_date, gw_date_number=1)
            first_for_date.gw_letter_suffix = int_to_letters(
                    first_for_date.gw_date_number).upper()
            first_for_date.save(update_fields=['gw_letter_suffix'])

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

    @classmethod
    def get_filter_kwargs_for_date_id_lookup(cls, date_id):
        """
        Takes in a superevent date id and gets the filter kwargs
        for looking it up using the default class manager's .get method.
        """

        # Try to get the prefix, date string, and letter suffix from the ID
        match = re.match(cls.ID_REGEX, date_id)
        if not match:
            raise ValueError(_('Superevent ID {0} does not have the correct '
                'format.'.format(date_id)))
        prefix, date_str, suffix = [g for g in match.groups()[1:]
            if g is not None]

        # Convert date string to a datetime.date object
        d = datetime.datetime.strptime(date_str, cls.DATE_STR_FMT).date()

        # Determine date_number from letter suffix
        if suffix == "":
            date_number = 1
        else:
            date_number = letters_to_int(suffix.lower())

        # Compile query kwargs
        q_kwargs = {'t_0_date': d}
        if prefix == cls.GW_ID_PREFIX:
            q_kwargs['is_gw'] = True
            date_number_key = 'gw_date_number'
        else:
            date_number_key = 'base_date_number'
        q_kwargs[date_number_key] = date_number

        return q_kwargs

    @classmethod
    def get_by_date_id(cls, date_id):
        """Get a superevent by its date-based ID"""
        q_kwargs = cls.get_filter_kwargs_for_date_id_lookup(date_id)
        return cls.objects.get(**q_kwargs)

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
        if self.is_gw:
            id_prefix = self.GW_ID_PREFIX
            letter_suffix = self.gw_letter_suffix
        else:
            id_prefix = self.DEFAULT_ID_PREFIX
            letter_suffix = self.base_letter_suffix

        return id_prefix + self.t_0_date.strftime(self.DATE_STR_FMT) + \
            letter_suffix

    # Custom methods ----------------------------------------------------------
    def get_external_events(self):
        """Returns a queryset of external events"""
        return self.events.filter(group__name=settings.EXTERNAL_ANALYSIS_GROUP)

    def get_internal_events(self):
        """Returns a queryset of internal events"""
        return self.events.exclude(group__name=
            settings.EXTERNAL_ANALYSIS_GROUP)

    def get_web_url(self):
        return reverse('superevents:view', args=[self.superevent_id])

    def get_api_url(self):
        raise NotImplemented
        #return reverse('')

    def __unicode__(self):
        return self.superevent_id

    class PreferredEventRemovalError(Exception):
        # To be raised when an attempt is made to remove the preferred event.
        pass

class Log(CleanSaveModel, LogBase, AutoIncrementModel):
    """
    Log message object attached to a Superevent. Uses the AutoIncrementModel
    to handle log enumeration on a per-Superevent basis.
    """
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINT = 'superevent'
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
    AUTO_CONSTRAINT = 'superevent'
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
    AUTO_CONSTRAINT = 'superevent'
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
    AUTO_CONSTRAINT = 'observation'
    observation = models.ForeignKey(EMObservation, null=False,
        on_delete=models.CASCADE)

    class Meta(EMFootprintBase.Meta):
        unique_together = (('observation', 'N'),)
