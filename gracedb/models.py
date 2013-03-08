from django.db import models
from django.core.urlresolvers import reverse

from model_utils.managers import InheritanceManager

import datetime
import thread
import string
import os


# XXX ER2.utils.  utils is in project directory.  ugh.
from utils import posixToGpsTime

from django.conf import settings
import pytz, time

SERVER_TZ = pytz.timezone(settings.TIME_ZONE)

# Let's say we start here on schema versions
#
# 1.0 -> 1.1   changed EventLog.comment from CharField(length=200) -> TextField
#
schema_version = "1.1"

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    principal = models.CharField(max_length=100)
    dn = models.CharField(max_length=100)
    unixid = models.CharField(max_length=25)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=20)
    managers = models.ManyToManyField(User)
    def __unicode__(self):
        return self.name

class Label(models.Model):
    name = models.CharField(max_length=20, unique=True)
    # XXX really, does this belong here? probably not.
    defaultColor = models.CharField(max_length=20, unique=False, default="black")
    def __unicode__(self):
        return self.name

class Event(models.Model):

    objects = InheritanceManager() # Queries can return subclasses, if available.

    ANALYSIS_TYPE_CHOICES = (
        ("LM",  "LowMass"),
        ("HM",  "HighMass"),
        ("GRB", "GRB"),
        ("RD",  "Ringdown"),
        ("OM",  "Omega"),
        ("Q",   "Q"),
        ("X",   "X"),
        ("CWB", "CWB"),
        ("MBTA", "MBTAOnline"),
        ("HWINJ", "HardwareInjection"),
    )
    DEFAULT_EVENT_NEIGHBORHOOD = (5,5)

    submitter = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group)
    uid = models.CharField(max_length=20, default="")  # XXX deprecated.  should be removed.
    analysisType = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)

    # from coinc_event
    instruments = models.CharField(max_length=20, default="")
    nevents = models.PositiveIntegerField(null=True)
    far = models.FloatField(null=True)
    likelihood = models.FloatField(null=True)

    # NOT from coinc_event, but so, so common.
    #   Note that the semantics for this is different depending
    #   on search type, so in some sense, querying on this may
    #   be considered, umm, wrong?  But it is a starting point.
    gpstime = models.PositiveIntegerField(null=True)

    labels = models.ManyToManyField(Label, through="Labelling")

    class Meta:
        ordering = ["-id"]

    def graceid(self):
        if self.group.name == "Test":
            return "T%04d" % self.id
        elif self.analysisType == "HWINJ":
            return "H%04d" % self.id
        elif self.analysisType == "GRB":
            return "E%04d" % self.id
        return "G%04d" % self.id

    def weburl(self):
        # XXX Not good.  But then, it never was.
        return "https://gracedb.ligo.org/gracedb-files/%s" % self.graceid()
        return "https://ldas-jobs.phys.uwm.edu/gracedb/data/%s" % self.graceid()

    def clusterurl(self):
        #return "pcdev1.phys.uwm.edu:/archive/gracedb/data/%s" % self.graceid()
        return "file://pcdev1.phys.uwm.edu/archive/gracedb/data/%s" % self.graceid()

    def datadir(self, general=False):
        # Move to this.  Not the (more) ad hoc crap that's floating around.
        if general:
            subdir = "general"
        else:
            subdir = "private"
        return os.path.join(settings.GRACEDB_DATA_DIR, self.graceid(), subdir)

    def ligoApproved(self):
        return self.approval_set.filter(approvingCollaboration='L').count()

    def virgoApproved(self):
        return self.approval_set.filter(approvingCollaboration='V').count()

    def reportingLatency(self):
        if self.gpstime:
            dt = self.created
            if not dt.tzinfo:
                dt = SERVER_TZ.localize(dt)
            posix_time = time.mktime(dt.timetuple())
            gps_time = int(posixToGpsTime(posix_time))
            return gps_time - self.gpstime

    def neighbors(self, neighborhood=None):
        if not self.gpstime:
            return []
        if self.group.name == 'Test':
            nearby = Event.objects.filter(group__name='Test')
        else:
            nearby = Event.objects.exclude(group__name='Test')

        delta, delta2 = neighborhood or self.DEFAULT_EVENT_NEIGHBORHOOD

        nearby = nearby.filter(gpstime__range=(self.gpstime-delta, self.gpstime+delta2))
        nearby = nearby.exclude(id=self.id)
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
        if (id[0] == "H") and (e.analysisType == "HWINJ"):
            return e
        if (id[0] == "E") and (e.analysisType == "GRB"):
            return e
        if (id[0] == "G"):
            return e
        raise cls.DoesNotExist("Event matching query does not exist")

    def __unicode__(self):
        return self.graceid()

class EventLog(models.Model):
    class Meta:
        ordering = ["-created"]
    event = models.ForeignKey(Event, null=False)
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(User)
    filename = models.CharField(max_length=100, default="")
    comment = models.TextField(null=False)

    def fileurl(self):
        if self.filename:
            return reverse('file', args=[self.event.graceid(), self.filename])
            #return os.path.join(self.event.weburl(), 'private', self.filename)
        else:
            return None

    def hasImage(self):
        # XXX hacky
        return self.filename and self.filename[-3:].lower() in ['png','gif','jpg']

class Labelling(models.Model):
    event = models.ForeignKey(Event)
    label = models.ForeignKey(Label)
    creator = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)

# XXX Deprecated?  Is this used *anywhere*?
# Appears to only be used in models.py.  Here and Event class as approval_set
class Approval(models.Model):
    COLLABORATION_CHOICES = ( ('L','LIGO'), ('V','Virgo'), )
    approver = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    approvedEvent = models.ForeignKey(Event, null=False)
    approvingCollaboration = models.CharField(max_length=1, choices=COLLABORATION_CHOICES)

## Analysis Specific Attributes.

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

## Slots (user-defined event attributes)

class Slot(models.Model):
    """Slot Model"""
    # Does the slot need to have a submitter column?
    class Meta:
        unique_together = (('event', 'name'))
    event = models.ForeignKey(Event)
    name  = models.CharField(max_length=100)
    value = models.CharField(max_length=100)

    # In case the slot value is not a filename, this will just return None.
    def fileurl(self):
        if self.value:
            return reverse('file', args=[self.event.graceid(), self.value])
        else:
            return None

