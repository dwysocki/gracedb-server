try:
    from StringIO import StringIO
except ImportError:  # python >= 3
    from io import StringIO
import datetime
from hashlib import sha1
import logging
import os
import pytz
import re
import shutil

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as AuthGroup
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import models, IntegrityError
from django.urls import reverse
from django.utils import six
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import ugettext_lazy as _

from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from core.models import CleanSaveModel, AutoIncrementModel, LogBase, \
    m2mThroughBase
from core.time_utils import posixToGpsTime, gpsToUtc
from core.utils import int_to_letters, letters_to_int
from events.models import Event, SignoffBase, VOEventBase, EMObservationBase, \
    EMFootprintBase

# Other setup
UserModel = get_user_model()
logger = logging.getLogger(__name__)

# Dates for allowed superevent date ranges (all t_0 values should be
# START <= t_0 < END)
SUPEREVENT_DATE_START = datetime.datetime(1980, 1, 1, 0, 0, 0, 0, pytz.utc)
SUPEREVENT_DATE_END = datetime.datetime(2080, 1, 1, 0, 0, 0, 0, pytz.utc)


@python_2_unicode_compatible
class Superevent(CleanSaveModel, AutoIncrementModel):
    """
    Superevent date-based IDs:
        Initially, a superevent has an ID like 'S180725a'
        Once a superevent is confirmed as a GW, its prefix is changed to 'GW'
            and its suffix is recalculated in terms of how many confirmed GWs
            exist for the given date. Ex: S180101b -> GW180101A
    """
    # Superevent types
    SUPEREVENT_CATEGORY_PRODUCTION = 'P'
    SUPEREVENT_CATEGORY_TEST = 'T'
    SUPEREVENT_CATEGORY_MDC = 'M'
    SUPEREVENT_CATEGORY_CHOICES = (
        (SUPEREVENT_CATEGORY_PRODUCTION, 'Production'),
        (SUPEREVENT_CATEGORY_TEST, 'Test'),
        (SUPEREVENT_CATEGORY_MDC, 'MDC'),
    )

    # Prefixes
    DEFAULT_ID_PREFIX = 'S'
    GW_ID_PREFIX = 'GW'

    # Format for date string in date-based ID
    DATE_STR_FMT = '%y%m%d'

    # Full date-based ID regex:
    # (T|M)?S180709abc OR (T|M)?GW180709ABC
    ID_REGEX = (r'(({test}|{mdc})?({0})(\d{{6}})([a-z]+)|'
        '({test}|{mdc})?({1})(\d{{6}})([A-Z]+))').format(DEFAULT_ID_PREFIX,
        GW_ID_PREFIX, test=SUPEREVENT_CATEGORY_TEST,
        mdc=SUPEREVENT_CATEGORY_MDC)

    # Auto-increment save fields
    AUTO_FIELD = 'base_date_number'
    AUTO_CONSTRAINTS = ('t_0_date', 'category',)

    # Fields ------------------------------------------------------------------
    submitter = models.ForeignKey(UserModel, on_delete=models.CASCADE)
    created = models.DateTimeField(auto_now_add=True)

    # Type of superevent (Production, Test, MDC)
    category = models.CharField(max_length=1, null=False, blank=False,
        choices=SUPEREVENT_CATEGORY_CHOICES,
        default=SUPEREVENT_CATEGORY_PRODUCTION)

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
    base_letter_suffix = models.CharField(max_length=10, null=False,
        editable=False)
    gw_date_number = models.PositiveIntegerField(null=True, editable=False)
    gw_letter_suffix = models.CharField(max_length=10, null=True,
        editable=False)

    # Booleans
    is_gw = models.BooleanField(default=False)
    # Because there are multiple actions/permissions involved with exposing a
    # superevent, we are going to use a database field to track it.
    is_exposed = models.BooleanField(default=False)

    # New O3b fields for RAVEN:
    coinc_far = models.FloatField(null=True, blank=True)
    em_type = models.CharField(blank=True, null=True, max_length=100)

    # Meta class --------------------------------------------------------------
    class Meta:
        ordering = ["-id"]
        unique_together = (
            ('t_0_date', 'base_date_number', 'category'),
            ('t_0_date', 'gw_date_number', 'category'),
            ('t_0_date', 'base_letter_suffix', 'category'),
            ('t_0_date', 'gw_letter_suffix', 'category'),
        )

        # Extra permissions beyond the standard add, change, delete perms
        permissions = (
            ('add_test_superevent', 'Can add test superevent'),
            ('add_mdc_superevent', 'Can add MDC superevent'),
            ('change_test_superevent', 'Can change test superevent'),
            ('change_mdc_superevent', 'Can change MDC superevent'),
            ('confirm_gw_superevent', 'Can confirm superevent as GW'),
            ('confirm_gw_test_superevent', 'Can confirm test superevent as '
                'GW'),
            ('confirm_gw_mdc_superevent', 'Can confirm MDC superevent as GW'),
            ('annotate_superevent', 'Can add log messages and '
                'EM observation data to superevent'),
            ('expose_superevent', 'Can expose a superevent to be viewed by '
                'external users'),
            ('hide_superevent', 'Can hide a superevent from external users'),
            #('view_superevent', 'Can view superevent'),
        )

    # Class method overrides --------------------------------------------------
    def clean(self, *args, **kwargs):

        # External events can't be set as preferred events
        if (self.preferred_event and self.preferred_event.group.name ==
            settings.EXTERNAL_ANALYSIS_GROUP):
            raise ValidationError({'preferred_event':
                _('External event cannot be set as preferred')})

        # FIXME: someone will have to deal with this in 2080
        # Make sure t_0 is in the appropriate range [1980 - 2079)
        # We do this in UTC since the GPS time of the end of ths range could
        # change as leap seconds are added
        t_0_UTC = gpsToUtc(self.t_0)
        if (t_0_UTC < SUPEREVENT_DATE_START or t_0_UTC >= SUPEREVENT_DATE_END):
            raise ValidationError({'t_0':
                _('t_0 out of range: we require that {start} <= t_0 < {end}' \
                .format(start=SUPEREVENT_DATE_START.__str__(),
                end=SUPEREVENT_DATE_END.__str__()))})

        # Set t_0_date on insert
        if self._get_pk_val() is None:
            self.t_0_date = t_0_UTC.date()

        super(Superevent, self).clean(*args, **kwargs)

    def save(self, *args, **kwargs):
        """
        Custom save method for managing date-based IDs
        """

        # Determine whether this is an insert or update - will be used for
        # deciding whether we need to calculate t_0_date and letter suffix
        pk_set = self._get_pk_val() is not None

        # Will do either base save (for updates) or auto_increment_insert
        # for new entries, to calculate base_date_number within the database
        super(Superevent, self).save(*args, **kwargs)

        # Update letter suffix from date number
        if not pk_set:
            self.base_letter_suffix = int_to_letters(self.base_date_number)
            self.save(update_fields=['base_letter_suffix'])

        # Add preferred event to events list. Have to do this after base save
        # because the superevent needs a pk to be used as a foreign key in the
        # event table
        if (self.preferred_event and
            self.preferred_event not in self.events.all()):
            self.events.add(self.preferred_event)

    def delete(self, purge=True, *args, **kwargs):
        # Store datadir before deletion from database
        datadir = self.datadir

        # Call base class delete
        super(Superevent, self).delete(*args, **kwargs)

        if purge:
            # GOPs are deleted automatically since we have a special class
            # for them that is attached directly to the superevent

            # Delete data directory
            if os.path.isdir(datadir):
                shutil.rmtree(datadir)

    def event_compatible(self, event):
        """
        Check whether an event is of the correct type to be part of this
        superevent
        """
        return self.__class__.event_category_check(event, self.category)

    @classmethod
    def event_category_check(cls, event, superevent_category):
        """
        Given a superevent type, check whether an event could be added to such
        a superevent
        """
        if (superevent_category == cls.SUPEREVENT_CATEGORY_TEST and
            not event.is_test()):
            return False
        elif (superevent_category == cls.SUPEREVENT_CATEGORY_MDC and
              not event.is_mdc()):
            return False
        elif (superevent_category == cls.SUPEREVENT_CATEGORY_PRODUCTION and
              (event.is_test() or event.is_mdc())):
            return False
        else:
            return True

    def is_production(self):
        return self.category == self.SUPEREVENT_CATEGORY_PRODUCTION

    def is_test(self):
        return self.category == self.SUPEREVENT_CATEGORY_TEST

    def is_mdc(self):
        return self.category == self.SUPEREVENT_CATEGORY_MDC

    def confirm_as_gw(self):
        """
        Sets is_gw to True, calculates the gw_date_number in the database, and
        the gw_letter_suffix afterward.
        """
        # Set is_gw bool to True
        self.is_gw = True

        # Prep for custom autoincrement update
        meta = self._meta
        constraint_fields = ['t_0_date', 'is_gw', 'category']

        # Do the update
        self.auto_increment_update('gw_date_number', constraint_fields)

        # Update gw_letter_suffix from gw_date_number
        self.gw_letter_suffix = int_to_letters(self.gw_date_number).upper()

        # Save the fields which have changed
        self.save(update_fields=['is_gw', 'gw_letter_suffix'])

    def get_groups_with_groupobjectpermissions(self):
        gops = self.supereventgroupobjectpermission_set.all()
        gop_group_pks = gops.values_list('group', flat=True).distinct()
        return AuthGroup.objects.filter(pk__in=gop_group_pks)

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

    @classmethod
    def get_filter_kwargs_for_date_id_lookup(cls, date_id):
        """
        Takes in a superevent date id and gets the filter kwargs
        for looking it up using the default class manager's .get method.
        """

        # Try to get the prefix, date string, and letter suffix from the ID
        match = re.match(cls.ID_REGEX, date_id)
        if not match:
            raise cls.DateIdError(_('Superevent ID {0} does not have the '
                'correct format.'.format(date_id)))
        # Match should have 9 groups: full match, then 4 matches to default
        # ID, or 4 matches to GW ID.  So we either want groups 2-5 or 6-9.
        if any(match.groups()[1:5]):
            grps = match.groups()[1:5]
        else:
            grps = match.groups()[5:]
        preprefix, prefix, date_str, suffix = grps

        # Convert date string to a datetime.date object
        try:
            d = datetime.datetime.strptime(date_str, cls.DATE_STR_FMT).date()
        except ValueError as e:
            # Catch error for bad date string (i.e., month=13 or something)
            raise cls.DateIdError(_('Bad superevent date string.'))

        # FIXME: someone will have to deal with this in 2080
        # Safety check for 2 digit years: enforce year range of [1980 - 2079),
        # since GPS time starts in 1980. datetime.datetime.strptime follows
        # the POSIX standard for 2 digit years with a range of 1969-2068.
        # We also enforce this range for t_0 in Superevent.clean()
        if (d.year >= SUPEREVENT_DATE_END.year or 
            d.year < SUPEREVENT_DATE_START.year):

            yr_tens = d.year % 100
            if yr_tens >= 80:
                replace_yr = 1900 + yr_tens
            else:
                replace_yr = 2000 + yr_tens
            d = d.replace(year=replace_yr)

        # Determine date_number from letter suffix
        date_number = letters_to_int(suffix.lower())

        # Compile query kwargs - we don't have to be too careful here
        # since the regex match above will filter out any issues
        q_kwargs = {'t_0_date': d}
        # Get category from preprefix
        if preprefix:
            q_kwargs['category'] = preprefix
        else:
            q_kwargs['category'] = cls.SUPEREVENT_CATEGORY_PRODUCTION

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
        hdf = StringIO(sha1(hash_input.encode()).hexdigest())

        # Build up the nodes of the directory structure
        nodes = [hdf.read(i) for i in settings.GRACEDB_DIR_DIGITS]

        # Read whatever is left over. This is the 'leaf' directory.
        nodes.append(hdf.read())
        return os.path.join(settings.GRACEDB_DATA_DIR, *nodes)

    @property
    def superevent_id(self):
        if self.is_gw:
            return self.gw_id
        else:
            return self.default_superevent_id

    @property
    def default_superevent_id(self):
        id_prefix = self.DEFAULT_ID_PREFIX
        letter_suffix = self.base_letter_suffix

        # Prepend category prefix (if not production)
        pre_prefix = ""
        if self.category != self.SUPEREVENT_CATEGORY_PRODUCTION:
            pre_prefix = self.category

        return pre_prefix + self.DEFAULT_ID_PREFIX + \
            self.t_0_date.strftime(self.DATE_STR_FMT) + self.base_letter_suffix

    @property
    def gw_id(self):
        if not self.is_gw:
            return None

        # Prepend category prefix (if not production)
        pre_prefix = ""
        if self.category != self.SUPEREVENT_CATEGORY_PRODUCTION:
            pre_prefix = self.category

        return pre_prefix + self.GW_ID_PREFIX + \
            self.t_0_date.strftime(self.DATE_STR_FMT) + self.gw_letter_suffix

    @property
    def graceid(self):
        """Alias for superevent_id"""
        return self.superevent_id

    @property
    def gpstime(self):
        """Alias for t_0"""
        return self.t_0

    @property
    def far(self):
        """Alias the FAR from the preferred_event"""
        return self.preferred_event.far

    # Custom methods ----------------------------------------------------------
    def get_external_events(self, related_fields=['group']):
        """Returns a queryset of external events"""
        return self.events.filter(
            group__name=settings.EXTERNAL_ANALYSIS_GROUP) \
            .select_related(*related_fields)

    def get_internal_events(self, related_fields=['group']):
        """Returns a queryset of internal events"""
        return self.events.exclude(
            group__name=settings.EXTERNAL_ANALYSIS_GROUP) \
            .select_related(*related_fields)

    def get_web_url(self):
        return reverse('superevents:view', args=[self.superevent_id])

    def get_api_url(self):
        raise NotImplemented
        #return reverse('')

    def __str__(self):
        return six.text_type(self.superevent_id)

    class DateIdError(Exception):
        # To be raised when the superevent date ID is in a bad format; i.e.,
        # one that datetime can't parse or that the regex won't match
        pass

    class EventCategoryMismatchError(Exception):
        # To be raised when an attempt is made to add an event with an
        # incompatible category
        pass

# Classes for direct foreign key lookups of permissions. Should
# increase speed and efficiency of permission lookups.
# view_superevent and annotate_superevent will be assigned on a
# row-level basis
class SupereventGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Superevent, on_delete=models.CASCADE)

    class Meta(GroupObjectPermissionBase.Meta):
        permissions = (
            #('view_supereventgroupobjectpermission',
            #    'Can view superevent groupobjectpermission'),
        )

class SupereventUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Superevent, on_delete=models.CASCADE)


class Log(CleanSaveModel, LogBase, AutoIncrementModel):
    """
    Log message object attached to a Superevent. Uses the AutoIncrementModel
    to handle log enumeration on a per-Superevent basis.
    """
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('superevent',)
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)
    tags = models.ManyToManyField('events.Tag', related_name='superevent_logs')

    class Meta(LogBase.Meta):
        unique_together = (('superevent', 'N'),)
        permissions = (
            ('expose_log', 'Can expose a log to be viewed by external users'),
            ('hide_log', 'Can hide a log from external users'),
            ('tag_log', 'Add tag to log'),
            ('untag_log', 'Remove tag from log'),
            #('view_log', 'Can view log'),
        )

    def get_full_file_path(self):
        return os.path.join(self.superevent.datadir, self.versioned_filename)

    def fileurl(self):
        return reverse("api:default:superevents:superevent-file-detail",
            args=[self.superevent.superevent_id, self.versioned_filename])


# Classes for direct foreign key lookups of permissions. Should
# increase speed and efficiency of permission lookups.
# view_log will be assigned on a row-level basis.
class LogGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(Log, on_delete=models.CASCADE)

class LogUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(Log, on_delete=models.CASCADE)


@python_2_unicode_compatible
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

    def __str__(self):
        return six.text_type(
            "{superevent_id} | {label}".format(
                superevent_id=self.superevent.superevent_id,
                label=self.label.name
            )
        )


@python_2_unicode_compatible
class Signoff(CleanSaveModel, SignoffBase):
    """Class for superevent signoffs"""
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)

    class Meta:
        unique_together = (('superevent', 'instrument'),)
        permissions = (
            #('view_signoff', 'Can view signoff'),
            ('do_H1_signoff', 'Can interact with H1 signoffs'),
            ('do_L1_signoff', 'Can interact with L1 signoffs'),
            ('do_V1_signoff', 'Can interact with V1 signoffs'),
            ('do_adv_signoff', 'Can interact with advocate signoffs'),
        )

    def __str__(self):
        return six.text_type(
            "{superevent_id} | {instrument} | {status}".format(
                superevent_id=self.superevent.superevent_id,
                instrument=self.instrument,
                status=self.status
            )
        )


class VOEvent(VOEventBase, AutoIncrementModel):
    """VOEvent class for superevents"""
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('superevent',)
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)

    class Meta(VOEventBase.Meta):
        unique_together = (('superevent', 'N'),)

    def fileurl(self):
        # TODO: implement this
        super(Log, self).fileurl()


@python_2_unicode_compatible
class EMObservation(CleanSaveModel, EMObservationBase, AutoIncrementModel):
    """EMObservation class for superevents"""
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('superevent',)
    superevent = models.ForeignKey(Superevent, null=False,
        on_delete=models.CASCADE)

    class Meta(EMObservationBase.Meta):
        unique_together = (('superevent', 'N'),)

    def __str__(self):
        return six.text_type(
            "{superevent_id} | {group} | {N}".format(
                superevent_id=self.superevent.superevent_id,
                group=self.group.name,
                N=self.N
            )
        )

    def calculateCoveringRegion(self):
        footprints = self.emfootprint_set.all()
        super(EMObservation, self).calculateCoveringRegion(footprints)


class EMFootprint(CleanSaveModel, EMFootprintBase, AutoIncrementModel):
    """EMFootprint class for superevent EMObservations"""
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('observation',)
    observation = models.ForeignKey(EMObservation, null=False,
        on_delete=models.CASCADE)

    class Meta(EMFootprintBase.Meta):
        unique_together = (('observation', 'N'),)
