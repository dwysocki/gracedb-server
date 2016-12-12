
from django.http import HttpResponse, HttpResponseBadRequest
from django.core.urlresolvers import reverse as django_reverse
from django.utils import dateformat
from django.utils.html import escape, urlize
#from django.utils.http import urlquote
from django.utils.safestring import mark_safe

from gracedb.models import SingleInspiral, Event, Search, Group

from utils.vfile import VersionedFile
from permission_utils import is_external
from django.db.models import Q

import os
from django.conf import settings

from templatetags.scientific import scientific

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

# The maximum number of rows to be returned by flexigridResponse
# in the event that the user asks for all of them.
MAX_FLEXI_ROWS = 250

GRACEDB_DATA_DIR = settings.GRACEDB_DATA_DIR

import logging
log = logging.getLogger(__name__)

import json
import pytz

import time
import calendar

from django.utils import timezone
from datetime import datetime, timedelta

SERVER_TZ = pytz.timezone(settings.TIME_ZONE)
def timeToUTC(dt):
    if not dt.tzinfo:
        dt = SERVER_TZ.localize(dt)
    return dateformat.format(dt.astimezone(pytz.utc), settings.GRACE_DATETIME_FORMAT)

#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------
# Modified reverse for REST API and serializers below
#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------

from rest_framework.reverse import reverse as rest_framework_reverse
from django.core.urlresolvers import resolve, get_script_prefix

# Note about reverse() in this file -- there are THREE versions of it here.
  #
  # SOURCE                               LOCAL NAME
  # django.core.urlresolvers.reverse ==> django_reverse
  # rest_framework.reverse.reverse   ==> rest_framework_reverse
  # reverse defined below            ==> reverse
  #
  # The Django reverse returns relative paths.
  #
  # The rest framework reverse is basically the same as the Django version
  # but will return full paths if the request is passed in using the request kw arg.
  #
  # The reverse defined below is basically the rest framework reverse, but
  # will attempt to deal with multiply-include()-ed url.py-type files with
  # different namespaces.  (see the comments in the function)
def reverse(name, *args, **kw):
      """Find a URL.  Respect where that URL was defined in urls.py
  
      Allow for a set of URLs to have been include()-ed on multiple URL paths.
  
      eg  urlpatterns = (
          (r'^api1/', include('someapp.urls', app_name="api", namespace="x509")),
          (r'^api2/', include('someapp.urls', app_name="api", namespace="shib")),
          ...)
  
      then reverse("api:root", request=self.request) will give the obviously
      correct full URL for the URL named "root" in someapp/urls.py.  Django's
      reverse will pick one URL path and use it no matter what path the
      URL resolver flows through and it will do so whether you specify an app_name
      or not.
  
      This function solves that issue.  app_name and namespace are required.
      The request must be the value at kw['request']
  
      Assembled with hints from http://stackoverflow.com/a/13249060
      """
      # XXX rashly assuming app is "api:"  brutal.
      if type(name) == str and not name.startswith("api:"):
          name = "api:"+name
  
      # Idea is to put 'current_app' into the kw args of reverse
      # where current_app is the namespace of the urlpattern we got here from.
      # Given that, reverse will find the right patterns in your urlpatterns.
      # I do know know why Django does not do this by default.
  
      # This probably only works if you give app_names which are the same
      # and namespaces that are different.
  
      if 'request' in kw and 'current_app' not in kw:
          request = kw['request']
          # For some reason, resolve() does not seem to like the script_prefix.
          # So, remove it.
          prefix = get_script_prefix()
          path = request.path.replace(prefix, '/')
          current_app = resolve(path).namespace
          kw['current_app'] = current_app
  
      return rest_framework_reverse(name, *args, **kw)


#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------
# Custom serializers 
#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------

def eventToDict(event, columns=None, request=None):
    """Convert an Event to a dictionary."""
    rv = {}
    graceid = event.graceid()
    try:
      rv['submitter'] = event.submitter.username
    except:
      rv['submitter'] = 'Unknown'

    rv['created'] = timeToUTC(event.created)
    rv['group'] = event.group.name
    rv['graceid'] = graceid
    rv['pipeline'] = event.pipeline.name
    if event.search:
        rv['search'] = event.search.name
    rv['gpstime'] = event.gpstime
    rv['instruments'] = event.instruments
    rv['nevents'] = event.nevents

    far_is_upper_limit = False
    display_far = event.far
    if event.far and request and is_external(request.user):
        if event.far < settings.VOEVENT_FAR_FLOOR:
            display_far = settings.VOEVENT_FAR_FLOOR
            far_is_upper_limit = True

    rv['far'] = display_far
    rv['far_is_upper_limit'] = far_is_upper_limit
    rv['likelihood'] = event.likelihood
    rv['labels'] = dict([
          (labelling.label.name,
              reverse("labels",
                  args=[graceid, labelling.label.name],
                  request=request))
          for labelling in event.labelling_set.all()])
    # XXX Try to produce a dictionary of analysis specific attributes.  Duck typing.
    # XXX These extra attributes should only be seen by internal users.
    if request and request.user and not is_external(request.user): 
        rv['extra_attributes'] = {}
        try:
            # GrbEvent
            rv['extra_attributes']['GRB'] = {
                  "ivorn" : event.ivorn,
                  "author_ivorn" : event.author_ivorn,
                  "author_shortname" : event.author_shortname,
                  "observatory_location_id" : event.observatory_location_id,
                  "coord_system" : event.coord_system,
                  "ra" : event.ra,
                  "dec" : event.dec,
                  "error_radius" : event.error_radius,
                  "how_description" : event.how_description,
                  "how_reference_url" : event.how_reference_url,
                  "T90" : event.t90,
                  "trigger_duration": event.trigger_duration,
                  "designation": event.designation,
                  "redshift": event.redshift,
                  "trigger_id": event.trigger_id,
                  }
        except:
            pass
        try:
            # CoincInspiralEvent
            rv['extra_attributes']['CoincInspiral'] = {
                  "ifos" : event.ifos,
                  "end_time" : event.end_time,
                  "end_time_ns" : event.end_time_ns,
                  "mass" : event.mass,
                  "mchirp" : event.mchirp,
                  "minimum_duration" : event.minimum_duration,
                  "snr" : event.snr,
                  "false_alarm_rate" : event.false_alarm_rate,
                  "combined_far" : event.combined_far,
                  }
        except:
            pass
        try:
            # SimInspiralEvent
            rv['extra_attributes']['SimInspiral'] = {
                    "source_channel": event.source_channel,
                    "destination_channel": event.destination_channel,
                    "mass1": event.mass1,
                    "mass2": event.mass2,
                    "eta": event.eta,
                    "mchirp": event.mchirp,
                    "amp_order": event.amp_order,
                    "coa_phase": event.coa_phase,
                    "spin1y": event.spin1y,
                    "spin1x": event.spin1x,
                    "spin1z": event.spin1z,
                    "spin2x": event.spin2x,
                    "spin2y": event.spin2y,
                    "spin2z": event.spin2z,
                    "geocent_end_time": event.geocent_end_time,
                    "geocent_end_time_ns": event.geocent_end_time_ns,
                    "end_time_gmst": event.end_time_gmst,
                    "f_lower": event.f_lower,
                    "f_final": event.f_final,
                    "distance": event.distance,
                    "latitude": event.latitude,
                    "longitude": event.longitude,
                    "polarization": event.polarization,
                    "inclination": event.inclination,
                    "theta0": event.theta0,
                    "phi0": event.phi0,
                    "waveform": event.waveform,
                    "numrel_mode_min": event.numrel_mode_min,
                    "numrel_mode_max": event.numrel_mode_max,
                    "numrel_data": event.numrel_data,
                    "source": event.source,
                    "taper": event.taper,
                    "bandpass": event.bandpass,
                    "alpha": event.alpha,
                    "beta": event.beta,
                    "psi0": event.psi0,
                    "psi3": event.psi3,
                    "alpha1": event.alpha1,
                    "alpha2": event.alpha2,
                    "alpha3": event.alpha3,
                    "alpha4": event.alpha4,
                    "alpha5": event.alpha5,
                    "alpha6": event.alpha6,
                    "g_end_time": event.g_end_time,
                    "g_end_time_ns": event.g_end_time_ns,
                    "h_end_time": event.h_end_time,
                    "h_end_time_ns": event.h_end_time_ns,
                    "l_end_time": event.l_end_time,
                    "l_end_time_ns": event.l_end_time_ns,
                    "t_end_time": event.t_end_time,
                    "t_end_time_ns": event.t_end_time_ns,
                    "v_end_time": event.v_end_time,
                    "v_end_time_ns": event.v_end_time_ns,
                    "eff_dist_g": event.eff_dist_g,
                    "eff_dist_h": event.eff_dist_h,
                    "eff_dist_l": event.eff_dist_l,
                    "eff_dist_t": event.eff_dist_t,
                    "eff_dist_v": event.eff_dist_v,
                }
        except:
            pass
        try:
            # MultiBurstEvent
            rv['extra_attributes']['MultiBurst'] = {
                  "ifos" : event.ifos,
                  "start_time" : event.start_time,
                  "start_time_ns" : event.start_time_ns,
                  "duration" : event.duration,
                  "peak_time" : event.peak_time,
                  "peak_time_ns" : event.peak_time_ns,
                  "central_freq" : event.central_freq,
                  "bandwidth" : event.bandwidth,
                  "amplitude" : event.amplitude,
                  "snr" : event.snr,
                  "confidence" : event.confidence,
                  "false_alarm_rate" : event.false_alarm_rate,
                  "ligo_axis_ra" : event.ligo_axis_ra,
                  "ligo_axis_dec" : event.ligo_axis_dec,
                  "ligo_angle" : event.ligo_angle,
                  "ligo_angle_sig" : event.ligo_angle_sig,
                  }
        except:
            pass
        try:
            # LalInferenceBurstEvent
            rv['extra_attributes']['LalInferenceBurst'] = {
                  "bci" : event.bci,
                  "bsn" : event.bsn,
                  "quality_mean" : event.quality_mean,
                  "quality_median": event.quality_median,
                  "omicron_snr_network" : event.omicron_snr_network,
                  "omicron_snr_H1" : event.omicron_snr_H1,
                  "omicron_snr_L1" : event.omicron_snr_L1,
                  "omicron_snr_V1" : event.omicron_snr_V1,
                  "hrss_mean" : event.hrss_mean,
                  "hrss_median" : event.hrss_median,
                  "frequency_mean": event.frequency_mean,
                  "frequency_median": event.frequency_median,
                  }
        except:
            pass


        # Finally add extra attributes for any SingleInspiral objects associated with this event
        # This will be a list of dictionaries.
        si_set = event.singleinspiral_set.all()
        if si_set.count():
            rv['extra_attributes']['SingleInspiral'] = [ singleInspiralToDict(si) for si in si_set ]
    elif (request and request.user) and (is_external(request.user)):
        try:
            rv['extra_attributes'] = {}
            # Only expose SingleInspiral times and ifos for external users.
            ext_keys = ['ifo','end_time','end_time_ns']
            si_set = event.singleinspiral_set.all()
            if si_set.count():
                SingleInspiral_list = [ singleInspiralToDict(si) for si in si_set ]
                rv['extra_attributes']['SingleInspiral'] = []
                for i, si in enumerate(SingleInspiral_list):
                    rv['extra_attributes']['SingleInspiral'].append({ k: si[k] for k in ext_keys })
        except:
            pass

    rv['links'] = {
          "neighbors" : reverse("neighbors", args=[graceid], request=request),
          "log"   : reverse("eventlog-list", args=[graceid], request=request),
          "emobservations"   : reverse("emobservation-list", args=[graceid], request=request),
          "files" : reverse("files", args=[graceid], request=request),
          "filemeta" : reverse("filemeta", args=[graceid], request=request),
          "labels" : reverse("labels", args=[graceid], request=request),
          "self"  : reverse("event-detail", args=[graceid], request=request),
          "tags"  : reverse("eventtag-list", args=[graceid], request=request),
          }
    return rv

def eventLogToDict(log, request=None):
    uri = None
    taglist_uri = None
    file_uri = None
    if request:
        uri = reverse("eventlog-detail",
                args=[log.event.graceid(), log.N],
                request=request)
        taglist_uri = reverse("eventlogtag-list",
                args=[log.event.graceid(), log.N],
                request=request)
        if log.filename:
            actual_filename = log.filename
            if log.file_version >= 0:
                actual_filename += ',%d' % log.file_version
            # NOTE: the reverse function will return a urlquoted
            # result, so we don't need urlquote here. Effectively
            # escaping twice results in wrong urls. 
            #filename = urlquote(actual_filename)
            filename = actual_filename
            file_uri = reverse("files",
                args=[log.event.graceid(), filename],
                request=request)

    # This is purely for convenience in working with the web interface.
    tag_names = [tag.name for tag in log.tag_set.all() ];

    if len(log.issuer.last_name):
        display_name = "%s %s" % (log.issuer.first_name, log.issuer.last_name)
    else:
        display_name = log.issuer.username

    issuer_info = {
        "username": log.issuer.username,
        "display_name": display_name,
    }

    return {
                "N"            : log.N,
                "comment"      : log.comment,
                "created"      : log.created.isoformat(),
                "issuer"       : issuer_info,
                "filename"     : log.filename,
                "file_version" : log.file_version,
                "tag_names"    : tag_names,
                "self"         : uri,
                "tags"         : taglist_uri,
                "file"         : file_uri,
           }


def labelToDict(label, request=None):
    return { 
            "name" : label.label.name,
            "creator" : label.creator.username,
            "created" : label.created.isoformat(),
            "self" : reverse("labels",
                args=[label.event.graceid(), label.label.name],
                request=request),
           }

# EEL serializer.
def embbEventLogToDict(eel, request=None):
      uri = None
      if request:
          uri = reverse("embbeventlog-detail",
                  args=[eel.event.graceid(), eel.N],
                  request=request)
      return {
                  "N"       : eel.N,
                  "self"    : uri,
                  "created" : eel.created.isoformat(),
                  "submitter"  : eel.submitter.username,
                  "group" : eel.group.name,
                  "instrument" : eel.instrument,
                  "footprintID" : eel.footprintID,
                  "waveband" : eel.waveband,
  
                  "ra"       : eel.ra,
                  "dec"      : eel.dec,
                  "raWidth"  : eel.raWidth,
                  "decWidth" : eel.decWidth,
                  "gpstime"  : eel.gpstime,
                  "duration" : eel.duration,
  
                  "raList"       : json.loads('['+eel.raList+']'),
                  "decList"      : json.loads('['+eel.decList+']'),
                  "raWidthList"  : json.loads('['+eel.raWidthList+']'),
                  "decWidthList" : json.loads('['+eel.decWidthList+']'),
                  "gpstimeList"  : json.loads('['+eel.gpstimeList+']'),
                  "durationList" : json.loads('['+eel.durationList+']'),
  
                  "eel_status" : eel.get_eel_status_display(),
                  "obs_status" : eel.get_obs_status_display(),
                  "comment" : eel.comment,
                  "extra_info_dict" : eel.extra_info_dict,
             }

# EMObservation serializer.
def emObservationToDict(emo, request=None):
      uri = None
      if request:
          uri = reverse("emobservation-detail",
                  args=[emo.event.graceid(), emo.N],
                  request=request)
      
      return {
                  "N"               : emo.N,
                  "footprint_count" : emo.emfootprint_set.count(),
                  "self"            : uri,
                  "created"         : emo.created.isoformat(),
                  "submitter"       : emo.submitter.username,
                  "group"           : emo.group.name,
                  "comment"         : emo.comment,                  
  
                  "ra"       : emo.ra,
                  "dec"      : emo.dec,
                  "raWidth"  : emo.raWidth,
                  "decWidth" : emo.decWidth,
                  "footprints" : [ emFootprintToDict(emf) for emf in emo.emfootprint_set.all()]
              }

# EMFootprint serializer
def emFootprintToDict(emf, request=None):
#      uri = None
#      if request:
#          uri = reverse("emfootprint-detail",
#                  args=[emf.emobservation.event.graceid(), emf.emobservation.N, emf.N],
#                  request=request)
      
      return {
# FIXME: At this point, we're not exposing the individual footprints.
# It would probably be nice to expose these resources, at least to GET.
#                  "self"            : uri,
                  "N"               : emf.N,
                  "ra"              : emf.ra,
                  "dec"             : emf.dec,
                  "raWidth"         : emf.raWidth,
                  "decWidth"        : emf.decWidth,
                  "start_time"      : emf.start_time.isoformat(),
                  "exposure_time"   : emf.exposure_time,
              }

# XXX Eventually hope to remove this
# EMObservation serializer for the skymap Viewer
def skymapViewerEMObservationToDict(emo, request=None):
    uri = None
    if request:
        uri = reverse("emobservation-detail",
                args=[emo.event.graceid(), emo.N],
                request=request)

    # Keys we want:
    # comment - empty
    # footprintID - average time, UTC
    # group
    # decWidthList, raWidthList, raList, decList

    raList = []
    decList = []
    raWidthList = []
    decWidthList = []
    startTimeList = []

    for fp in emo.emfootprint_set.all():
        raList.append(fp.ra)
        decList.append(fp.dec)
        raWidthList.append(fp.raWidth)
        decWidthList.append(fp.decWidth)
        startTimeList.append(fp.start_time)

    # Now find the average start time.
    time_count = 0
    avg_time_s = 0.0
    for t in startTimeList:
        time_count += 1
        # timetuple throws away the microsecond for some reason
        # Note: the datetimes in the startTimeList are in UTC.
        avg_time_s += calendar.timegm(t.timetuple()) + float(t.microsecond)/1e6

    if time_count > 0:
        avg_time_s /= time_count

    avg_time = time.gmtime(avg_time_s)
    avg_time_string = avg_time.strftime("%a %b %d %H:%M:%S UTC %Y")
          
    return {
                "N"               : emo.N,
                "self"            : uri,
                "created"         : emo.created.isoformat(),
                "submitter"       : emo.submitter.username,
                "comment"         : emo.comment,
                "footprintID"     : avg_time_string,
                "group"           : emo.group.name,
  
                "raList"       : raList,
                "decList"      : decList,
                "raWidthList"  : raWidthList,
                "decWidthList" : decWidthList,
            }

  
# VOEvent serializer
def voeventToDict(voevent, request=None):
    # NOTE the urlquote will be done by the reverse function.
    #filename = urlquote('%s,%d' % (voevent.filename, voevent.file_version))
    filename = '%s,%d' % (voevent.filename, voevent.file_version)

    uri = None
    file_uri = None
    if request:
        uri = reverse("voevent-detail",
                args=[voevent.event.graceid(), voevent.N],
                request=request)
        file_uri = reverse("files",
            args=[voevent.event.graceid(), filename],
            request=request)

    issuer_info = {
        "username": voevent.issuer.username,
        "display_name": "%s %s" % (voevent.issuer.first_name, voevent.issuer.last_name),
    }

    # Read in the filecontents
    filepath = os.path.join(voevent.event.datadir(), voevent.filename)
    text = None
    try: 
        text = open(filepath, 'r').read()
    except:
        pass

    return {
                "self"         : uri,
                "text"         : text,
                "file"         : file_uri,
                "N"            : voevent.N,
                "issuer"       : issuer_info,
                "ivorn"        : voevent.ivorn,
                "filename"     : voevent.filename,
                "file_version" : voevent.file_version,
                "voevent_type" : voevent.voevent_type,
                "created"      : voevent.created.isoformat(),
           }

def singleInspiralToDict(single_inspiral):
    rv = {}
    for field_name in SingleInspiral.field_names():
        value = getattr(single_inspiral, field_name, None)
        if value:
            rv.update({ field_name: value })
    return rv

def signoffToDict(signoff):
    return {
        'submitter':    signoff.submitter.username,
        'instrument':   signoff.instrument,
        'status':       signoff.status,
        'comment':      signoff.comment,
        'signoff_type': signoff.signoff_type
    } 

#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------
# Miscellany
#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------

def assembleLigoLw(objects):
    from glue.ligolw import ligolw
    # lsctables MUST be loaded before utils.
    from glue.ligolw import utils
    from glue.ligolw.utils import ligolw_add
    from glue.ligolw.ligolw import LIGOLWContentHandler
    from glue.ligolw.lsctables import use_in

    use_in(LIGOLWContentHandler)

    xmldoc = ligolw.Document()
    for obj in objects:
        fname = os.path.join(obj.datadir(), "coinc.xml")
        utils.load_filename(fname, xmldoc=xmldoc, contenthandler=LIGOLWContentHandler)

    ligolw_add.reassign_ids(xmldoc)
    ligolw_add.merge_ligolws(xmldoc)
    ligolw_add.merge_compatible_tables(xmldoc)
    return xmldoc

def _saveUploadedFile(event, uploadedFile):
    fname = os.path.join(event.datadir(), uploadedFile.name)
    f = VersionedFile(fname, "w")
    for chunk in uploadedFile.chunks():
        f.write(chunk)
    f.close()
    return f.version

import html5lib
def sanitize_html(data):
    """

    >>> sanitize_html5lib("foobar<p>adf<i></p>abc</i>")
    u'foobar<p>adf<i></i></p><i>abc</i>'
    >>> sanitize_html5lib('foobar<p style="color:red; remove:me; background-image: url(http://example.com/test.php?query_string=bad);">adf<script>alert("Uhoh!")</script><i></p>abc</i>')
    u'foobar<p style="color: red;">adf&lt;script&gt;alert("Uhoh!")&lt;/script&gt;<i></i></p><i>abc</i>'
    """
    from html5lib import treebuilders, treewalkers, serializer, sanitizer

    p = html5lib.HTMLParser(tokenizer=sanitizer.HTMLSanitizer, tree=treebuilders.getTreeBuilder("dom"))
    dom_tree = p.parseFragment(data)

    walker = treewalkers.getTreeWalker("dom")

    stream = walker(dom_tree)

    s = serializer.htmlserializer.HTMLSerializer(omit_optional_tags=False)
    return "".join(s.serialize(stream))

from templatetags.timeutil import timeSelections

def jqgridResponse(request, objects):
    # "GET /data?_search=false&nd=1266350238476&rows=10&page=1&sidx=invid&sord=asc HTTP/1.1"
    pass

def flexigridResponse(request, objects):
    response = HttpResponse(content_type='application/json')

    #sortname = request.POST.get('sortname', None)
    #sortorder = request.POST.get('sortorder', 'desc')
    #page = int(request.POST.get('page', 1))
    #rp = int(request.POST.get('rp', 10))

    sortname = request.GET.get('sidx', None)    # get index row - i.e. user click to sort
    sortorder = request.GET.get('sord', 'desc') # get the direction
    page = int(request.GET.get('page', 1))      # get the requested page
    rp = int(request.GET.get('rows', 10))       # get how many rows we want to have into the grid

    get_neighbors = request.GET.get('get_neighbors', False) # whether to retrieve the neighbors

    # select related objects to reduce the number of queries.
    objects = objects.select_related('group', 'pipeline', 'search', 'submitter')

    if sortname:
        if sortorder == "desc":
            sortname = "-" + sortname
        objects = objects.order_by(sortname)

    total = objects.count()
    rows = []
    if rp > -1:
        start = (page-1) * rp

        if total:
            total_pages = (total / rp) + 1
        else:
            total_pages = 0

        if page > total_pages:
            page = total_pages
        
        end = start+rp
    else:
        start = 0
        total_pages = 1
        page = 1
        end = total-1

        if total > MAX_FLEXI_ROWS:
            return HttpResponseBadRequest("Too many rows! Please try loading a smaller number.")

    for object in objects[start:end]:
        event_times = timeSelections(object.gpstime)
        created_times = timeSelections(object.created)
        if object.search:
            search_name = object.search.name
        else:
            search_name = ''

        display_far = scientific(object.far)
        if object.far and is_external(request.user):
            if object.far < settings.VOEVENT_FAR_FLOOR:
                display_far = "< %s" % scientific(settings.VOEVENT_FAR_FLOOR)

        cell_values = [ '<a href="%s">%s</a>' %
                            (django_reverse("view", args=[object.graceid()]), object.graceid()),
                         #Labels
                        " ".join(["""<span onmouseover="tooltip.show(tooltiptext('%s', '%s', '%s'));" onmouseout="tooltip.hide();"  style="color: %s"> %s </span>""" % (label.label.name, label.creator.username, label.created, label.label.defaultColor, label.label.name)
                                for label in object.labelling_set.all()]),
                        object.group.name,
                        object.pipeline.name,
                        search_name,

                        event_times.get('gps',""),
                        #event_times['utc'],

                        object.instruments,

                        #scientific(display_far),
                        display_far,

                        '<a href="%s">Data</a>' % object.weburl(),

                        #created_times['gps'],
                        created_times.get('utc',""),

                        "%s %s" % (object.submitter.first_name, object.submitter.last_name)

                      ]

        if get_neighbors:
            # Links to neighbors
            cell_values.insert(2, ', '.join([ '<a href="%s">%s</a>' %
                (django_reverse("view", args=[n.graceid()]), n.graceid()) for n in object.neighbors()]))

        rows.append(
            { 'id' : object.id,
              'cell': cell_values,
            }
        )
    d = {
            'page': page,
            'total': total_pages,
            'records': total,
            'rows': rows,
        }
    try:
        msg = json.dumps(d)
    except Exception:
        # XXX Not right not right not right.
        msg = "{}"
    response['Content-length'] = len(msg)
    response.write(msg)

    #query = request.POST['query']

    return response

def get_file(event, filename="event.log"):
    logfilename = os.path.join(event.datadir(), filename)
    contents = ""
    try:
        lines = open(logfilename, "r").readlines()
        contents = "<br/>".join([ escape(line) for line in lines])
        contents = mark_safe(urlize(contents))
    except Exception:
        contents = None
    return contents

#--------------------------------------------------------------
# This utility should raise an exception if the FAR range query 
# upper limit is below the VOEvent FAR floor. This should be 
# applied to the agglomerated Q object resulting from parsing a
# search query for external (non-LVC) users. The q object can 
# be full of all sorts of things. We just traverse the whole 
# thing looking for things like # Q(far__lte=#), etc., and then
# check the upper limit of the search range.
#--------------------------------------------------------------
class BadFARRange(Exception):
    pass

def check_query_far_range(q, floor=settings.VOEVENT_FAR_FLOOR):
    for c in q.children:
        # If the child is another Q object, we send it through 
        # the same function.
        if isinstance(c, Q):
            check_query_far_range(c, floor)
        # If, on the other hand, we've made all the way down to
        # a 'leaf' of the tree, we'll make sure that it's not a
        # bad FAR range query.
        elif isinstance(c, tuple):
            if c[0] in ('far__lt', 'far__lte') and c[1] < floor:
                raise BadFARRange
            elif c[0] == 'far__range' and c[1][1] < floor:
                raise BadFARRange

#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------
# Get a serialized list of recent events for use with the d3 visualization of 
# recent events.
#---------------------------------------------------------------------------------------
#---------------------------------------------------------------------------------------

def get_recent_events_string(request):
    #t_high = datetime(2016, 1, 12, 16, 0) # End of O1
    #t_high = pytz.utc.localize(t_high)
    t_high = timezone.now()
    dt = timedelta(days=7)
    t_low = t_high - dt
    # XXX Warning: If you open this up to non-internal users, you need
    # to filter these events.
    events = Event.objects.filter(created__range=(t_low, t_high))

    # Explicitly filter out MDC and Test events
    try:
        mdc = Search.objects.get(name='MDC')
        events = events.exclude(search=mdc)
    except:
        pass

    try:
        test = Group.objects.get(name='Test')
        events = events.exclude(group=test)
    except:
        pass

    if events.count() == 0:
        return ''

    event_list = [ {'pipeline': e.pipeline.name,
                    'graceid': e.graceid(),
                    'created': e.created.isoformat() } for e in events ]

    return json.dumps(event_list)

