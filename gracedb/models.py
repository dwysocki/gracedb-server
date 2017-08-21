from django.db import models, IntegrityError
from django.urls import reverse

from model_utils.managers import InheritanceManager

from django.contrib.auth.models import User as DjangoUser
#from django.contrib.auth.models import Group
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

# XXX ER2.utils.  utils is in project directory.  ugh.
from utils import posixToGpsTime

from django.conf import settings
import pytz
import calendar

from cStringIO import StringIO
from hashlib import sha1

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
    name = models.CharField(max_length=100)
    # XXX Need any additional fields? Like a librarian email? Or perhaps even fk?
    def __unicode__(self):
        return self.name

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
    defaultColor = models.CharField(max_length=20, unique=False, default="black")
    description = models.TextField(blank=False)
    def __unicode__(self):
        return self.name

DEFAULT_PIPELINE_ID = 1

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

    submitter = models.ForeignKey(DjangoUser)
    created = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group)
    #uid = models.CharField(max_length=20, default="")  # XXX deprecated.  should be removed.
    #analysisType = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)

    # Note: a default value is needed only during the schema migration
    # that creates this column. After that, we can safely remove it.
    # The presence or absence of the default value has no effect on the DB
    # tables, so removing it does not necessitate a migration.
    #pipeline = models.ForeignKey(Pipeline, default=DEFAULT_PIPELINE_ID)
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
        return reverse('file_list', args=[self.graceid()])

    def datadir(self):
        # Create a file-like object which is the SHA-1 hexdigest of the Event's primary key
        hdf = StringIO(sha1(str(self.id)).hexdigest())

        # Build up the nodes of the directory structure
        nodes = [hdf.read(i) for i in settings.GRACEDB_DIR_DIGITS]

        # Read whatever is left over. This is the 'leaf' directory.
        nodes.append(hdf.read())
        return os.path.join(settings.GRACEDB_DATA_DIR, *nodes)

    def ligoApproved(self):
        return self.approval_set.filter(approvingCollaboration='L').count()

    def virgoApproved(self):
        return self.approval_set.filter(approvingCollaboration='V').count()

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
        if (id[0] == "H") and (e.pipeline.name == "HardwareInjection"):
            return e
        if (id[0] == "E") and (e.group.name == "External"):
            return e
        if (id[0] == "M") and (e.search.name == "MDC"):
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
            for tag in log.tag_set.all():
                if tag.name==tagname:
                    loglist.append(log)
        return loglist

    # A method to update the permissions according to the permission objects in 
    # the database. 
    def refresh_perms(self):
        # Content type is 'Event', obvs.
        content_type = ContentType.objects.get(app_label='gracedb', model='event')
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

class AutoIncrementModel(models.Model):
    """
    An abstract class used as a base for classes which need the
    autoincrementing save method described below.
    """

    class Meta:
        abstract = True

    def save(self, auto_field, auto_fk, *args, **kwargs):
        """
        This custom save method does a SELECT and INSERT in a single raw SQL
        query in order to properly handle a quasi-autoincrementing field, which
        is used to identify instances associated with a ForeignKey. With this
        method, concurrency issues are handled by the database backend.
        Ex: EventLog instances associated with an Event should be numbered 1-N.

        This has been tested with the following classes:
            EventLog, EMObservation, EMFootprint, EMBBEventLog

        Thorough testing is needed to use this method for a new model. Note
        that this method may not work properly for non-MySQL backends.

        Arguments:
            auto_field: name of field which acts as an autoincrement field.
            auto_fk:    name of ForeignKey to which the auto_field is relative.
        """

        # Do normal save if this is not an insert (i.e., the instance has a
        # primary key already).
        meta = self.__class__._meta
        pk_set = self._get_pk_val(meta) is not None
        if pk_set:
            super(AutoIncrementModel, self).save(*args, **kwargs)
            return

        # Otherwise, we'll generate some raw SQL to do the
        # insert and auto-increment.

        # Get model fields, except for primary key field.
        fields = meta.local_concrete_fields
        if not pk_set:
            fields = [f for f in fields if not
                isinstance(f, models.fields.AutoField)]

        # Setup for generating base SQL query for doing an INSERT.
        query = models.sql.InsertQuery(self.__class__._base_manager.model)
        query.insert_values(fields, objs=[self])
        compiler = query.get_compiler(using=self.__class__._base_manager.db)
        compiler.return_id = meta.has_auto_field and not pk_set

        fk_name = meta.get_field(auto_fk).column
        with compiler.connection.cursor() as cursor:
            # Get base SQL query as string.
            for sql, params in compiler.as_sql():
                # Modify SQL string to do an INSERT with SELECT.
                # NOTE: it's unlikely that the following will generate
                # a functional database query for non-MySQL backends.

                # Replace VALUES (%s, %s, ..., %s) with
                # SELECT %s, %s, ..., %s
                sql = re.sub(r"VALUES \((.*)\)", r"SELECT \1", sql)

                # Add table to SELECT from and ForeignKey id corresponding to
                # our autoincrement field.
                sql += " FROM `{tbl_name}` WHERE `{fk_name}`={fk_id}".format(
                    tbl_name=meta.db_table,
                    fk_name=fk_name,
                    fk_id=getattr(self, fk_name)
                    )

                # Get index corresponding to auto_field.
                af_idx = [f.name for f in fields].index(auto_field)
                # Put this directly in the SQL; cursor.execute quotes it
                # as a literal, which causes the SQL command to fail.
                # We shouldn't have issues with SQL injection because
                # auto_field should never be a user-defined parameter.
                del params[af_idx]
                sql = re.sub(r"((%s, ){{{0}}})%s".format(af_idx),
                    r"\1IFNULL(MAX({af}),0)+1", sql, 1).format(af=auto_field)

                # Execute SQL command.
                cursor.execute(sql, params)

            # Get primary key from database and set it in memory.
            if compiler.connection.features.can_return_id_from_insert:
                id = compiler.connection.ops.fetch_returned_insert_id(cursor)
            else:
                id = compiler.connection.ops.last_insert_id(cursor,
                    meta.db_table, meta.pk.column)
            self._set_pk_val(id)

            # Refresh object in memory in order to get auto_field value.
            self.refresh_from_db()
            
class EventLog(AutoIncrementModel):
    class Meta:
        ordering = ['-created','-N']
        unique_together = ('event','N')
    event = models.ForeignKey(Event, null=False)
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(DjangoUser)
    filename = models.CharField(max_length=100, default="")
    comment = models.TextField(null=False)
    #XXX Does this need to be indexed for better performance?
    N = models.IntegerField(null=False)
    file_version = models.IntegerField(null=True)

    def fileurl(self):
        if self.filename:
            actual_filename = self.filename
            if self.file_version >= 0:
                actual_filename += ',%d' % self.file_version
            return reverse('file', args=[self.event.graceid(), actual_filename])
        else:
            return None

    def hasImage(self):
        # XXX hacky
        return self.filename and self.filename[-3:].lower() in ['png','gif','jpg']

    def save(self, *args, **kwargs):
        # XXX filename must not be 'None' because null=False for the filename
        # field above.
        self.filename = self.filename or ""

        # Set up to call save method of the base class (AutoIncrementModel)
        kwargs.update({'auto_field': 'N', 'auto_fk': 'event'})
        super(EventLog, self).save(*args, **kwargs)

class EMGroup(models.Model):
    name = models.CharField(max_length=50, unique=True)

    # XXX what else? Possibly the liasons. These can be populated 
    # automatically from the gw-astronomy COManage-provisioned LDAP.
    # Let's leave this out for now. The submitter will be stored in 
    # the EMBB log record, and that should be enough for audit/blame
    # purposes.
    #liasons = models.ManyToManyField(DjangoUser)

    # XXX Characteristics needed to produce pointings?

    def __unicode__(self):
        return self.name

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

class EMObservation(AutoIncrementModel):
    """
    EMObservation:  An observation record for EM followup.  
    """
    class Meta:
        ordering = ['-created', '-N']
        unique_together = ("event","N")

    def __unicode__(self):
        return "%s-%s-%d" % (self.event.graceid(), self.group.name, self.N)

    N = models.IntegerField(null=False)
    created = models.DateTimeField(auto_now_add=True)
    event = models.ForeignKey(Event)
    submitter  = models.ForeignKey(DjangoUser)  

    # The MOU group responsible 
    group = models.ForeignKey(EMGroup)       # from a table of facilities

    # The following fields should be calculated from the footprint info provided
    # by the user. These fields are just for convenience and fast searching

    # The center of the bounding box of the rectangular footprints ra,dec
    # in J2000 in decimal degrees
    ra         = models.FloatField(null=True)
    dec        = models.FloatField(null=True)    

    # The width and height (RA range and Dec range) in decimal degrees 
    raWidth    = models.FloatField(null=True)
    decWidth   = models.FloatField(null=True)    

    comment = models.TextField(blank=True)

    def save(self, *args, **kwargs):
        # Set up to call save method of the base class (AutoIncrementModel)
        kwargs.update({'auto_field': 'N', 'auto_fk': 'event'})
        super(EMObservation, self).save(*args, **kwargs)

    def calculateCoveringRegion(self):
        # How to access the related footprint objects?
        footprints = self.emfootprint_set.all()
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

class EMFootprint(AutoIncrementModel):
    """
    A single footprint associated with an observation.
    Each EMObservation can have many footprints underneath.

    None of the fields are optional here.
    """
    class Meta:
        ordering = ['-N']
        unique_together = ("observation","N")

    N = models.IntegerField(null=False)

    observation = models.ForeignKey(EMObservation, null = False)

    # The center of the rectangular footprint, right ascension and declination
    # in J2000 in decimal degrees
    ra         = models.FloatField()
    dec        = models.FloatField()    

    # The width and height (RA range and Dec range) in decimal degrees 
    raWidth    = models.FloatField()
    decWidth   = models.FloatField()    

    # The start time of the observation for this footprint
    start_time = models.DateTimeField()

    # The exposure time in seconds for this footprint
    exposure_time = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        # Set up to call save method of the base class (AutoIncrementModel)
        kwargs.update({'auto_field': 'N', 'auto_fk': 'observation'})
        super(EMFootprint, self).save(*args, **kwargs)

class EMBBEventLog(AutoIncrementModel):
    """EMBB EventLog:  A multi-purpose annotation for EM followup.
     
    A rectangle on the sky, equatorially aligned,
    that has or will be imaged that is related to an event"""

    class Meta:
        ordering = ['-created', '-N']
        unique_together = ("event","N")

    def __unicode__(self):
        return "%s-%s-%d" % (self.event.graceid(), self.group.name, self.N)

    # A counter for Eels associated with a given event. This is 
    # important for addressibility.
    N = models.IntegerField(null=False)
    
    # The time at which this Eel was created. Important for event auditing.
    created = models.DateTimeField(auto_now_add=True)

    # The gracedb event that this Eel relates to
    event = models.ForeignKey(Event)

    # The responsible author of this communication
    submitter  = models.ForeignKey(DjangoUser)  # from a table of people

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

    def save(self, *args, **kwargs):
        # Set up for calling save method of the base class (AutoIncrementModel)
        kwargs.update({'auto_field': 'N', 'auto_fk': 'event'})
        super(EMBBEventLog, self).save(*args, **kwargs)

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
    channel           = models.CharField(max_length=20, blank=True)
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
                # Only set value of class instance member if
                # value is not None or if field is nullable.
                # Otherwise we could overwrite non-nullable fields
                # which have default values with None.
                if value is not None or f.null:
                    #log.debug("Setting column '%s' with value '%s'" % (column, value))
                    setattr(e, f.attname, value)
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
    source_channel       = models.CharField(max_length=50, blank=True, default="")
    destination_channel  = models.CharField(max_length=50, blank=True, default="")

    @classmethod
    def field_names(cls):
        try:
            return cls._field_names
        except AttributeError: pass
        # We only care about the model field names in this particular case.
        cls._field_names = [ x.name for x in cls._meta.get_fields(include_parents=False) ]
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

class VOEvent(models.Model):
    class Meta:
        ordering = ['-created','-N']
        unique_together = ("event","N")
    # Now N will be the serial number.
    event = models.ForeignKey(Event, null=False)
    created = models.DateTimeField(auto_now_add=True)
    issuer = models.ForeignKey(DjangoUser)
    ivorn = models.CharField(max_length=200, default="")
    filename = models.CharField(max_length=100, default="")
    file_version = models.IntegerField(null=True)
    N = models.IntegerField(null=False)
    VOEVENT_TYPE_CHOICES = (('PR','preliminary'), ('IN','initial'), ('UP','update'), ('RE', 'retraction'),)
    voevent_type = models.CharField(max_length=2, choices=VOEVENT_TYPE_CHOICES)

    def fileurl(self):
        if self.filename:
            actual_filename = self.filename
            if self.file_version >= 0:
                actual_filename += ',%d' % self.file_version
            return reverse('file', args=[self.event.graceid(), actual_filename])
        else:
            return None

    def save(self, *args, **kwargs):
        success = False
        # XXX filename must not be 'None' because null=False for the filename
        # field above.
        self.filename = self.filename or ""
        attempts = 0
        while (not success and attempts < 5):
            attempts = attempts + 1
            if not self.N:
                if self.event.voevent_set.count():
                    self.N = int(self.event.voevent_set.aggregate(models.Max('N'))['N__max']) + 1
                else:
                    self.N = 1
            try:
                super(VOEvent, self).save(*args, **kwargs)
                success = True
            except IntegrityError:
                # IntegrityError means an attempt to insert a duplicate
                # key or to violate a foreignkey constraint.
                # We are under race conditions.  Let's try again.
                pass

        if not success:
            # XXX Should this be a custom exception?  That way we could catch it
            # in the views that use it and give an informative error message.
            raise Exception("Too many attempts to save log message. Something is wrong.")

INSTRUMENTS = ( ('H1', 'LHO'), ('L1', 'LLO'), ('V1', 'Virgo') )
OPERATOR_STATUSES = ( ('OK', 'OKAY'), ('NO', 'NOT OKAY') )
SIGNOFF_TYPE_CHOICES = ( ('OP', 'operator'), ('ADV', 'advocate') )
class Signoff(models.Model):
    class Meta:
        unique_together = ("event","instrument")
    submitter = models.ForeignKey(DjangoUser)
    event = models.ForeignKey(Event)
    signoff_type = models.CharField(max_length=3, choices=SIGNOFF_TYPE_CHOICES, blank=False)
    instrument = models.CharField(max_length=2, choices=INSTRUMENTS, blank=True)
    status = models.CharField(max_length=2, choices=OPERATOR_STATUSES, blank=False)
    comment = models.TextField(blank=True)

    def __unicode__(self):
        return "%s | %s | %s" % (self.event.graceid(), self.instrument, self.status)

