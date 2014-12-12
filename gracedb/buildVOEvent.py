
# Taken from VOEventLib example code, which is:
# Copyright 2010 Roy D. Williams
# then modified
"""
buildVOEvent: Creates a complex VOEvent with tables
See the VOEvent specification for details
http://www.ivoa.net/Documents/latest/VOEvent.html
"""

from VOEventLib.VOEvent import VOEvent, Who, Author, Param, How, Why, What, Group
from VOEventLib.Vutil import makeWhereWhen, stringVOEvent

# XXX ER2.utils.  utils is in project directory.  ugh.
from utils import gpsToUtc
from datetime import datetime
from django.conf import settings
from django.core.urlresolvers import reverse
from models import CoincInspiralEvent, MultiBurstEvent

import os

class VOEventBuilderException(Exception):
    pass

def get_url(request, graceid, view_name, file_name=None):
    args = [graceid,]
    if file_name:
        args.append(file_name)
    rel_url = reverse(view_name, args=args)
    return request.build_absolute_uri(rel_url)

#
# Types of VOEvents:
#   preliminary:    no skymap
#   initial:        BAYESTAR skymap
#   update:         PE skymap
#
#   If the type of skymap doesn't exist, then we need to fail in such
#   a way as to get the attention of the requestor. We don't want to
#   forward a bad VOEvent with now skymap.
#
#   For each skymap, we demand that there be at least one of: 1) an image file,
#   2) a data file. The image (data) file name should conform to the pattern:
#   stem + '.png' ('.fits.gz').
#   This is obviously very fragile. A 'Skymap' data model would help this 
#   situation considerably, especially if additional skymap types arise.
#
SKYMAP_INFO = {
    'initial' : {
        'name' : 'BAYESTAR',
        'stem' : 'skymap',
    },
    'update'  : {
        'name' : 'LALINFERENCE_MCMC',
        'stem' : 'binned_posterior_samples',
    }
}

VOEVENT_TYPES = ['preliminary', 'initial', 'update',]

def buildVOEvent(event, request=None, description=None, role=None, 
    voevent_type='preliminary'):

    if not event.far:
        raise VOEventBuilderException("Cannot build a VOEvent because event has no FAR.")

    if not event.gpstime:
        raise VOEventBuilderException("Cannot build a VOEvent because event has no gpstime.")

    if not voevent_type in VOEVENT_TYPES:
        # Do something real here XXX
        raise VOEventBuilderException("voevent_type must be preliminary, initial, or update")

    objid = event.graceid()

    ############ VOEvent header ############################
    v = VOEvent(version="2.0")
    v.set_ivorn(settings.SKYALERT_IVORN_PATTERN % objid)
    v.set_role(role or settings.SKYALERT_ROLE)
    v.set_Description(description or settings.SKYALERT_DESCRIPTION)

    ############ Who ############################
    w = Who()
    a = Author()
    a.add_contactName("LIGO Scientific Collaboration and Virgo Collaboration")
    #a.add_contactEmail("postmaster@ligo.org")
    w.set_Author(a)
    w.set_Date(datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S"))
    v.set_Who(w)

    ############ Why ############################
    y = Why()
    y.add_Description("Candidate gravitational wave event identified by low-latency analysis")
    v.set_Why(y)

    ############ How ############################

    h = How()
    instruments = event.instruments.split(',')
    if 'H1' in instruments:
        h.add_Description("H1: LIGO Hanford 4 km gravitational wave detector")
    if 'L1' in instruments:
        h.add_Description("L1: LIGO Livingston 4 km gravitational wave detector")
    if 'V1' in instruments:
        h.add_Description("V1: Virgo 3 km gravitational wave detector")
    v.set_How(h)

    ############ What ############################
    w = What()

    # UCD = Unified Content Descriptors
    # http://monet.uni-sw.gwdg.de/twiki/bin/view/VOEvent/UnifiedContentDescriptors
    # OR --   (from VOTable document, [21] below)
    # http://www.ivoa.net/twiki/bin/view/IVOA/IvoaUCD
    # http://cds.u-strasbg.fr/doc/UCD.htx
    #
    # which somehow gets you to: http://www.ivoa.net/Documents/REC/UCD/UCDlist-20070402.html
    # where you might find some actual information.

    # Unit / Section 4.3 of [21] which relies on [25]
    # [21] http://www.ivoa.net/Documents/latest/VOT.html
    # [25] http://vizier.u-strasbg.fr/doc/catstd-3.2.htx
    #
    # basically, a string that makes sense to humans about what units a value is. eg. "m/s"

    # The GraceID
    w.add_Param(Param(name="GraceID", 
        dataType="string",
        ucd="meta.id", 
        value=objid, 
        Description=["Identifier in GraceDB"]))

    # The alert type
    w.add_Param(Param(name="AlertType",
        dataType="string",
        ucd="meta.version",
        unit="",
        value = voevent_type.capitalize(),
        Description=["VOEvent alert type"]))

    # False alarm rate
    w.add_Param(Param(name="FAR", 
        dataType="float", 
        ucd="arith.rate;stat.falsealarm", 
        unit="Hz", 
        value=float(event.far), 
        Description=["False alarm rate for GW candidates with this strength or greater"]))

    # Shib protected event page
    w.add_Param(Param(name="EventPage",
        ucd="meta.ref.url",
        value=get_url(request, objid, "view2"),
        Description=["Web page for evolving status of this candidate event"]))

    # Pipeline
    w.add_Param(Param(name="Pipeline", 
        dataType="string", 
        ucd="meta.code",
        unit="",
        value=event.pipeline.name,
        Description=["Low-latency data analysis pipeline"]))

    # Search
    if event.search:
        w.add_Param(Param(name="Search", 
            ucd="meta.code",
            unit="",
            dataType="string", 
            value=event.search.name,
            Description=["Specific low-latency search"]))

    if voevent_type in ["initial", "update"]:
        # Skymaps. Create group and set particular fits and image file names
        g = Group('GW_SKYMAP', SKYMAP_INFO[voevent_type]['name'])
        fits_name = SKYMAP_INFO[voevent_type]['stem'] + '.fits.gz'
        img_name  = SKYMAP_INFO[voevent_type]['stem'] + '.png'

        # Check for the existence of the files.
        for filename in [fits_name, img_name]:
            filepath = os.path.join(event.datadir(), filename)
            if not os.path.exists(filepath):
                raise VOEventBuilderException("Skymap file %s not found" % filename) 

        # shib urls.
        shib_fits_skymap_url = get_url(request, objid, "file", fits_name)
        shib_png_skymap_url  = get_url(request, objid, "file", img_name)

        # x509 urls. Hafta specify the api namespace.
        x509_fits_skymap_url = get_url(request, objid, "x509:files", fits_name)
        x509_png_skymap_url  = get_url(request, objid, "x509:files", img_name)

        # Add parameters to the skymap group
        g.add_Param(Param(name="skymap_png_x509", 
            dataType="string",
            ucd="meta.ref.url", 
            unit="",
            value=x509_png_skymap_url,
            Description=["Sky Map image X509 protected"]))

        g.add_Param(Param(name="skymap_fits_x509", 
            dataType="string",
            ucd="meta.ref.url", 
            unit="",
            value=x509_fits_skymap_url,
            Description=["Sky Map FITS X509 protected"]))

        g.add_Param(Param(name="skymap_png_shib", 
            dataType="string",
            ucd="meta.ref.url", 
            unit="",
            value=shib_png_skymap_url,
            Description=["Sky Map image Shibboleth protected"]))

        g.add_Param(Param(name="skymap_fits_shib", 
            dataType="string",
            ucd="meta.ref.url", 
            unit="",
            value=shib_fits_skymap_url,
            Description=["Sky Map FITS Shibboleth protected"]))

        w.add_Group(g)

    # Analysis specific attributes
    if isinstance(event,CoincInspiralEvent):
        # get mchirp and mass
        mchirp = float(event.mchirp)
        mass = float(event.mass)
        # calculate eta = (mchirp/total_mass)**(5/3)
        eta = pow((mchirp/mass),5.0/3.0)
        w.add_Param(Param(name="ChirpMass", 
            dataType="float", 
            ucd="phys.mass", 
            unit="solar mass",
            value=mchirp,
            Description=["Estimated CBC chirp mass"]))

        w.add_Param(Param(name="Eta", 
            dataType="float", 
            ucd="phys.mass;arith.factor", 
            unit="",
            value=eta,
            Description=["Estimated ratio of reduced mass to total mass"]))

        # build up MaxDistance. event.singleinspiral_set.all()?
        # Each detector calculates an effective distance assuming the inspiral is 
        # optimally oriented. It is the maximum distance at which a source of the 
        # given parameters would've been seen by that particular detector. To get
        # an effective 'maximum distance', we just find the minumum over detectors
        max_distance = float('inf')
        for obj in event.singleinspiral_set.all():
            if obj.eff_distance < max_distance:
                max_distance = obj.eff_distance
        if max_distance < float('inf'):
            w.add_Param(Param(name="MaxDistance", 
                dataType="float", 
                ucd="pos.distance", 
                unit="Mpc",
                value=max_distance, 
                Description=["Estimated maximum distance for CBC event"]))
            
    elif isinstance(event,MultiBurstEvent):
        w.add_Param(Param(name="CentralFreq", 
            dataType="float", 
            ucd="gw.frequency", 
            unit="Hz", 
            value=float(event.central_freq),
            Description=["Central frequency of GW burst signal"]))
        w.add_Param(Param(name="Duration", 
            dataType="float", 
            ucd="time.duration", 
            unit="s", 
            value=float(event.duration),
            Description=["Measured duration of GW burst signal"]))

        # XXX Calculate the fluence. Unfortunately, this requires parsing the trigger.txt
        # file for hrss values.  These should probably be pulled into the database.
        # But there is no consensus on whether hrss or fluence is meaningful. So I will
        # put off changing the schema for now.
        try:
            # Go find the data file.
            log = event.eventlog_set.filter(comment__startswith="Original Data").all()[0]
            filename = log.filename
            filepath = os.path.join(event.datadir(),filename)
            if os.path.isfile(filepath):
                datafile = open(filepath,"r")
            else:
                raise Exception("No file found.")
            # Now parse the datafile.
            # The line we want looks like:
            # hrss: 1.752741e-23 2.101590e-23 6.418900e-23
            for line in datafile:
                if line.startswith('hrss:'):
                    hrss_values = [float(hrss) for hrss in line.split()[1:]]
            max_hrss = max(hrss_values)
            # From Min-A Cho: fluence = pi*(c**3)*(freq**2)*(hrss_max**2)*(10**3)/(4*G)
            # Note that hrss here actually has units of s^(-1/2)
            pi = 3.14152
            c = 2.99792E10
            G = 6.674E-8
            fluence = pi * pow(c,3) * pow(event.central_freq,2) * 1000.0
            fluence = fluence * pow(max_hrss,2)
            fluence = fluence / (4.0*G)

            w.add_Param(Param(name="Fluence", 
                dataType="float", 
                ucd="gw.fluence", 
                unit="erg/cm^2", 
                value=fluence,
                Description=["Estimated fluence of GW burst signal"]))
        except Exception: 
            pass
    else:
        pass

    v.set_What(w)

    ############ Wherewhen ############################
    wwd = {'observatory':     'LIGO Virgo',
           'coord_system':    'UTC-FK5-GEO',
           # XXX time format
           'time':            str(gpsToUtc(event.gpstime).isoformat())[:-6],   #'1918-11-11T11:11:11',
           #'timeError':       1.0,
           'longitude':       0.0,
           'latitude':        0.0,
           'positionalError': 180.0,
    }

    ww = makeWhereWhen(wwd)
    if ww: v.set_WhereWhen(ww)

    ############ Citation ############################
    #c = Citations()
    #c.add_EventIVORN(EventIVORN(cite="followup", valueOf_="ivo:silly/billy#89474"))
    #c.add_EventIVORN(EventIVORN(cite="followup", valueOf_="ivo:silly/billy#89475"))
    #v.set_Citations(c)

    ############ output the event ############################
    xml = stringVOEvent(v) 
        #schemaURL = "http://www.ivoa.net/xml/VOEvent/VOEvent-v2.0.xsd")
    return xml

def submitToSkyalert(event, validate_only=False):
    ## Python stub code for validating and authoring VOEvents to Skyalert
    import urllib
    dict = {}

    # the server that will handle the submit request
    url = "http://skyalert.org/submit/"
    url = "https://betelgeuse.ligo.caltech.edu:8000/submit/"
    url = "http://betelgeuse.ligo.caltech.edu/submit/"

    # choose 'dryrun' for validation and 'author' for authoring
    dict['checker'] = 'dryrun'

    # for command line, we want plain text output, not HTML
    dict['plainResponse'] = 'on'

    if not validate_only:
        # uncomment these for authoring
        dict['checker'] = 'author'

        # Skyalert username and password
        dict['username'] = 'system'
        dict['password'] = 'OPV537'

        # This is the short name for the stream, must match credentials and event!
        dict['streamName'] = 'LIGO'

        # Should alerts be run once the event is ingested?
        dict['doRules'] = 'on'

    dict['xmlText'] = buildVOEvent(event)
    params = urllib.urlencode(dict)
    f = urllib.urlopen(url, params)
    result = f.read()
    return result


