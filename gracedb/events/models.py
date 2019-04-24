from math import isnan
import numbers

from django.db import models, IntegrityError
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from model_utils.managers import InheritanceManager

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType

from guardian.models import GroupObjectPermission
import logging; log = logging.getLogger(__name__)

import os
import glue
import glue.ligolw
import glue.ligolw.utils
import glue.ligolw.table
import glue.ligolw.lsctables
from glue.ligolw.ligolw import LIGOLWContentHandler
from glue.lal import LIGOTimeGPS

import json, re

from core.models import AutoIncrementModel, CleanSaveModel
from core.models import LogBase, m2mThroughBase
from core.time_utils import posixToGpsTime

from django.conf import settings
import pytz
import calendar

try:
    from io import StringIO
except ImportError:  # python < 3
    from cStringIO import StringIO

from hashlib import sha1
import shutil

from .managers import ProductionPipelineManager, ExternalPipelineManager


UserModel = get_user_model()

SERVER_TZ = pytz.timezone(settings.TIME_ZONE)

# Let's say we start here on schema versions
#
# 1.0 -> 1.1   changed EventLog.comment from CharField(length=200) -> TextField
#
schema_version = "1.1"

#class User(models.Model):
    #name = models.CharField(max_length=100)
    #email = models.EmailField()
    #principal = models.CharField(max_length=100)
    #dn = models.CharField(max_length=100)
    #unixid = models.CharField(max_length=25)

    #class Meta:
        #ordering = ["name"]

    #def __unicode__(self):
        #return self.name

class Group(models.Model):
    name = models.CharField(max_length=20)
    def __unicode__(self):
        return self.name


class Pipeline(models.Model):
    PIPELINE_TYPE_EXTERNAL = 'E'
    PIPELINE_TYPE_OTHER = 'O'
    PIPELINE_TYPE_SEARCH_OTHER = 'SO'
    PIPELINE_TYPE_SEARCH_PRODUCTION = 'SP'
    PIPELINE_TYPE_CHOICES = (
        (PIPELINE_TYPE_EXTERNAL, 'external'),
        (PIPELINE_TYPE_OTHER, 'other'),
        (PIPELINE_TYPE_SEARCH_OTHER, 'non-production search'),
        (PIPELINE_TYPE_SEARCH_PRODUCTION, 'production search'),
    )
    name = models.CharField(max_length=100)
    # Are submissions allowed for this pipeline?
    enabled = models.BooleanField(default=True)
    # Pipeline type
    pipeline_type = models.CharField(max_length=2,
        choices=PIPELINE_TYPE_CHOICES)

    # Add custom managers; must manually define 'objects' as well
    objects = models.Manager()
    production_objects = ProductionPipelineManager()
    external_objects = ExternalPipelineManager()

    class Meta:
        permissions = (
            ('manage_pipeline', 'Can enable or disable pipeline'),
        )

    def __unicode__(self):
        return self.name


class PipelineLog(models.Model):
    PIPELINE_LOG_ACTION_DISABLE = 'D'
    PIPELINE_LOG_ACTION_ENABLE = 'E'
    PIPELINE_LOG_ACTION_CHOICES = (
        (PIPELINE_LOG_ACTION_DISABLE, 'disable'),
        (PIPELINE_LOG_ACTION_ENABLE, 'enable'),
    )
    creator = models.ForeignKey(UserModel)
    pipeline = models.ForeignKey(Pipeline)
    created = models.DateTimeField(auto_now_add=True)
    action = models.CharField(max_length=10,
        choices=PIPELINE_LOG_ACTION_CHOICES)


class Search(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    # XXX Need any additional fields? Like a PI email? Or perhaps even fk?
    def __unicode__(self):
        return self.name

# Label color will be used in CSS, see
# https://www.w3schools.com/colors/colors_names.asp for
# allowed color choices
class Label(models.Model):
    name = models.CharField(max_length=20, unique=True)
    # XXX really, does this belong here? probably not.
    defaultColor = models.CharField(max_length=20, unique=False,
        default="black")
    description = models.TextField(blank=False)
    # protected = True means that the Label should not be "writeable": i.e.,
    # users should not be able to directly apply or remove it.  This is useful
    # for labels that are added and removed as part of a process, like
    # signoffs, for examples.
    protected = models.BooleanField(default=False)

    def __unicode__(self):
        return self.name

    class ProtectedLabelError(Exception):
        # To be raised when an attempt is made to apply or remove a
        # protected label to/from an event or superevent
        pass

    class RelatedSignoffExistsError(Exception):
        # To be raised when an attempt is made to apply a "signoff request"
        # label (like ADVREQ, H1OPS, etc.) when a signoff of that type already
        # exists (example: an advocate signoff exists and ADVOK or ADVNO is
        # applied, but a user tries to apply 'ADVREQ')
        pass


class Event(models.Model):

    objects = InheritanceManager() # Queries can return subclasses, if available.

#    ANALYSIS_TYPE_CHOICES = (
#        ("LM",  "LowMass"),
#        ("HM",  "HighMass"),
#        ("GRB", "GRB"),
#        ("RD",  "Ringdown"),
#        ("OM",  "Omega"),
#        ("Q",   "Q"),
#        ("X",   "X"),
#        ("CWB", "CWB"),
#        ("MBTA", "MBTAOnline"),
#        ("HWINJ", "HardwareInjection"),
#    )
    DEFAULT_EVENT_NEIGHBORHOOD = (-5,5)

    submitter = models.ForeignKey(UserModel)
    created = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group)
    #uid = models.CharField(max_length=20, default="")  # XXX deprecated.  should be removed.
    #analysisType = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)

    # Events aren't required to be part of a superevent. If the superevent is
    # deleted, don't delete the event; just set this FK to null.
    superevent = models.ForeignKey('superevents.Superevent', null=True,
        related_name='events', on_delete=models.SET_NULL)

    # Note: a default value is needed only during the schema migration
    # that creates this column. After that, we can safely remove it.
    # The presence or absence of the default value has no effect on the DB
    # tables, so removing it does not necessitate a migration.
    pipeline = models.ForeignKey(Pipeline) 
    search = models.ForeignKey(Search, null=True)

    # from coinc_event
    instruments = models.CharField(max_length=20, default="")
    nevents = models.PositiveIntegerField(null=True)
    far = models.FloatField(null=True)
    likelihood = models.FloatField(null=True)

    # NOT from coinc_event, but so, so common.
    #   Note that the semantics for this is different depending
    #   on search type, so in some sense, querying on this may
    #   be considered, umm, wrong?  But it is a starting point.
    #gpstime = models.PositiveIntegerField(null=True)
    gpstime = models.DecimalField(max_digits=16, decimal_places=6, null=True)

    labels = models.ManyToManyField(Label, through="Labelling")

    # This field will store a JSON-serialized list of permissions, of the
    # form <group name>_can_<permission codename>
    # This obviously duplicates information that is already in the database
    # in the form of GroupObjectPermission objects. Such duplication is 
    # normally a bad thing, as it can lead to divergence. But we're going
    # to try really hard to avoid that. And it may help speed up the 
    # searches quite considerably.
    perms = models.TextField(null=True)

    # Boolean which determines whether the event was submitted by an offline
    # analysis (True) or an online/low-latency analysis (False). Because this
    # is being implemented during a run (O2), we use a default value of False
    # so as to ensure backwards-compatibility; i.e., all events treated as
    # "online" by default.
    offline = models.BooleanField(default=False)

    class Meta:
        ordering = ["-id"]

    @property
    def graceid(self):
        if self.group.name == "Test":
            return "T%04d" % self.id
        elif str(self.search) == str("MDC"):
            return "M%04d" % self.id
        elif self.pipeline.name == "HardwareInjection":
            return "H%04d" % self.id
        elif self.group.name == "External":
            return "E%04d" % self.id
        return "G%04d" % self.id

    def weburl(self):
        # XXX Not good.  But then, it never was.
        return reverse('file_list', args=[self.graceid])

    @property
    def datadir(self):
        # Create a file-like object which is the SHA-1 hexdigest of the Event's primary key
        hdf = StringIO(sha1(str(self.id)).hexdigest())

        # Build up the nodes of the directory structure
        nodes = [hdf.read(i) for i in settings.GRACEDB_DIR_DIGITS]

        # Read whatever is left over. This is the 'leaf' directory.
        nodes.append(hdf.read())
        return os.path.join(settings.GRACEDB_DATA_DIR, *nodes)

    def is_ns_candidate(self):
        # Used for notifications
        # Current condition: m2 < 3.0 M_sun

        # Ensure that we have the base event class
        event = self
        if hasattr(self, 'event_ptr'):
            event = self.event_ptr

        # Check for single inspirals
        if event.singleinspiral_set.exists():
            si = event.singleinspiral_set.first()
            if (si.mass2 > 0 and si.mass2 < 3):
                return True
        return False

    def is_test(self):
        return self.group.name == 'Test'

    def is_mdc(self):
        return (self.search and self.search.name == 'MDC' and
                self.group.name != 'Test')

    def is_production(self):
        return not (self.is_test() or self.is_mdc())

    def get_event_category(self):
        if self.is_test():
            return 'Test'
        elif self.is_mdc():
            return 'MDC'
        else:
            return 'Production'

    def reportingLatency(self):
        if self.gpstime:
            dt = self.created
            if not dt.tzinfo:
                dt = SERVER_TZ.localize(dt)
            dt = dt.astimezone(pytz.utc)
            posix_time = calendar.timegm(dt.timetuple())
            gps_time = int(posixToGpsTime(posix_time))
            return gps_time - self.gpstime

    def neighbors(self, neighborhood=None):
        if not self.gpstime:
            return Event.objects.none()
        if self.group.name == 'Test':
            nearby = Event.objects.filter(group__name='Test')
        else:
            nearby = Event.objects.exclude(group__name='Test')

        delta1, delta2 = neighborhood or self.DEFAULT_EVENT_NEIGHBORHOOD

        nearby = nearby.filter(gpstime__range=(self.gpstime+delta1, self.gpstime+delta2))
        nearby = nearby.exclude(id=self.id)
        nearby = nearby.distinct()
        nearby = nearby.order_by('gpstime')
        return nearby

    @classmethod
    def getTypeLabel(cls, code):
        for key, label in cls.ANALYSIS_TYPE_CHOICES:
            if (key == code) or (code == label):
                return label
        raise KeyError("Unknown analysis type code: %s" % code)

    @classmethod
    def getByGraceid(cls, id):
        try:
            e = cls.objects.filter(id=int(id[1:])).select_subclasses()[0]
        except IndexError:
            raise cls.DoesNotExist("Event matching query does not exist")
        if (id[0] == "T") and (e.group.name == "Test"):
            return e
        if (id[0] == "H") and (e.pipeline.name == "HardwareInjection"):
            return e
        if (id[0] == "E") and (e.group.name == "External"):
            return e
        if (id[0] == "M") and (e.search and e.search.name == "MDC"):
            return e
        if (id[0] == "G"):
            return e
        raise cls.DoesNotExist("Event matching query does not exist")

    def __unicode__(self):
        return self.graceid

    # Return a list of distinct tags associated with the log messages of this
    # event.
    def getAvailableTags(self):
        tagset_list = [log.tags.all() for log in self.eventlog_set.all()]
        taglist = []
        for tagset in tagset_list:
            for tag in tagset:
                taglist.append(tag)
        # Eliminate duplicates
        taglist = list(set(taglist))
        # Ordering should match the ordering of blessed tags list.
        # XXX Possibly, there are smarter ways of doing this.
        if settings.BLESSED_TAGS:
            availableTags = []
            for blessed_tag in settings.BLESSED_TAGS:
                for tag in taglist:
                    if tag.name == blessed_tag:
                        taglist.remove(tag)
                        availableTags.append(tag)
            # Append any remaining tags at the end of the list
            if len(taglist)>0:
                for tag in taglist:
                    availableTags.append(tag)
        else:
            availableTags = taglist
        return availableTags

    def getLogsForTag(self,tagname):
        loglist = []
        for log in self.eventlog_set.all():
            for tag in log.tags.all():
                if tag.name==tagname:
                    loglist.append(log)
        return loglist

    def get_subclass(self):
        """
        For a base Event object, returns subclass (if any); should be only
        one subclass for each event.

        For a subclass, returns self.
        """
        if not (self.__class__ == Event):
            return self
        subclass_fields = [f.name for f in self.__class__._meta.get_fields()
            if (f.one_to_one and f.auto_created and not f.concrete and
                self.__class__ in f.related_model.__bases__)]
        for f in subclass_fields:
            if hasattr(self, f):
                return getattr(self, f)
        return None

    def get_subclass_or_self(self):
        """
        'Safe' version of get_subclass
        """
        subclass = self.get_subclass()
        if subclass is None:
            return self
        return subclass

    # A method to update the permissions according to the permission objects in
    # the database. 
    def refresh_perms(self):
        # Content type is 'Event', obvs.
        content_type = ContentType.objects.get(app_label='events', model='event')
        # Get all of the GroupObjectPermissions for this object id and content type
        group_object_perms = GroupObjectPermission.objects.filter(object_pk=self.id,
            content_type=content_type)
        perm_strings = []
        # Make a list of permission strings
        for obj in group_object_perms:
            perm_strings.append('%s_can_%s' % (obj.group.name, obj.permission.codename.split('_')[0]))
        # Serialize as json.
        self.perms = json.dumps(perm_strings)
        # Fool! Save yourself!
        self.save()

    def delete(self, purge=True, *args, **kwargs):
        """
        Optionally override the delete method for Event models.
        By default, deleting an Event deletes corresponding subclasses
        (GrbEvent, CoincInspiralEvent, etc.) and EventLogs, EMObservations,
        etc., but does not remove the data directory or the
        GroupObjectPermissions corresponding to the Event or its subclasses.

        Usage:
            event.delete() will do the basic delete, just as before
            event.delete(purge=True) will also remove the data directory
                and GroupObjectPermissions for the Event and its subclasses
        """
        # Store datadir and pk before delete - the pk will be set to None
        # by removal from the database, and thus, the datadir won't be
        # correct anymore, since it depends on the pk
        pk = self.pk
        datadir = self.datadir

        # Call base class delete
        super(Event, self).delete(*args, **kwargs)

        # If the database entry was deleted, then we are good to proceed on
        # purging everything else (if specified)
        if purge:
            # Delete data directory
            if os.path.isdir(datadir):
                shutil.rmtree(datadir)

            # Delete any GroupObjectPermissions for this event and its
            # subclasses (MultiBurstEvent, CoincInspiralEvent, etc.)
            cls = self.__class__
            subclasses = [f.related_model for f in cls._meta.get_fields()
                if (f.one_to_one and f.auto_created and not f.concrete and
                    cls in f.related_model.__bases__)]
            for m in subclasses + [cls]:
                ctype = ContentType.objects.get_for_model(m)
                gops = GroupObjectPermission.objects.filter(object_pk=pk,
                    content_type=ctype)
                gops.delete()


class EventLog(CleanSaveModel, LogBase, AutoIncrementModel):
    """
    Log message object attached to an Event. Uses the AutoIncrementModel
    to handle log enumeration on a per-Event basis.
    """
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('event',)

    # Extra fields
    event = models.ForeignKey(Event, null=False)
    tags = models.ManyToManyField('Tag', related_name='event_logs')

    class Meta(LogBase.Meta):
        unique_together = (('event', 'N'),)

    def fileurl(self):
        if self.filename:
            return reverse('file-download', args=[self.event.graceid,
                self.versioned_filename])
        else:
            return None


class EMGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)

    # XXX what else? Possibly the liasons. These can be populated 
    # automatically from the gw-astronomy COManage-provisioned LDAP.
    # Let's leave this out for now. The submitter will be stored in 
    # the EMBB log record, and that should be enough for audit/blame
    # purposes.
    #liasons = models.ManyToManyField(UserModel)

    def __unicode__(self):
        return self.name


class EMObservationBase(models.Model):
    """Abstract base class for EM follow-up observation records"""
    class Meta:
        abstract = True
        ordering = ['-created', '-N']

    N = models.IntegerField(null=False, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    submitter  = models.ForeignKey(UserModel, null=False,
        related_name='%(app_label)s_%(class)s_set')

    # The MOU group responsible 
    group = models.ForeignKey(EMGroup, null=False,
        related_name='%(app_label)s_%(class)s_set')

    # The following fields should be calculated from the footprint info
    # provided by the user. These fields are just for convenience and
    # fast searching

    # The center of the bounding box of the rectangular footprints ra,dec
    # in J2000 in decimal degrees
    ra         = models.FloatField(null=True, blank=True)
    dec        = models.FloatField(null=True, blank=True)

    # The width and height (RA range and Dec range) in decimal degrees 
    raWidth    = models.FloatField(null=True, blank=True)
    decWidth   = models.FloatField(null=True, blank=True)

    comment = models.TextField(blank=True)

    def calculateCoveringRegion(self, footprints=None):
        # Implement most of the logic in the abstract class' method
        # without needing to specify the footprints field
        if not footprints:
            return

        ramin = 360.0
        ramax = 0.0
        decmin = 90.0
        decmax = -90.0

        for f in footprints:
            
            # evaluate bounding box
            w = float(f.raWidth)/2
            if f.ra-w < ramin: ramin = f.ra-w
            if f.ra+w > ramax: ramax = f.ra+w

            w = float(f.decWidth)/2
            if f.dec-w < decmin: decmin = f.dec-w
            if f.dec+w > decmax: decmax = f.dec+w

        # Make sure the min/max ra and dec are within bounds:
        ramin  = max(0.0,   ramin)
        ramax  = min(360.0, ramax)
        decmin = max(-90.0, decmin)
        decmax = min(90.0,  decmax)

        # Calculate sky rectangle bounds
        self.ra       = (ramin + ramax)/2
        self.dec      = (decmin + decmax)/2
        self.raWidth  = ramax-ramin
        self.decWidth = decmax-decmin


class EMObservation(EMObservationBase, AutoIncrementModel):
    """EMObservation class for events"""
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('event',)
    event = models.ForeignKey(Event, null=False, on_delete=models.CASCADE)

    class Meta(EMObservationBase.Meta):
        unique_together = (('event', 'N'),)

    def __unicode__(self):
        return "{event_id} | {group} | {N}".format(
            event_id=self.event.graceid, group=self.group.name, N=self.N)

    def calculateCoveringRegion(self):
        footprints = self.emfootprint_set.all()
        super(EMObservation, self).calculateCoveringRegion(footprints)


class EMFootprintBase(models.Model):
    """
    Abstract base class for EM footprints:
    Each EMObservation can have many footprints underneath.

    None of the fields are optional here.
    """
    N = models.IntegerField(null=False, editable=False)

    # The center of the rectangular footprint, right ascension and declination
    # in J2000 in decimal degrees
    ra         = models.FloatField(null=False, blank=False)
    dec        = models.FloatField(null=False, blank=False)

    # The width and height (RA range and Dec range) in decimal degrees 
    raWidth    = models.FloatField(null=False, blank=False)
    decWidth   = models.FloatField(null=False, blank=False)

    # The start time of the observation for this footprint
    start_time = models.DateTimeField(null=False, blank=False)

    # The exposure time in seconds for this footprint
    exposure_time = models.PositiveIntegerField(null=False, blank=False)

    class Meta:
        abstract = True
        ordering = ['-N']


class EMFootprint(EMFootprintBase, AutoIncrementModel):
    """EMFootprint class for event EMObservations"""
    # For AutoIncrementModel save
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('observation',)
    observation = models.ForeignKey(EMObservation, null=False,
        on_delete=models.CASCADE)

    class Meta(EMFootprintBase.Meta):
        unique_together = (('observation', 'N'),)


class Labelling(m2mThroughBase):
    """
    Model which provides the "through" relationship between Events and Labels.
    """
    event = models.ForeignKey(Event)
    label = models.ForeignKey(Label)

    def __unicode__(self):
        return "{graceid} | {label}".format(graceid=self.event.graceid,
            label=self.label.name)


## Analysis Specific Attributes.
class GrbEvent(Event):
    ivorn = models.CharField(max_length=200, null=True)
    author_ivorn = models.CharField(max_length=200, null=True)
    author_shortname = models.CharField(max_length=200, null=True)
    observatory_location_id = models.CharField(max_length=200, null=True)
    coord_system = models.CharField(max_length=200, null=True)
    ra = models.FloatField(null=True)
    dec = models.FloatField(null=True)
    error_radius = models.FloatField(null=True)
    how_description = models.CharField(max_length=200, null=True)
    how_reference_url = models.URLField(null=True)
    trigger_duration = models.FloatField(null=True)
    t90 = models.FloatField(null=True)
    designation = models.CharField(max_length=20, null=True)
    redshift = models.FloatField(null=True)
    trigger_id = models.CharField(max_length=25, null=True)

class CoincInspiralEvent(Event):
    ifos             = models.CharField(max_length=20, default="")
    end_time         = models.PositiveIntegerField(null=True)
    end_time_ns      = models.PositiveIntegerField(null=True)
    mass             = models.FloatField(null=True)
    mchirp           = models.FloatField(null=True)
    minimum_duration = models.FloatField(null=True)
    snr              = models.FloatField(null=True)
    false_alarm_rate = models.FloatField(null=True)
    combined_far     = models.FloatField(null=True)


class MultiBurstEvent(Event):
    ifos             = models.CharField(max_length=20, default="")
    start_time       = models.PositiveIntegerField(null=True)
    start_time_ns    = models.PositiveIntegerField(null=True)
    duration         = models.FloatField(null=True)
    peak_time        = models.PositiveIntegerField(null=True)
    peak_time_ns     = models.PositiveIntegerField(null=True)
    central_freq     = models.FloatField(null=True)
    bandwidth        = models.FloatField(null=True)
    amplitude        = models.FloatField(null=True)
    snr              = models.FloatField(null=True)
    confidence       = models.FloatField(null=True)
    false_alarm_rate = models.FloatField(null=True)
    ligo_axis_ra     = models.FloatField(null=True)
    ligo_axis_dec    = models.FloatField(null=True)
    ligo_angle       = models.FloatField(null=True)
    ligo_angle_sig   = models.FloatField(null=True)
    single_ifo_times = models.CharField(max_length=255, default="")

class LalInferenceBurstEvent(Event):
    bci                 = models.FloatField(null=True)
    quality_mean        = models.FloatField(null=True)
    quality_median      = models.FloatField(null=True)
    bsn                 = models.FloatField(null=True)
    omicron_snr_network = models.FloatField(null=True)
    omicron_snr_H1      = models.FloatField(null=True)
    omicron_snr_L1      = models.FloatField(null=True)
    omicron_snr_V1      = models.FloatField(null=True)
    hrss_mean           = models.FloatField(null=True)
    hrss_median         = models.FloatField(null=True)
    frequency_mean      = models.FloatField(null=True)
    frequency_median    = models.FloatField(null=True)

class SingleInspiral(models.Model):
    event             = models.ForeignKey(Event, null=False)
    ifo               = models.CharField(max_length=20, null=True)
    search            = models.CharField(max_length=20, null=True)
    channel           = models.CharField(max_length=100, blank=True)
    end_time          = models.IntegerField(null=True)
    end_time_ns       = models.IntegerField(null=True)
    end_time_gmst     = models.FloatField(null=True)
    impulse_time      = models.IntegerField(null=True)
    impulse_time_ns   = models.IntegerField(null=True)
    template_duration = models.FloatField(null=True)
    event_duration    = models.FloatField(null=True)
    amplitude         = models.FloatField(null=True)
    eff_distance      = models.FloatField(null=True)
    coa_phase         = models.FloatField(null=True)
    mass1             = models.FloatField(null=True)
    mass2             = models.FloatField(null=True)
    mchirp            = models.FloatField(null=True)
    mtotal            = models.FloatField(null=True)
    eta               = models.FloatField(null=True)
    kappa             = models.FloatField(null=True)
    chi               = models.FloatField(null=True)
    tau0              = models.FloatField(null=True)
    tau2              = models.FloatField(null=True)
    tau3              = models.FloatField(null=True)
    tau4              = models.FloatField(null=True)
    tau5              = models.FloatField(null=True)
    ttotal            = models.FloatField(null=True)
    psi0              = models.FloatField(null=True)
    psi3              = models.FloatField(null=True)
    alpha             = models.FloatField(null=True)
    alpha1            = models.FloatField(null=True)
    alpha2            = models.FloatField(null=True)
    alpha3            = models.FloatField(null=True)
    alpha4            = models.FloatField(null=True)
    alpha5            = models.FloatField(null=True)
    alpha6            = models.FloatField(null=True)
    beta              = models.FloatField(null=True)
    f_final           = models.FloatField(null=True)
    snr               = models.FloatField(null=True)
    chisq             = models.FloatField(null=True)
    chisq_dof         = models.IntegerField(null=True)
    bank_chisq        = models.FloatField(null=True)
    bank_chisq_dof    = models.IntegerField(null=True)
    cont_chisq        = models.FloatField(null=True)
    cont_chisq_dof    = models.IntegerField(null=True)
    sigmasq           = models.FloatField(null=True)
    rsqveto_duration  = models.FloatField(null=True)
    Gamma0            = models.FloatField(null=True)
    Gamma1            = models.FloatField(null=True)
    Gamma2            = models.FloatField(null=True)
    Gamma3            = models.FloatField(null=True)
    Gamma4            = models.FloatField(null=True)
    Gamma5            = models.FloatField(null=True)
    Gamma6            = models.FloatField(null=True)
    Gamma7            = models.FloatField(null=True)
    Gamma8            = models.FloatField(null=True)
    Gamma9            = models.FloatField(null=True)
    spin1x            = models.FloatField(null=True)
    spin1y            = models.FloatField(null=True)
    spin1z            = models.FloatField(null=True)
    spin2x            = models.FloatField(null=True)
    spin2y            = models.FloatField(null=True)
    spin2z            = models.FloatField(null=True)

    def end_time_full(self):
        return LIGOTimeGPS(self.end_time, self.end_time_ns)

    def impulse_time_full(self):
        return LIGOTimeGPS(self.impulse_time, self.impulse_time_ns)

    @classmethod
    def create_events_from_ligolw_table(cls, table, event):
        """For an Event, given a table (loaded by ligolw.utils.load_filename or similar) create SingleEvent tables for the event"""

        created_events = []

        #log.debug("Single/create from table/fields: " + str(field_names))

        for row in table:
            e = cls(event=event)
            #log.debug("Single/creating event")
            for f in [cls._meta.get_field(f) for f in cls.field_names()]:
                value = getattr(row, f.attname, f.default)

                # Awful kludge for handling nan for eff_distance
                try:
                    if (f.attname == 'eff_distance' and
                        isinstance(value, numbers.Number) and isnan(value)):
                        value = None
                except Exception as e:
                    pass

                # Only set value of class instance member if
                # value is not None or if field is nullable.
                # Otherwise we could overwrite non-nullable fields
                # which have default values with None.
                if value is not None or f.null:
                    #log.debug("Setting column '%s' with value '%s'" % (f.attname, value))
                    setattr(e, f.attname, value)
            e.save()
            created_events.append(e)

        return created_events

    @classmethod
    def update_event(cls, event, datafile=None):
        """Given an Event (and optional location of coinc.xml) update SingleInspiral data"""
        # XXX Need a better way to find original data.
        if datafile is None:
            datafile = os.path.join(event.datadir, 'coinc.xml')

        try:
            xmldoc = glue.ligolw.utils.load_filename(datafile, contenthandler=LIGOLWContentHandler)
        except IOError:
            return None

        # Extract Single Inspiral Information
        s_inspiral_tables = glue.ligolw.lsctables.SnglInspiralTable.get_table(xmldoc)

        # Concatentate the tables' rows into a single table
        table = sum(s_inspiral_tables, [])

        event.singleinspiral_set.all().delete()

        return cls.create_events_from_ligolw_table(table, event)

    @classmethod
    def field_names(cls):
        try:
            return cls._field_names
        except AttributeError: pass
        model_field_names = set([ x.name for x in cls._meta.get_fields(include_parents=False) ])
        ligolw_field_names = set(
                glue.ligolw.lsctables.SnglInspiralTable.validcolumns.keys())
        cls._field_names = model_field_names.intersection(ligolw_field_names)
        return cls._field_names

# Event subclass for injections
class SimInspiralEvent(Event):
    mass1                = models.FloatField(null=True)
    mass2                = models.FloatField(null=True)
    eta                  = models.FloatField(null=True)
    amp_order            = models.IntegerField(null=True)
    coa_phase            = models.FloatField(null=True)
    mchirp               = models.FloatField(null=True)
    spin1y               = models.FloatField(null=True)
    spin1x               = models.FloatField(null=True)
    spin1z               = models.FloatField(null=True)
    spin2x               = models.FloatField(null=True)
    spin2y               = models.FloatField(null=True)
    spin2z               = models.FloatField(null=True)
    geocent_end_time     = models.IntegerField(null=True)
    geocent_end_time_ns  = models.IntegerField(null=True)
    end_time_gmst        = models.FloatField(null=True)
    f_lower              = models.FloatField(null=True)
    f_final              = models.FloatField(null=True)
    distance             = models.FloatField(null=True)
    latitude             = models.FloatField(null=True)
    longitude            = models.FloatField(null=True)
    polarization         = models.FloatField(null=True)
    inclination          = models.FloatField(null=True)
    theta0               = models.FloatField(null=True)
    phi0                 = models.FloatField(null=True)
    waveform             = models.CharField(max_length=50, blank=True, default="")
    numrel_mode_min      = models.IntegerField(null=True)
    numrel_mode_max      = models.IntegerField(null=True)
    numrel_data          = models.CharField(max_length=50, blank=True, default="")
    source               = models.CharField(max_length=50, blank=True, default="")
    taper                = models.CharField(max_length=50, blank=True, default="")
    bandpass             = models.IntegerField(null=True)
    alpha                = models.FloatField(null=True)
    beta                 = models.FloatField(null=True)
    psi0                 = models.FloatField(null=True)
    psi3                 = models.FloatField(null=True)
    alpha1               = models.FloatField(null=True)
    alpha2               = models.FloatField(null=True)
    alpha3               = models.FloatField(null=True)
    alpha4               = models.FloatField(null=True)
    alpha5               = models.FloatField(null=True)
    alpha6               = models.FloatField(null=True)
    g_end_time           = models.IntegerField(null=True)
    g_end_time_ns        = models.IntegerField(null=True)
    h_end_time           = models.IntegerField(null=True)
    h_end_time_ns        = models.IntegerField(null=True)
    l_end_time           = models.IntegerField(null=True)
    l_end_time_ns        = models.IntegerField(null=True)
    t_end_time           = models.IntegerField(null=True)
    t_end_time_ns        = models.IntegerField(null=True)
    v_end_time           = models.IntegerField(null=True)
    v_end_time_ns        = models.IntegerField(null=True)
    eff_dist_g           = models.FloatField(null=True)
    eff_dist_h           = models.FloatField(null=True)
    eff_dist_l           = models.FloatField(null=True)
    eff_dist_t           = models.FloatField(null=True)
    eff_dist_v           = models.FloatField(null=True)
    # Additional desired attributes that are not in the SimInspiral table
    source_channel       = models.CharField(max_length=50, blank=True, default="", null=True)
    destination_channel  = models.CharField(max_length=50, blank=True, default="", null=True)

    @classmethod
    def field_names(cls):
        try:
            return cls._field_names
        except AttributeError: pass
        # We only care about the model field names in this particular case.
        cls._field_names = [ x.name for x in cls._meta.get_fields(include_parents=False) ]
        return cls._field_names

# Tags (user-defined log message attributes)
class Tag(CleanSaveModel):
    """
    Model for tags attached to EventLogs.

    We don't use an explicit through model to track relationship creators and
    time of relationship creation since we generally create a log message
    whenever another log is tagged.  Not sure that it's good to make the
    assumption that this will always be done.  But is it really important to
    track those things?  Doesn't seem like it.
    """
    name = models.CharField(max_length=100, null=False, blank=False,
        unique=True,
        validators=[
            models.fields.validators.RegexValidator(
                regex=r'^[0-9a-zA-Z_\-]*$',
                message="Tag names can only include [0-9a-zA-z_-]",
                code="invalid_tag_name",
            )
        ])
    displayName = models.CharField(max_length=200, null=True, blank=True)

    def __unicode__(self):
        return self.displayName if self.displayName else self.name


class VOEventBase(CleanSaveModel):
    """Abstract base model for VOEvents"""

    class Meta:
        abstract = True
        ordering = ['-created', '-N']

    # VOEvent type choices
    VOEVENT_TYPE_PRELIMINARY = 'PR'
    VOEVENT_TYPE_INITIAL = 'IN'
    VOEVENT_TYPE_UPDATE = 'UP'
    VOEVENT_TYPE_RETRACTION = 'RE'
    VOEVENT_TYPE_CHOICES = (
        (VOEVENT_TYPE_PRELIMINARY, 'preliminary'),
        (VOEVENT_TYPE_INITIAL, 'initial'),
        (VOEVENT_TYPE_UPDATE, 'update'),
        (VOEVENT_TYPE_RETRACTION, 'retraction'),
    )

    # Fields
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(UserModel, null=False,
        related_name='%(app_label)s_%(class)s_set')
    ivorn = models.CharField(max_length=200, default="", blank=True,
        editable=False)
    filename = models.CharField(max_length=100, default="", blank=True,
        editable=False)
    file_version = models.IntegerField(null=True, default=None, blank=True)
    N = models.IntegerField(null=False, editable=False)
    voevent_type = models.CharField(max_length=2, choices=VOEVENT_TYPE_CHOICES)
    skymap_type = models.CharField(max_length=100, null=True, default=None,
        blank=True)
    skymap_filename = models.CharField(max_length=100, null=True, default=None,
        blank=True)
    internal = models.BooleanField(null=False, default=True, blank=True)
    open_alert = models.BooleanField(null=False, default=False, blank=True)
    hardware_inj = models.BooleanField(null=False, default=False, blank=True)
    coinc_comment = models.BooleanField(null=False, default=False, blank=True)
    prob_has_ns = models.FloatField(null=True, default=None, blank=True,
        validators=[models.fields.validators.MinValueValidator(0.0),
        models.fields.validators.MaxValueValidator(1.0)])
    prob_has_remnant = models.FloatField(null=True, default=None, blank=True,
        validators=[models.fields.validators.MinValueValidator(0.0),
        models.fields.validators.MaxValueValidator(1.0)])
    prob_bns = models.FloatField(null=True, default=None, blank=True,
        validators=[models.fields.validators.MinValueValidator(0.0),
        models.fields.validators.MaxValueValidator(1.0)])
    prob_nsbh = models.FloatField(null=True, default=None, blank=True,
        validators=[models.fields.validators.MinValueValidator(0.0),
        models.fields.validators.MaxValueValidator(1.0)])
    prob_bbh = models.FloatField(null=True, default=None, blank=True,
        validators=[models.fields.validators.MinValueValidator(0.0),
        models.fields.validators.MaxValueValidator(1.0)])
    prob_terrestrial = models.FloatField(null=True, default=None, blank=True,
        validators=[models.fields.validators.MinValueValidator(0.0),
        models.fields.validators.MaxValueValidator(1.0)])
    prob_mass_gap = models.FloatField(null=True, default=None, blank=True,
        validators=[models.fields.validators.MinValueValidator(0.0),
        models.fields.validators.MaxValueValidator(1.0)])

    def fileurl(self):
        # Override this method on derived classes
        return NotImplemented


class VOEvent(VOEventBase, AutoIncrementModel):
    """VOEvent class for events"""
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('event',)
    event = models.ForeignKey(Event, null=False, on_delete=models.CASCADE)

    class Meta(VOEventBase.Meta):
        unique_together = (('event', 'N'),)

    def fileurl(self):
        if self.filename:
            actual_filename = self.filename
            if self.file_version >= 0:
                actual_filename += ',%d' % self.file_version
            return reverse('file-download', args=[self.event.graceid,
                actual_filename])
        else:
            return None


class SignoffBase(models.Model):
    """Abstract base model for operator and advocate signoffs"""

    # Instrument choices
    INSTRUMENT_H1 = 'H1'
    INSTRUMENT_L1 = 'L1'
    INSTRUMENT_V1 = 'V1'
    INSTRUMENT_CHOICES = (
        (INSTRUMENT_H1, 'LHO'),
        (INSTRUMENT_L1, 'LLO'),
        (INSTRUMENT_V1, 'Virgo'),
    )

    # Operator status choices
    OPERATOR_STATUS_OK = 'OK'
    OPERATOR_STATUS_NOTOK = 'NO'
    OPERATOR_STATUS_CHOICES = (
        (OPERATOR_STATUS_OK, 'OKAY'),
        (OPERATOR_STATUS_NOTOK, 'NOT OKAY'),
    )

    # Signoff type choices
    SIGNOFF_TYPE_OPERATOR = 'OP'
    SIGNOFF_TYPE_ADVOCATE = 'ADV'
    SIGNOFF_TYPE_CHOICES = (
        (SIGNOFF_TYPE_OPERATOR, 'operator'),
        (SIGNOFF_TYPE_ADVOCATE, 'advocate'),
    )

    # Field definitions
    submitter = models.ForeignKey(UserModel, related_name=
        '%(app_label)s_%(class)s_set')
    comment = models.TextField(blank=True)
    instrument = models.CharField(max_length=2, blank=True,
        choices=INSTRUMENT_CHOICES)
    status = models.CharField(max_length=2, blank=False,
        choices=OPERATOR_STATUS_CHOICES)
    signoff_type = models.CharField(max_length=3, blank=False,
        choices=SIGNOFF_TYPE_CHOICES)

    # Timezones for instruments (this should really be handled separately
    # by an instrument class)
    instrument_time_zones = {
        INSTRUMENT_H1: 'America/Los_Angeles',
        INSTRUMENT_L1: 'America/Chicago',
        INSTRUMENT_V1: 'Europe/Rome',
    }

    class Meta:
        abstract = True

    def clean(self, *args, **kwargs):
        """Custom clean method for signoffs"""

        # Make sure instrument is non-blank if this is an operator signoff
        if (self.signoff_type == self.SIGNOFF_TYPE_OPERATOR and
            not self.instrument):

            raise ValidationError({'instrument':
                _('Instrument must be specified for operator signoff')})

        super(SignoffBase, self).clean(*args, **kwargs)

    def get_req_label_name(self):
        if self.signoff_type == 'OP':
            return self.instrument + 'OPS'
        elif self.signoff_type == 'ADV':
            return 'ADVREQ'

    def get_status_label_name(self):
        if self.signoff_type == 'OP':
            return self.instrument + self.status
        elif self.signoff_type == 'ADV':
            return 'ADV' + self.status

    @property
    def opposite_status(self):
        if self.status == 'OK':
            return 'NO'
        elif self.status == 'NO':
            return 'OK'

    def get_opposite_status_label_name(self):
        if self.signoff_type == 'OP':
            return self.instrument + self.opposite_status
        elif self.signoff_type == 'ADV':
            return 'ADV' + self.opposite_status



class Signoff(SignoffBase):
    """Class for Event signoffs"""

    event = models.ForeignKey(Event)

    class Meta:
        unique_together = ('event', 'instrument')

    def __unicode__(self):
        return "%s | %s | %s" % (self.event.graceid, self.instrument,
            self.status)

EMSPECTRUM = (
('em.gamma',            'Gamma rays part of the spectrum'),
('em.gamma.soft',       'Soft gamma ray (120 - 500 keV)'),
('em.gamma.hard',       'Hard gamma ray (>500 keV)'),
('em.X-ray',            'X-ray part of the spectrum'),
('em.X-ray.soft',       'Soft X-ray (0.12 - 2 keV)'),
('em.X-ray.medium',     'Medium X-ray (2 - 12 keV)'),
('em.X-ray.hard',       'Hard X-ray (12 - 120 keV)'),
('em.UV',               'Ultraviolet part of the spectrum'),
('em.UV.10-50nm',       'Ultraviolet between 10 and 50 nm'),
('em.UV.50-100nm',      'Ultraviolet between 50 and 100 nm'),
('em.UV.100-200nm',     'Ultraviolet between 100 and 200 nm'),
('em.UV.200-300nm',     'Ultraviolet between 200 and 300 nm'),
('em.UV.FUV',           'Far-Infrared, 30-100 microns'),
('em.opt',              'Optical part of the spectrum'),
('em.opt.U',            'Optical band between 300 and 400 nm'),
('em.opt.B',            'Optical band between 400 and 500 nm'),
('em.opt.V',            'Optical band between 500 and 600 nm'),
('em.opt.R',            'Optical band between 600 and 750 nm'),
('em.opt.I',            'Optical band between 750 and 1000 nm'),
('em.IR',               'Infrared part of the spectrum'),
('em.IR.NIR',           'Near-Infrared, 1-5 microns'),
('em.IR.J',             'Infrared between 1.0 and 1.5 micron'),
('em.IR.H',             'Infrared between 1.5 and 2 micron'),
('em.IR.K',             'Infrared between 2 and 3 micron'),
('em.IR.MIR',           'Medium-Infrared, 5-30 microns'),
('em.IR.3-4um',         'Infrared between 3 and 4 micron'),
('em.IR.4-8um',         'Infrared between 4 and 8 micron'),
('em.IR.8-15um',        'Infrared between 8 and 15 micron'),
('em.IR.15-30um',       'Infrared between 15 and 30 micron'),
('em.IR.30-60um',       'Infrared between 30 and 60 micron'),
('em.IR.60-100um',      'Infrared between 60 and 100 micron'),
('em.IR.FIR',           'Far-Infrared, 30-100 microns'),
('em.mm',               'Millimetric part of the spectrum'),
('em.mm.1500-3000GHz',  'Millimetric between 1500 and 3000 GHz'),
('em.mm.750-1500GHz',   'Millimetric between 750 and 1500 GHz'),
('em.mm.400-750GHz',    'Millimetric between 400 and 750 GHz'),
('em.mm.200-400GHz',    'Millimetric between 200 and 400 GHz'),
('em.mm.100-200GHz',    'Millimetric between 100 and 200 GHz'),
('em.mm.50-100GHz',     'Millimetric between 50 and 100 GHz'),
('em.mm.30-50GHz',      'Millimetric between 30 and 50 GHz'),
('em.radio',            'Radio part of the spectrum'),
('em.radio.12-30GHz',   'Radio between 12 and 30 GHz'),
('em.radio.6-12GHz',    'Radio between 6 and 12 GHz'),
('em.radio.3-6GHz',     'Radio between 3 and 6 GHz'),
('em.radio.1500-3000MHz','Radio between 1500 and 3000 MHz'),
('em.radio.750-1500MHz','Radio between 750 and 1500 MHz'),
('em.radio.400-750MHz', 'Radio between 400 and 750 MHz'),
('em.radio.200-400MHz', 'Radio between 200 and 400 MHz'),
('em.radio.100-200MHz', 'Radio between 100 and 200 MHz'),
('em.radio.20-100MHz',  'Radio between 20 and 100 MHz'),
)

# TP (2 Apr 2018): pretty sure this class is deprecated - most recent
# production use is T137114 = April 2015.
class EMBBEventLog(AutoIncrementModel):
    """EMBB EventLog:  A multi-purpose annotation for EM followup.

    A rectangle on the sky, equatorially aligned,
    that has or will be imaged that is related to an event"""

    class Meta:
        ordering = ['-created', '-N']
        unique_together = ("event","N")

    def __unicode__(self):
        return "%s-%s-%d" % (self.event.graceid, self.group.name, self.N)

    # A counter for Eels associated with a given event. This is 
    # important for addressibility.
    N = models.IntegerField(null=False)

    # The time at which this Eel was created. Important for event auditing.
    created = models.DateTimeField(auto_now_add=True)

    # The gracedb event that this Eel relates to
    event = models.ForeignKey(Event)

    # The responsible author of this communication
    submitter  = models.ForeignKey(UserModel)  # from a table of people

    # The MOU group responsible 
    group = models.ForeignKey(EMGroup)       # from a table of facilities

    # The instrument used or intended for the imaging implied by this footprint
    instrument = models.CharField(max_length=200, blank=True)

    # Facility-local identifier for this footprint
    footprintID= models.TextField(blank=True)

    # Now the global ID is a concatenation: facilityName#footprintID

    # the EM waveband used for the imaging as below
    waveband   = models.CharField(max_length=25, choices=EMSPECTRUM)

    # The center of the bounding box of the rectangular footprints, right ascension and declination
    # in J2000 in decimal degrees
    ra         = models.FloatField(null=True)
    dec        = models.FloatField(null=True)

    # The width and height (RA range and Dec range) in decimal degrees of each image
    raWidth    = models.FloatField(null=True)
    decWidth   = models.FloatField(null=True)

    # The GPS time of the middle of the bounding box of the imaging time
    gpstime    = models.PositiveIntegerField(null=True)

    # The duration of each image in seconds
    duration   = models.PositiveIntegerField(null=True)

    # The lists of RA and Dec of the centers of the images
    raList         = models.TextField(blank=True)
    decList        = models.TextField(blank=True)

    # The width and height of each individual image
    raWidthList    = models.TextField(blank=True)
    decWidthList   = models.TextField(blank=True)

    # The list of GPS times of the images
    gpstimeList        = models.TextField(blank=True)

    # The duration of each individual image
    durationList   = models.TextField(blank=True)

    # Event Log status
    EEL_STATUS_CHOICES = (('FO','FOOTPRINT'), ('SO','SOURCE'), ('CO','COMMENT'), ('CI','CIRCULAR'))
    eel_status     = models.CharField(max_length=2, choices=EEL_STATUS_CHOICES)

    # Observation status. If OBSERVATION, then there is a good chance of good image
    OBS_STATUS_CHOICES = (('NA', 'NOT APPLICABLE'), ('OB','OBSERVATION'), ('TE','TEST'), ('PR','PREDICTION'))
    obs_status     = models.CharField(max_length=2, choices=OBS_STATUS_CHOICES)

    # This field is natural language for human
    comment = models.TextField(blank=True)

    # This field is formal struct by a syntax TBD
    # for example  {"phot.mag.limit": 22.3}
    extra_info_dict = models.TextField(blank=True)

    # For AutoIncrementModel save
    AUTO_FIELD = 'N'
    AUTO_CONSTRAINTS = ('event',)

    # Validates the input and builds  bounding box in RA/Dec/GPS
    def validateMakeRects(self):
        # get all the list based position and times and their widths
        raRealList = []
        rawRealList = []
        # add a [ and ] to convert the input csv list to a json parsable text

        if self.raList:        raRealList = json.loads('['+self.raList+']')
        if self.raWidthList:   rawRealList = json.loads('['+self.raWidthList+']')

        if self.decList:       decRealList = json.loads('['+self.decList+']')
        if self.decWidthList:  decwRealList = json.loads('['+self.decWidthList+']')

        if self.gpstimeList:   gpstimeRealList = json.loads('['+self.gpstimeList+']')
        if self.durationList:  durationRealList = json.loads('['+self.durationList+']')

        # is there anything in the ra list? 
        nList = len(raRealList)
        if nList > 0: 
            if decRealList and len(decRealList) != nList:
                raise ValueError('RA and Dec lists are different lengths.')
            if gpstimeRealList and len(gpstimeRealList) != nList:
                raise ValueError('RA and GPS lists are different lengths.')

        # is there anything in the raWidth list? 
        mList = len(rawRealList)
        if mList > 0:
            if decwRealList and len(decwRealList) != mList:
                raise ValueError('RAwidth and Decwidth lists are different lengths.')
            if durationRealList and len(durationRealList) != mList:
                raise ValueError('RAwidth and Duration lists are different lengths.')

            # There can be 1 width for the whole list, or one for each ra/dec/gps 
            if mList != 1 and mList != nList:
                raise ValueError('Width and duration lists must be length 1 or same length as coordinate lists')
        else:
            mList = 0

        ramin = 360.0
        ramax = 0.0
        decmin = 90.0
        decmax = -90.0
        gpsmin = 100000000000
        gpsmax = 0
        for i in range(nList):
            try:
                ra = float(raRealList[i])
            except:
                raise ValueError('Cannot read RA list element %d of %s'%(i, self.raList))
            try:
                dec = float(decRealList[i])
            except:
                raise ValueError('Cannot read Dec list element %d of %s'%(i, self.decList))
            try:
                gps = int(gpstimeRealList[i])
            except:
                raise ValueError('Cannot read GPStime list element %d of %s'%(i, self.gpstimeList))

            # the widths list can have 1 member to cover all, or one for each
            if mList==1: j=0
            else       : j=i

            try:
                w = float(rawRealList[j])/2
            except:
                raise ValueError('Cannot read raWidth list element %d of %s'%(i, self.raWidthList))

            # evaluate bounding box
            if ra-w < ramin: ramin = ra-w
            if ra+w > ramax: ramax = ra+w

            try:
                w = float(decwRealList[j])/2
            except:
                raise ValueError('Cannot read raWidth list element %d of %s'%(i, self.decWidthList))

            # evaluate bounding box
            if dec-w < decmin: decmin = dec-w
            if dec+w > decmax: decmax = dec+w

            try:
                w = int(durationRealList[j])/2
            except:
                raise ValueError('Cannot read duration list element %d of %s'%(i, self.durationList))

            # evaluate bounding box
            if gps-w < gpsmin: gpsmin = gps-w
            if gps+w > gpsmax: gpsmax = gps+w

        # Make sure the min/max ra and dec are within bounds:
        ramin  = max(0.0,   ramin)
        ramax  = min(360.0, ramax)
        decmin = max(-90.0, decmin)
        decmax = min(90.0,  decmax)

        if nList>0:
            self.ra       = (ramin + ramax)/2
            self.dec      = (decmin + decmax)/2
            self.gpstime  = (gpsmin+gpsmax)/2
        if mList>0:
            self.raWidth  = ramax-ramin
            self.decWidth = decmax-decmin
            self.duration = gpsmax-gpsmin
        return True
