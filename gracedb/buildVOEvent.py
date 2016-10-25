
# Taken from VOEventLib example code, which is:
# Copyright 2010 Roy D. Williams
# then modified
"""
buildVOEvent: Creates a complex VOEvent with tables
See the VOEvent specification for details
http://www.ivoa.net/Documents/latest/VOEvent.html
"""

from VOEventLib.VOEvent import VOEvent, Who, Author, Param, How, What, Group
from VOEventLib.VOEvent import Citations, EventIVORN
#from VOEventLib.VOEvent import Why
#from VOEventLib.Vutil import makeWhereWhen, stringVOEvent
from VOEventLib.Vutil import stringVOEvent

from VOEventLib.VOEvent import AstroCoords, AstroCoordSystem
from VOEventLib.VOEvent import ObservationLocation, ObservatoryLocation
from VOEventLib.VOEvent import ObsDataLocation, WhereWhen
from VOEventLib.VOEvent import Time, TimeInstant

# XXX ER2.utils.  utils is in project directory.  ugh.
from utils import gpsToUtc
from django.utils import timezone
from django.conf import settings
from django.core.urlresolvers import reverse
from models import CoincInspiralEvent, MultiBurstEvent
from models import VOEvent as GraceDBVOEvent
from models import LalInferenceBurstEvent

import os

class VOEventBuilderException(Exception):
    pass

def get_url(request, graceid, view_name, file_name=None):
    args = [graceid,]
    if file_name:
        args.append(file_name)
    rel_url = reverse(view_name, args=args)
    return request.build_absolute_uri(rel_url)

VOEVENT_TYPE_DICT = dict(GraceDBVOEvent.VOEVENT_TYPE_CHOICES)

def get_voevent_type(short_name):
    for t in GraceDBVOEvent.VOEVENT_TYPE_CHOICES:
        if short_name in t:
            return t[1]
    return None

def buildVOEvent(event, serial_number, voevent_type, request=None, skymap_filename=None,
                 skymap_type=None, skymap_image_filename=None, internal=1, vetted=0,
                 open_alert=0, hardware_inj=0, CoincComment=0, ProbHasNS=None,
                 ProbHasRemnant=None):

# XXX Branson commenting out. Reed's MDC events do not have FAR for some reason.
#    if not event.far:
#        raise VOEventBuilderException("Cannot build a VOEvent because event has no FAR.")

    if not event.gpstime:
        raise VOEventBuilderException("Cannot build a VOEvent because event has no gpstime.")

    if not voevent_type in VOEVENT_TYPE_DICT.keys():
        raise VOEventBuilderException("voevent_type must be preliminary, initial, update, or retraction")

    # Let's convert that voevent_type to something nicer looking
    voevent_type = VOEVENT_TYPE_DICT[voevent_type]

    objid = event.graceid()

    # Now build the IVORN. 
    # XXX This will have the string '-Retraction' appended if it is a retraction,
    # and the voevent_type will refer to the type of the *previous* voevent.
    # This is highly objectionable.
    type_string = voevent_type.capitalize()
    if voevent_type == 'retraction':
        try:
            last_voevent = event.voevent_set.order_by('-N')[1] 
            type_string = get_voevent_type(last_voevent.voevent_type).capitalize()
            type_string += '-Retraction'
        except:
            # XXX Somehow failed to get the previous VOEvent. This is a bad situation.
            # But we can't just error out, because sending out the retraction is pretty
            # important. 
            type_string = 'Preliminary-Retraction'

    event_id = "%s-%d-%s" % (objid, serial_number, type_string)
    ivorn = settings.SKYALERT_IVORN_PATTERN % event_id

    ############ VOEvent header ############################
    v = VOEvent(version="2.0")
    v.set_ivorn(ivorn)

    if event.search and event.search.name == 'MDC':
        v.set_role("test")
    elif event.group.name == 'Test':
        v.set_role("test")
    else:
        v.set_role("observation")
    if voevent_type != 'retraction':
        v.set_Description(settings.SKYALERT_DESCRIPTION)

    ############ Who ############################
    w = Who()
    a = Author()
    a.add_contactName("LIGO Scientific Collaboration and Virgo Collaboration")
    #a.add_contactEmail("postmaster@ligo.org")
    w.set_Author(a)
    w.set_Date(timezone.now().strftime("%Y-%m-%dT%H:%M:%S"))
    v.set_Who(w)

    ############ Why ############################
    # Moving this information into the 'How' section.
    #if voevent_type != 'retraction':
    #    y = Why()
    #    y.add_Description("Candidate gravitational wave event identified by low-latency analysis")
    #    v.set_Why(y)

    ############ How ############################

    if voevent_type != 'retraction':
        h = How()
        h.add_Description("Candidate gravitational wave event identified by low-latency analysis")
        instruments = event.instruments.split(',')
        if 'H1' in instruments:
            h.add_Description("H1: LIGO Hanford 4 km gravitational wave detector")
        if 'L1' in instruments:
            h.add_Description("L1: LIGO Livingston 4 km gravitational wave detector")
        if 'V1' in instruments:
            h.add_Description("V1: Virgo 3 km gravitational wave detector")
        if CoincComment==1:
            h.add_Description("A gravitational wave trigger identified a possible counterpart GRB")
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

    # Whether the alert is internal or not
    w.add_Param(Param(name="internal", value=internal, dataType="int",
        Description=['Indicates whether this event should be distributed to LSC/Virgo members only']))
    
    # The serial number
    w.add_Param(Param(name="Pkt_Ser_Num", value=serial_number))

    # The GraceID
    w.add_Param(Param(name="GraceID", 
        dataType="string",
        ucd="meta.id", 
        value=objid, 
        Description=["Identifier in GraceDB"]))

    # XXX if voevent_type == 'retraction' the AlertType will be the type of the
    # last VOEvent sent out. This is highly objectionable.
    alert_type = voevent_type

    if voevent_type == 'retraction':
        try:
            last_voevent = event.voevent_set.order_by('-N')[1] 
            alert_type = get_voevent_type(last_voevent.voevent_type)
        except:
            # XXX We have failed to obtain the last voevent for some reason, so 
            # we don't know what the alert type should be. Let's just set it to
            # preliminary, since we need to try not to error out of sending the
            # retraction
            alert_type = 'preliminary'

    w.add_Param(Param(name="AlertType",
        dataType="string",
        ucd="meta.version",
        unit="",
        value = alert_type.capitalize(),
        Description=["VOEvent alert type"]))

    w.add_Param(Param(name="Retraction",
        dataType="string",
        ucd="meta.code",
        unit="",
        value= "true" if voevent_type == 'retraction' else "false",
        Description=["Set to true if the event is retracted."]))

    # Shib protected event page
    # Whether the event is a hardware injection or not
    w.add_Param(Param(name="HardwareInj",
        dataType="int",
        ucd="meta.number",
        unit="",
        value=hardware_inj,
        Description=['Indicates that this event is a hardware injection if 1, no if 0']))

    w.add_Param(Param(name="Vetted",
        dataType="int",
        ucd = "meta.number",
        unit="",
        value=vetted,
        Description=['Indicates whether this candidate has undergone basic vetting by humans']))

    w.add_Param(Param(name="OpenAlert",
        dataType="int",
        ucd="meta.number",
        unit="",
        value=open_alert,
        Description=['Indicates that this event is an open alert if 1, no if 0']))

    w.add_Param(Param(name="EventPage",
        ucd="meta.ref.url",
        value=get_url(request, objid, "view2"),
        Description=["Web page for evolving status of this candidate event"]))

    if voevent_type != 'retraction':
        # Instruments
        w.add_Param(Param(name="Instruments", 
            dataType="string",
            ucd="meta.code", 
            value=event.instruments, 
            Description=["List of instruments used in analysis to identify this event"]))

        # False alarm rate
        if event.far:
            w.add_Param(Param(name="FAR", 
                dataType="float", 
                ucd="arith.rate;stat.falsealarm", 
                unit="Hz", 
                value=float(max(event.far, settings.VOEVENT_FAR_FLOOR)), 
                Description=["False alarm rate for GW candidates with this strength or greater"]))

        # Group
        w.add_Param(Param(name="Group", 
            dataType="string", 
            ucd="meta.code",
            unit="",
            value=event.group.name,
            Description=["Data analysis working group"]))

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

    # initial and update VOEvents must have a skymap.
    # new feature (10/24/5/2016): preliminary VOEvents can have a skymap,
    # but they don't have to.
    if (voevent_type in ["initial", "update"] or 
       (voevent_type == "preliminary" and skymap_filename != None)):
        if not skymap_filename:
            raise VOEventBuilderException("Skymap filename not provided.")

        fits_name = skymap_filename
        fits_path = os.path.join(event.datadir(), fits_name)
        if not os.path.exists(fits_path):
            raise VOEventBuilderException("Skymap file does not exist: %s" % skymap_filename)

        # Let's try to get an image.
        img_name = skymap_image_filename
        if not img_name:
            stem = '.'.join(fits_name.split('.')[:-1])
            img_name = stem + '.png'
            img_path = os.path.join(event.datadir(), img_name)
            if not os.path.exists(img_path):
                img_name = None

        if not skymap_type:
            raise VOEventBuilderException("Skymap type must be provided.")

        # Skymaps. Create group and set particular fits and image file names
        g = Group('GW_SKYMAP', skymap_type)

        # shib urls.
        shib_fits_skymap_url = get_url(request, objid, "file", fits_name)
        if img_name:
            shib_png_skymap_url  = get_url(request, objid, "file", img_name)

        # x509 urls. Hafta specify the api namespace.
        x509_fits_skymap_url = get_url(request, objid, "x509:files", fits_name)
        if img_name:
            x509_png_skymap_url  = get_url(request, objid, "x509:files", img_name)

        # basic urls. Hafta specify the api namespace.
        basic_fits_skymap_url = get_url(request, objid, "basic:files", fits_name)
        if img_name:
            basic_png_skymap_url  = get_url(request, objid, "basic:files", img_name)
        

        # Add parameters to the skymap group
        g.add_Param(Param(name="skymap_fits_shib", 
            dataType="string",
            ucd="meta.ref.url", 
            unit="",
            value=shib_fits_skymap_url,
            Description=["Sky Map FITS Shibboleth protected"]))
        g.add_Param(Param(name="skymap_fits_x509", 
            dataType="string",
            ucd="meta.ref.url", 
            unit="",
            value=x509_fits_skymap_url,
            Description=["Sky Map FITS X509 protected"]))
        g.add_Param(Param(name="skymap_fits_basic", 
            dataType="string",
            ucd="meta.ref.url", 
            unit="",
            value=basic_fits_skymap_url,
            Description=["Sky Map FITS basic auth protected"]))

        if img_name:
            g.add_Param(Param(name="skymap_png_shib", 
                dataType="string",
                ucd="meta.ref.url", 
                unit="",
                value=shib_png_skymap_url,
                Description=["Sky Map image Shibboleth protected"]))
            g.add_Param(Param(name="skymap_png_x509", 
                dataType="string",
                ucd="meta.ref.url", 
                unit="",
                value=x509_png_skymap_url,
                Description=["Sky Map image X509 protected"]))
            g.add_Param(Param(name="skymap_png_basic", 
                dataType="string",
                ucd="meta.ref.url", 
                unit="",
                value=basic_png_skymap_url,
                Description=["Sky Map image basic auth protected"]))

        w.add_Group(g)

    # Analysis specific attributes
    if voevent_type != 'retraction':
        if isinstance(event,CoincInspiralEvent) and voevent_type != 'retraction':
            # get mchirp and mass
            mchirp = float(event.mchirp)
            mass = float(event.mass)
            # calculate eta = (mchirp/total_mass)**(5/3)
            eta = pow((mchirp/mass),5.0/3.0)

            # EM-Bright mass classifier information for CBC event candidates
            if ProbHasNS!=None:
                w.add_Param(Param(name="ProbHasNS",
                    dataType="float",
                    ucd="stat.probability",
                    unit="",
                    value=ProbHasNS,
                    Description=["Probability that at least one object in the binary is less than 3 solar masses"]))

            if ProbHasRemnant!=None:
                w.add_Param(Param(name="ProbHasRemnant",
                    dataType="float",
                    ucd="stat.probability",
                    unit="",
                    value=ProbHasRemnant,
                    Description=["Probability that there is matter in the surroundings of the central object"]))

# XXX
#            w.add_Param(Param(name="ChirpMass", 
#                dataType="float", 
#                ucd="phys.mass", 
#                unit="solar mass",
#                value=mchirp,
#                Description=["Estimated CBC chirp mass"]))

# XXX 
#            w.add_Param(Param(name="Eta", 
#                dataType="float", 
#                ucd="phys.mass;arith.factor", 
#                unit="",
#                value=eta,
#                Description=["Estimated ratio of reduced mass to total mass"]))

            # build up MaxDistance. event.singleinspiral_set.all()?
            # Each detector calculates an effective distance assuming the inspiral is 
            # optimally oriented. It is the maximum distance at which a source of the 
            # given parameters would've been seen by that particular detector. To get
            # an effective 'maximum distance', we just find the minumum over detectors
            max_distance = float('inf')
            for obj in event.singleinspiral_set.all():
                if obj.eff_distance < max_distance:
                    max_distance = obj.eff_distance
#            if max_distance < float('inf'):
#                w.add_Param(Param(name="MaxDistance", 
#                    dataType="float", 
#                    ucd="pos.distance", 
#                    unit="Mpc",
#                    value=max_distance, 
#                    Description=["Estimated maximum distance for CBC event"]))
                
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
                fluence = pi * pow(c,3) * pow(event.central_freq,2) 
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
        elif isinstance(event,LalInferenceBurstEvent):
            w.add_Param(Param(name="frequency", 
                dataType="float", 
                ucd="gw.frequency", 
                unit="Hz", 
                value=float(event.frequency),
                Description=["Frequency of GW burst signal"]))

            # Calculate the fluence. 
            # From Min-A Cho: fluence = pi*(c**3)*(freq**2)*(hrss_max**2)*(10**3)/(4*G)
            # Note that hrss here actually has units of s^(-1/2)
            # XXX obviously need to refactor here.
            try:
                pi = 3.14152
                c = 2.99792E10
                G = 6.674E-8
                fluence = pi * pow(c,3) * pow(event.frequency,2) 
                fluence = fluence * pow(event.hrss,2)
                fluence = fluence / (4.0*G)

                w.add_Param(Param(name="Fluence", 
                    dataType="float", 
                    ucd="gw.fluence", 
                    unit="erg/cm^2", 
                    value=fluence,
                    Description=["Estimated fluence of GW burst signal"]))
            except:
                pass
        else:
            pass

    v.set_What(w)

    ############ Wherewhen ############################
# The old way of making the WhereWhen section led to a pointless position
# location.
#        wwd = {'observatory':     'LIGO Virgo',
#               'coord_system':    'UTC-FK5-GEO',
#               # XXX time format
#               'time':            str(gpsToUtc(event.gpstime).isoformat())[:-6],   #'1918-11-11T11:11:11',
#               #'timeError':       1.0,
#               'longitude':       0.0,
#               'latitude':        0.0,
#               'positionalError': 180.0,
#        }
#
#        ww = makeWhereWhen(wwd)
#        if ww: v.set_WhereWhen(ww)

    coord_system_id = 'UTC-FK5-GEO'
    event_time = str(gpsToUtc(event.gpstime).isoformat())[:-6]
    observatory_id = 'LIGO Virgo'
    ac =  AstroCoords(coord_system_id=coord_system_id)
    acs = AstroCoordSystem(id=coord_system_id)
    ac.set_Time(Time(TimeInstant = TimeInstant(event_time)))

    onl = ObservationLocation(acs, ac)
    oyl = ObservatoryLocation(id=observatory_id)
    odl = ObsDataLocation(oyl, onl)
    ww = WhereWhen()
    ww.set_ObsDataLocation(odl)
    v.set_WhereWhen(ww)

    ############ Citation ############################
    if event.voevent_set.count()>1:
        c = Citations()
        for ve in event.voevent_set.all():
            # Oh, actually we need to exclude *this* voevent.
            if serial_number == ve.N:
                continue
            if voevent_type == 'initial':
                ei = EventIVORN('supersedes', ve.ivorn)
                c.set_Description('Initial localization is now available')
            elif voevent_type == 'update':            
                ei = EventIVORN('supersedes', ve.ivorn)
                c.set_Description('Updated localization is now available')
            elif voevent_type == 'retraction':
                ei = EventIVORN('retraction', ve.ivorn)
                c.set_Description('Determined to not be a viable GW event candidate')
            elif voevent_type == 'preliminary':
                # For cases when an additional preliminary VOEvent is sent
                # in order to add a preliminary skymap.
                ei = EventIVORN('supersedes', ve.ivorn)
                c.set_Description('Initial localization is now available (preliminary)')
            c.add_EventIVORN(ei)

        v.set_Citations(c)

    ############ output the event ############################
    xml = stringVOEvent(v) 
        #schemaURL = "http://www.ivoa.net/xml/VOEvent/VOEvent-v2.0.xsd")
    return xml, ivorn

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


