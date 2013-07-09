from django.db import models, IntegrityError
from django.core.urlresolvers import reverse

from model_utils.managers import InheritanceManager

from django.contrib.auth.models import User as DjangoUser


import datetime
import thread
import string
import os
import logging

import glue
import glue.ligolw
import glue.ligolw.utils
import glue.ligolw.table
import glue.ligolw.lsctables
from glue.lal import LIGOTimeGPS

log = logging.getLogger('gracedb.models')

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
    DEFAULT_EVENT_NEIGHBORHOOD = (-5,5)

    submitter = models.ForeignKey(DjangoUser)
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
        if (id[0] == "H") and (e.analysisType == "HWINJ"):
            return e
        if (id[0] == "E") and (e.analysisType == "GRB"):
            return e
        if (id[0] == "G"):
            return e
        raise cls.DoesNotExist("Event matching query does not exist")

    def __unicode__(self):
        return self.graceid()

    # Return a list of distinct tags associated with the log messages of this
    # event.
    def getAvailableTags(self):
        tagset_list = [log.tag_set.all() for log in self.eventlog_set.all()]
        taglist = []
        for tagset in tagset_list:
            for tag in tagset:
                taglist.append(tag)
        # Eliminate duplicates
        return list(set(taglist))

    def getLogsForTag(self,tagname):
        loglist = []
        for log in self.eventlog_set.all():
            for tag in log.tag_set.all():
                if tag.name==tagname:
                    loglist.append(log)
        return loglist

class EventLog(models.Model):
    class Meta:
        ordering = ['-created','-N']
        unique_together = ("event","N")
    event = models.ForeignKey(Event, null=False)
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(DjangoUser)
    filename = models.CharField(max_length=100, default="")
    comment = models.TextField(null=False)
    #XXX Does this need to be indexed for better performance?
    N = models.IntegerField(null=False)

    def fileurl(self):
        if self.filename:
            return reverse('file', args=[self.event.graceid(), self.filename])
            #return os.path.join(self.event.weburl(), 'private', self.filename)
        else:
            return None

    def hasImage(self):
        # XXX hacky
        return self.filename and self.filename[-3:].lower() in ['png','gif','jpg']

    def save(self, *args, **kwargs):
        success = False
        # XXX filename must not be 'None' because null=False for the filename
        # field above.
        self.filename = self.filename or ""
        attempts = 0
        while (not success and attempts < 5):
            attempts = attempts + 1
            if self.event.eventlog_set.count():
                self.N = int(self.event.eventlog_set.aggregate(models.Max('N'))['N__max']) + 1
            else:
                self.N = 1
            try:
                super(EventLog, self).save(*args, **kwargs)
                success = True
            except IntegrityError as e:
                # IntegrityError means an attempt to insert a duplicate
                # key or to violate a foreignkey constraint.
                # We are under race conditions.  Let's try again.
                pass

        if not success:
            # XXX Should this be a custom exception?  That way we could catch it
            # in the views that use it and give an informative error message.
            raise Exception("Too many attempts to save log message. Something is wrong.")

class Labelling(models.Model):
    event = models.ForeignKey(Event)
    label = models.ForeignKey(Label)
    creator = models.ForeignKey(DjangoUser)
    created = models.DateTimeField(auto_now_add=True)

# XXX Deprecated?  Is this used *anywhere*?
# Appears to only be used in models.py.  Here and Event class as approval_set
class Approval(models.Model):
    COLLABORATION_CHOICES = ( ('L','LIGO'), ('V','Virgo'), )
    approver = models.ForeignKey(DjangoUser)
    created = models.DateTimeField(auto_now_add=True)
    approvedEvent = models.ForeignKey(Event, null=False)
    approvingCollaboration = models.CharField(max_length=1, choices=COLLABORATION_CHOICES)

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

class SingleInspiral(models.Model):
    event             = models.ForeignKey(Event, null=False)
    ifo               = models.CharField(max_length=20, null=True)
    search            = models.CharField(max_length=20, null=True)
    channel           = models.CharField(max_length=20)
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

    def end_time_full(self):
        return LIGOTimeGPS(self.end_time, self.end_time_ns)

    def impulse_time_full(self):
        return LIGOTimeGPS(self.impulse_time, self.impulse_time_ns)

    @classmethod
    def create_events_from_ligolw_table(cls, table, event):
        """For an Event, given a table (loaded by ligolw.utils.load_filename or similar) create SingleEvent tables for the event"""

        field_names = cls.field_names()
        created_events = []

        log.debug("Single/create from table/fields: " + str(field_names))

        for row in table:
            e = cls(event=event)
            log.debug("Single/creating event")
            for column in field_names:
                value = getattr(row, column)
                log.debug("Setting column '%s' with value '%s'" % (column, value))
                setattr(e, column, value)
            e.save()
            created_events.append(e)

        return created_events

    @classmethod
    def update_event(cls, event, datafile=None):
        """Given an Event (and optional location of coinc.xml) update SingleInspiral data"""
        # XXX Need a better way to find original data.
        if datafile is None:
            datafile = os.path.join(event.datadir(), 'coinc.xml')

        try:
            xmldoc = glue.ligolw.utils.load_filename(datafile)
        except IOError:
            return None

        # Extract Single Inspiral Information
        s_inspiral_tables = glue.ligolw.table.getTablesByName(
                xmldoc,
                glue.ligolw.lsctables.SnglInspiralTable.tableName)

        # Concatentate the tables' rows into a single table
        table = sum(s_inspiral_tables, [])

        event.singleinspiral_set.all().delete()

        return cls.create_events_from_ligolw_table(table, event)

    @classmethod
    def field_names(cls):
        try:
            return cls._field_names
        except AttributeError: pass
        model_field_names = set([ x.name for x in cls._meta.fields ])
        ligolw_field_names = set(
                glue.ligolw.lsctables.SnglInspiralTable.validcolumns.keys())

        cls._field_names = model_field_names.intersection(ligolw_field_names)
        return cls._field_names


## Tags (user-defined log message attributes)
class Tag(models.Model):
    """Tag Model"""
    # XXX Does the tag need to have a submitter column?
    # No, because creating a tag will generate a log message.
    # For the same reason, a timstamp is not necessary.
    eventlogs   = models.ManyToManyField(EventLog)
    name        = models.CharField(max_length=100)
    displayName = models.CharField(max_length=200,null=True)

    def __unicode__(self):
        if self.displayName:
            return self.displayName
        else:
            return self.name

#     def getEvents(self):
#         # XXX Any way of doing this with filters?
#         # We would need to filter for a non-null intersection of the 
#         # set of log messages in the event with the set of log 
#         # messages in the tag.
#         eventlist = [log.event for log in self.eventlogs.all()]

