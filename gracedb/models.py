from django.db import models
import datetime
import thread
import string
import os


from gracedb.ligolw.models import CoincEvent
from gracedb.utils import posixToGpsTime

from django.conf import settings
import pytz, time

SERVER_TZ = pytz.timezone(settings.TIME_ZONE)

# Let's say we start here on schema versions
schema_version = "1.0"

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
    submitter = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group)
    analysisType = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)
    # From ligolw coinc_event table -- none are required.  yet.
    instruments = models.CharField(max_length=20, default="")
    nevents = models.PositiveIntegerField(null=True)
    far = models.FloatField(null=True)
    likelihood = models.FloatField(null=True)
    coincEvent = models.ForeignKey(CoincEvent, null=True)

    # NOT from coinc_event, but so, so common.
    #   Note that the semantics for this is different depending
    #   on search type, so in some sense, querying on this may
    #   be considered, umm, wrong?  But it is a starting point.
    gpstime = models.PositiveIntegerField(null=True)

    # XXX Deprecated.  Only useful for old test data.
    # Remove this when it won't freak people out to lose
    # old date encoded uids.
    uid = models.CharField(max_length=20, unique=False, default="")

    labels = models.ManyToManyField(Label, through="Labelling")

    class Meta:
        ordering = ["-id"]

    def graceid(self):
        if self.uid:
            return self.uid
        elif self.group.name == "Test":
            return "T%04d" % self.id
        elif self.analysisType == "HWINJ":
            return "H%04d" % self.id
        return "G%04d" % self.id

    def weburl(self):
        return "https://ldas-jobs.phys.uwm.edu/gracedb/data/%s" % self.graceid()

    def wikiurl(self):
        return "https://www.lsc-group.phys.uwm.edu/twiki/bin/view/Sandbox/%s" % self.graceid()

    def clusterurl(self):
        #return "pcdev1.phys.uwm.edu:/archive/gracedb/data/%s" % self.graceid()
        return "file://pcdev1.phys.uwm.edu/archive/gracedb/data/%s" % self.graceid()

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

    def neighbors(self, delta=5):
        if not self.gpstime:
            return []
        if self.group.name == 'Test':
            nearby = Event.objects.filter(group__name='Test')
        else:
            nearby = Event.objects.exclude(group__name='Test')
        nearby = nearby.filter(gpstime__range=(self.gpstime-delta, self.gpstime+delta))
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
        if id[0] not in "GHT":
            # Very old, probably useless data.
            return cls.objects.get(uid=id)
        e = cls.objects.get(id=int(id[1:]))
        if (id[0] == "T") and (e.group.name != "Test"):
            raise cls.DoesNotExist()
        if (id[0] == "H") and (e.analysisType == "HWINJ"):
            raise cls.DoesNotExist()
        return e

    def __unicode__(self):
        return self.graceid()

class EventLog(models.Model):
    class Meta:
        ordering = ["-created"]
    event = models.ForeignKey(Event, null=False)
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(User)
    filename = models.CharField(max_length=100, default="")
    comment = models.CharField(max_length=200, null=False, default="")

    def fileurl(self):
        if self.filename:
            return os.path.join(self.event.weburl(), 'private', self.filename)
        else:
            return None

class Labelling(models.Model):
    event = models.ForeignKey(Event)
    label = models.ForeignKey(Label)
    creator = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)

class Approval(models.Model):
    COLLABORATION_CHOICES = ( ('L','LIGO'), ('V','Virgo'), )
    approver = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    approvedEvent = models.ForeignKey(Event, null=False)
    approvingCollaboration = models.CharField(max_length=1, choices=COLLABORATION_CHOICES)

