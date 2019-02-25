
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
from VOEventLib.Vutil import stringVOEvent

from VOEventLib.VOEvent import AstroCoords, AstroCoordSystem
from VOEventLib.VOEvent import ObservationLocation, ObservatoryLocation
from VOEventLib.VOEvent import ObsDataLocation, WhereWhen
from VOEventLib.VOEvent import Time, TimeInstant

from core.urls import build_absolute_uri
from core.time_utils import gpsToUtc
from django.conf import settings
from django.urls import reverse
from django.utils import timezone
from django.db.models import Min
from events.models import CoincInspiralEvent, MultiBurstEvent, \
    LalInferenceBurstEvent
from .models import VOEvent as GraceDBVOEvent

import os
import logging
logger = logging.getLogger(__name__)

VOEVENT_TYPE_DICT = dict(GraceDBVOEvent.VOEVENT_TYPE_CHOICES)

class VOEventBuilderException(Exception):
    pass

# Used to create the Packet_Type parameter block
PACKET_TYPES = {
    GraceDBVOEvent.VOEVENT_TYPE_PRELIMINARY: (150, 'LVC_PRELIMINARY'),
    GraceDBVOEvent.VOEVENT_TYPE_INITIAL: (151, 'LVC_INITIAL'),
    GraceDBVOEvent.VOEVENT_TYPE_UPDATE: (152, 'LVC_UPDATE'),
    GraceDBVOEvent.VOEVENT_TYPE_RETRACTION: (164, 'LVC_RETRACTION'),
}

def get_voevent_type(short_name):
    for t in GraceDBVOEvent.VOEVENT_TYPE_CHOICES:
        if short_name in t:
            return t[1]
    return None


def construct_voevent_file(superevent, voevent, request=None,
    skymap_filename=None, skymap_type=None, internal=True, open_alert=False,
    hardware_inj=False, CoincComment=False, ProbHasNS=None,
    ProbHasRemnant=None, BNS=None, NSBH=None, BBH=None, Terrestrial=None,
    MassGap=None):

    # Set preferred_event as event to be used in most of this
    event = superevent.preferred_event
    # Get the event subclass (CoincInspiralEvent, MultiBurstEvent, etc.) and
    # set that as the event
    subclass_fields = [f for f in event.__class__._meta.get_fields()
        if (f.one_to_one and f.auto_created and not f.concrete and
            event.__class__ in f.related_model.__bases__)]
    for f in subclass_fields:
        if hasattr(event, f.name):
            event = getattr(event, f.name)
            break

    # Let's convert that voevent_type to something nicer looking
    voevent_type = VOEVENT_TYPE_DICT[voevent.voevent_type]

    # Now build the IVORN. 
    type_string = voevent_type.capitalize()
    voevent_id = '{s_id}-{N}-{type_str}'.format(type_str=type_string,
        s_id=superevent.default_superevent_id, N=voevent.N)
    ivorn = settings.IVORN_PREFIX + voevent_id

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
        if CoincComment:
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

    # Add Packet_Type for GCNs
    w.add_Param(Param(name="Packet_Type",
        value=PACKET_TYPES[voevent.voevent_type][0], dataType="int",
        Description=[("The Notice Type number is assigned/used within GCN, eg "
        "type={typenum} is an {typedesc} notice").format(
        typenum=PACKET_TYPES[voevent.voevent_type][0],
        typedesc=PACKET_TYPES[voevent.voevent_type][1])]))

    # Whether the alert is internal or not
    w.add_Param(Param(name="internal", value=int(internal), dataType="int",
        Description=['Indicates whether this event should be distributed to LSC/Virgo members only']))
    
    # The serial number
    w.add_Param(Param(name="Pkt_Ser_Num", value=voevent.N,
        Description=["A number that increments by 1 each time a new revision "
        "is issued for this event"]))

    # The superevent ID
    w.add_Param(Param(name="GraceID",
        dataType="string",
        ucd="meta.id", 
        value=superevent.default_superevent_id,
        Description=["Identifier in GraceDB"]))

    # Alert type parameter
    w.add_Param(Param(name="AlertType",
        dataType="string",
        ucd="meta.version",
        value = voevent_type.capitalize(),
        Description=["VOEvent alert type"]))

    # Whether the event is a hardware injection or not
    w.add_Param(Param(name="HardwareInj",
        dataType="int",
        ucd="meta.number",
        value=int(hardware_inj),
        Description=['Indicates that this event is a hardware injection if 1, no if 0']))

    w.add_Param(Param(name="OpenAlert",
        dataType="int",
        ucd="meta.number",
        value=int(open_alert),
        Description=['Indicates that this event is an open alert if 1, no if 0']))

    # Superevent page
    w.add_Param(Param(name="EventPage",
        ucd="meta.ref.url",
        value=build_absolute_uri(reverse("superevents:view",
            args=[superevent.default_superevent_id]), request),
        Description=["Web page for evolving status of this GW candidate"]))

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
            value=event.group.name,
            Description=["Data analysis working group"]))

        # Pipeline
        w.add_Param(Param(name="Pipeline", 
            dataType="string", 
            ucd="meta.code",
            value=event.pipeline.name,
            Description=["Low-latency data analysis pipeline"]))

        # Search
        if event.search:
            w.add_Param(Param(name="Search", 
                ucd="meta.code",
                dataType="string", 
                value=event.search.name,
                Description=["Specific low-latency search"]))

    # initial and update VOEvents must have a skymap.
    # new feature (10/24/2016): preliminary VOEvents can have a skymap,
    # but they don't have to.
    if (voevent_type in ["initial", "update"] or 
       (voevent_type == "preliminary" and skymap_filename != None)):

        fits_name = skymap_filename

        # Skymaps. Create group and set fits file name
        g = Group('GW_SKYMAP', skymap_type)

        fits_skymap_url = build_absolute_uri(reverse(
            "api:default:superevents:superevent-file-detail",
            args=[superevent.default_superevent_id, fits_name]), request)

        # Add parameters to the skymap group
        g.add_Param(Param(name="skymap_fits", dataType="string",
            ucd="meta.ref.url", value=fits_skymap_url,
            Description=["Sky Map FITS"]))

        w.add_Group(g)

    # Analysis specific attributes
    if voevent_type != 'retraction':
        classification_group = Group('Classification', Description=["Source "
            "classification: binary neutron star (BNS), neutron star-black "
            "hole (NSBH), binary black hole (BBH), MassGap, or terrestrial "
            "(noise)"])
        properties_group = Group('Properties', Description=["Qualitative "
            "properties of the source, conditioned on the assumption that the "
            "signal is an astrophysical compact binary merger"])
        if isinstance(event, CoincInspiralEvent) and voevent_type != 'retraction':
            # get mchirp and mass
            mchirp = float(event.mchirp)
            mass = float(event.mass)
            # calculate eta = (mchirp/total_mass)**(5/3)
            eta = pow((mchirp/mass),5.0/3.0)

            # EM-Bright mass classifier information for CBC event candidates
            if BNS is not None:
                classification_group.add_Param(Param(name="BNS",
                    dataType="float", ucd="stat.probability",
                    value=BNS, Description=["Probability that the "
                    "source is a binary neutron star merger (both objects "
                    "lighter than 3 solar masses)"]))

            if NSBH is not None:
                classification_group.add_Param(Param(name="NSBH",
                    dataType="float", ucd="stat.probability",
                    value=NSBH, Description=["Probability that the "
                    "source is a neutron star-black hole merger (primary "
                    "heavier than 5 solar masses, secondary lighter than 3 "
                    "solar masses)"]))

            if BBH is not None:
                classification_group.add_Param(Param(name="BBH",
                    dataType="float", ucd="stat.probability",
                    value=BBH, Description=["Probability that the "
                    "source is a binary black hole merger (both objects "
                    "heavier than 5 solar masses)"]))

            if MassGap is not None:
                classification_group.add_Param(Param(name="MassGap",
                    dataType="float", ucd="stat.probability",
                    value=MassGap, Description=["Probability that the source "
                    "has at least one object between 3 and 5 solar masses"]))

            if Terrestrial is not None:
                classification_group.add_Param(Param(name="Terrestrial",
                    dataType="float", ucd="stat.probability",
                    value=Terrestrial, Description=["Probability "
                    "that the source is terrestrial (i.e., a background noise "
                    "fluctuation or a glitch)"]))

            # Add to source properties group
            if ProbHasNS is not None:
                properties_group.add_Param(Param(name="HasNS",
                    dataType="float", ucd="stat.probability", value=ProbHasNS,
                    Description=["Probability that at least one object in the "
                    "binary has a mass that is less than 2.83 solar masses"]))

            if ProbHasRemnant is not None:
                properties_group.add_Param(Param(name="HasRemnant",
                    dataType="float", ucd="stat.probability",
                    value=ProbHasRemnant, Description=["Probability that a "
                    "nonzero mass was ejected outside the central remnant "
                    "object"]))

            # build up MaxDistance. event.singleinspiral_set.all()?
            # Each detector calculates an effective distance assuming the inspiral is 
            # optimally oriented. It is the maximum distance at which a source of the 
            # given parameters would've been seen by that particular detector. To get
            # an effective 'maximum distance', we just find the minumum over detectors
            max_distance = event.singleinspiral_set.all().aggregate(
                max_dist=Min('eff_distance'))
            max_distance = max_distance or float('inf')
                
        elif isinstance(event, MultiBurstEvent):
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
                filepath = os.path.join(event.datadir,filename)
                if os.path.isfile(filepath):
                    datafile = open(filepath,"r")
                else:
                    raise VOEventBuilderException("No file found.")
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
            except Exception as e:
                logger.exception(e)

        elif isinstance(event, LalInferenceBurstEvent):
            w.add_Param(Param(name="frequency", 
                dataType="float", 
                ucd="gw.frequency", 
                unit="Hz", 
                value=float(event.frequency_mean),
                Description=["Mean frequency of GW burst signal"]))

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
            except Exception as e:
                logger.exception(e)

        # Add Groups to What block
        w.add_Group(classification_group)
        w.add_Group(properties_group)

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
    if superevent.voevent_set.count() > 1:
        c = Citations()
        for ve in superevent.voevent_set.all():
            # Oh, actually we need to exclude *this* voevent.
            if ve.N == voevent.N:
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
