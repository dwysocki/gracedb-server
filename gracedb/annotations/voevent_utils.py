# See the VOEvent specification for details
# http://www.ivoa.net/Documents/latest/VOEvent.html

import datetime
import logging
import os

from scipy.constants import c, G, pi
import voeventparse as vp

from django.conf import settings
from django.urls import reverse

from core.time_utils import gpsToUtc
from core.urls import build_absolute_uri
from events.models import VOEventBase, Event
from events.models import CoincInspiralEvent, MultiBurstEvent, \
    LalInferenceBurstEvent
from superevents.shortcuts import is_superevent

# Set up logger
logger = logging.getLogger(__name__)


###############################################################################
# SETUP #######################################################################
###############################################################################
# Dict of VOEvent type abbreviations and full strings
VOEVENT_TYPE_DICT = dict(VOEventBase.VOEVENT_TYPE_CHOICES)


# Used to create the Packet_Type parameter block
# Note: order matters. The order of this dict is the 
# same as VOEVENT_TYPE_DICT.

PACKET_TYPES = {
    VOEventBase.VOEVENT_TYPE_PRELIMINARY: (150, 'LVC_PRELIMINARY'),
    VOEventBase.VOEVENT_TYPE_INITIAL: (151, 'LVC_INITIAL'),
    VOEventBase.VOEVENT_TYPE_UPDATE: (152, 'LVC_UPDATE'),
    VOEventBase.VOEVENT_TYPE_RETRACTION: (164, 'LVC_RETRACTION'),
    VOEventBase.VOEVENT_TYPE_EARLYWARNING: (163, 'LVC_EARLY_WARNING'),
}


# Description strings
DEFAULT_DESCRIPTION = \
    "Candidate gravitational wave event identified by low-latency analysis"
INSTRUMENT_DESCRIPTIONS = {
    "H1": "H1: LIGO Hanford 4 km gravitational wave detector",
    "L1": "L1: LIGO Livingston 4 km gravitational wave detector",
    "V1": "V1: Virgo 3 km gravitational wave detector",
    "K1": "K1: KAGRA 3 km gravitational wave detector"
}


###############################################################################
# MAIN ########################################################################
###############################################################################
def construct_voevent_file(obj, voevent, request=None):

    # Setup ###################################################################
    ## Determine event or superevent
    obj_is_superevent = False
    if is_superevent(obj):
        obj_is_superevent = True
        event = obj.preferred_event
        graceid = obj.default_superevent_id
        obj_view_name = "superevents:view"
        fits_view_name = "api:default:superevents:superevent-file-detail"
    else:
        event = obj
        graceid = obj.graceid
        obj_view_name = "view"
        fits_view_name = "api:default:events:files"

    # Get the event subclass (CoincInspiralEvent, MultiBurstEvent, etc.) and
    # set that as the event
    event = event.get_subclass_or_self()

    ## Let's convert that voevent_type to something nicer looking
    voevent_type = VOEVENT_TYPE_DICT[voevent.voevent_type]

    ## Now build the IVORN.
    if voevent_type == 'earlywarning':
        type_string = 'EarlyWarning'
    else: 
        type_string = voevent_type.capitalize()
    voevent_id = '{gid}-{N}-{type_str}'.format(type_str=type_string,
        gid=graceid, N=voevent.N)

    ## Determine role
    if event.is_mdc() or event.is_test():
        role = vp.definitions.roles.test
    else:
        role = vp.definitions.roles.observation

    ## Instantiate VOEvent
    v = vp.Voevent(settings.VOEVENT_STREAM, voevent_id, role)

    ## Set root Description
    if voevent_type != 'retraction':
        v.Description = "Report of a candidate gravitational wave event"

    # Overwrite the description for early warning events:
    if voevent_type == 'earlywarning':
        v.Description = "Early warning report of a candidate gravitational wave event"

    # Who #####################################################################
    ## Remove Who.Description
    v.Who.remove(v.Who.Description)

    ## Set Who.Date
    vp.set_who(
        v,
        date=datetime.datetime.utcnow()
    )
    v.Who.Date += 'Z'

    ## Set Who.Author
    vp.set_author(
        v,
        contactName="LIGO Scientific Collaboration, Virgo Collaboration, and KAGRA Collaboration"
    )

    # How #####################################################################
    if voevent_type != 'retraction':
        descriptions = [DEFAULT_DESCRIPTION]

        # Add instrument descriptions
        instruments = event.instruments.split(',')
        for inst in INSTRUMENT_DESCRIPTIONS:
            if inst in instruments:
                descriptions.append(INSTRUMENT_DESCRIPTIONS[inst])
        if voevent.coinc_comment:
            descriptions.append("A gravitational wave trigger identified a "
                                "possible counterpart GRB")
        vp.add_how(v, descriptions=descriptions)

    # What ####################################################################
    # UCD = Unified Content Descriptors
    # http://monet.uni-sw.gwdg.de/twiki/bin/view/VOEvent/UnifiedContentDescriptors
    # OR --   (from VOTable document, [21] below)
    # http://www.ivoa.net/twiki/bin/view/IVOA/IvoaUCD
    # http://cds.u-strasbg.fr/doc/UCD.htx
    #
    # which somehow gets you to:
    # http://www.ivoa.net/Documents/REC/UCD/UCDlist-20070402.html
    # where you might find some actual information.

    # Unit / Section 4.3 of [21] which relies on [25]
    # [21] http://www.ivoa.net/Documents/latest/VOT.html
    # [25] http://vizier.u-strasbg.fr/doc/catstd-3.2.htx
    #
    # Basically, a string that makes sense to humans about what units a value
    # is. eg. "m/s"

    ## Packet_Type param
    p_packet_type = vp.Param(
        "Packet_Type",
        value=PACKET_TYPES[voevent.voevent_type][0],
        ac=True
    )
    p_packet_type.Description = ("The Notice Type number is assigned/used "
        "within GCN, eg type={typenum} is an {typedesc} notice").format(
            typenum=PACKET_TYPES[voevent.voevent_type][0],
            typedesc=PACKET_TYPES[voevent.voevent_type][1]
        )
    v.What.append(p_packet_type)

    # Internal param
    p_internal = vp.Param(
        "internal",
        value=int(voevent.internal),
        ac=True
    )
    p_internal.Description = ("Indicates whether this event should be "
        "distributed to LSC/Virgo/KAGRA members only")
    v.What.append(p_internal)
    
    ## Packet serial number
    p_serial_num = vp.Param(
        "Pkt_Ser_Num",
        value=voevent.N,
        ac=True
    )
    p_serial_num.Description = ("A number that increments by 1 each time a "
                                "new revision is issued for this event")
    v.What.append(p_serial_num)

    ## Event graceid or superevent ID
    p_gid = vp.Param(
        "GraceID",
        value=graceid,
        ucd="meta.id",
        dataType="string"
    )
    p_gid.Description = "Identifier in GraceDB"
    v.What.append(p_gid)

    ## Alert type parameter
    if voevent_type == 'earlywarning':
        voevent_at = 'EarlyWarning'
    else:
        voevent_at = voevent_type.capitalize()

    p_alert_type = vp.Param(
        "AlertType",
        value = voevent_at,
        ucd="meta.version",
        dataType="string"
    )
    p_alert_type.Description = "VOEvent alert type"
    v.What.append(p_alert_type)

    ## Whether the event is a hardware injection or not
    p_hardware_inj = vp.Param(
        "HardwareInj",
        value=int(voevent.hardware_inj),
        ucd="meta.number",
        ac=True
    )
    p_hardware_inj.Description = ("Indicates that this event is a hardware "
                                  "injection if 1, no if 0")
    v.What.append(p_hardware_inj)

    ## Open alert parameter
    p_open_alert = vp.Param(
        "OpenAlert",
        value=int(voevent.open_alert),
        ucd="meta.number",
        ac=True
    )
    p_open_alert.Description = ("Indicates that this event is an open alert "
                                "if 1, no if 0")
    v.What.append(p_open_alert)

    ## Superevent page
    p_detail_url = vp.Param(
        "EventPage",
        value=build_absolute_uri(
            reverse(obj_view_name, args=[graceid]),
            request
        ),
        ucd="meta.ref.url",
        dataType="string"
    )
    p_detail_url.Description = ("Web page for evolving status of this GW "
                                    "candidate")
    v.What.append(p_detail_url)

    ## Only for non-retractions 
    if voevent_type != 'retraction':
        ## Instruments
        p_instruments = vp.Param(
            "Instruments",
            value=event.instruments,
            ucd="meta.code",
            dataType="string"
        )
        p_instruments.Description = ("List of instruments used in analysis to "
                                     "identify this event")
        v.What.append(p_instruments)

        ## False alarm rate
        if event.far:
            p_far = vp.Param(
                "FAR",
                value=float(max(event.far, settings.VOEVENT_FAR_FLOOR)),
                ucd="arith.rate;stat.falsealarm",
                unit="Hz",
                ac=True
            )
            p_far.Description = ("False alarm rate for GW candidates with "
                                 "this strength or greater")
            v.What.append(p_far)

        ## Whether this is a significant candidate or not
        p_significant = vp.Param(
            "Significant",
            value=int(voevent.significant),
            ucd="meta.number",
            ac=True
        )
        p_significant.Description = ("Indicates that this event is significant if "
                                     "1, no if 0")
        v.What.append(p_significant)

        ## Analysis group
        p_group = vp.Param(
            "Group",
            value=event.group.name,
            ucd="meta.code",
            dataType="string"
        )
        p_group.Description = "Data analysis working group"
        v.What.append(p_group)

        ## Analysis pipeline
        p_pipeline = vp.Param(
            "Pipeline",
            value=event.pipeline.name,
            ucd="meta.code",
            dataType="string"
        )
        p_pipeline.Description = "Low-latency data analysis pipeline"
        v.What.append(p_pipeline)

        ## Search type
        if event.search:
            p_search = vp.Param(
                "Search",
                value=event.search.name,
                ucd="meta.code",
                dataType="string"
            )
            p_search.Description = "Specific low-latency search"
            v.What.append(p_search)

        ## RAVEN specific entries
        if (is_superevent(obj) and voevent.raven_coinc):
            ext_id = obj.em_type
            ext_event = Event.getByGraceid(ext_id)
            emcoinc_params = []

            ## External GCN ID
            if ext_event.trigger_id:
                p_extid = vp.Param(
                    "External_GCN_Notice_Id",
                    value=ext_event.trigger_id,
                    ucd="meta.id",
                    dataType="string"
                )
                p_extid.Description = ("GCN trigger ID of external event")
                emcoinc_params.append(p_extid)

            ## External IVORN
            if ext_event.ivorn:
                p_extivorn = vp.Param(
                    "External_Ivorn",
                    value=ext_event.ivorn,
                    ucd="meta.id",
                    dataType="string"
                )
                p_extivorn.Description = ("IVORN of external event")
                emcoinc_params.append(p_extivorn)

            ## External Pipeline
            if ext_event.pipeline:
                p_extpipeline = vp.Param(
                    "External_Observatory",
                    value=ext_event.pipeline.name,
                    ucd="meta.code",
                    dataType="string"
                )
                p_extpipeline.Description = ("External Observatory")
                emcoinc_params.append(p_extpipeline)

            ## External Search
            if ext_event.search:
                p_extsearch = vp.Param(
                    "External_Search",
                    value=ext_event.search.name,
                    ucd="meta.code",
                    dataType="string"
                )
                p_extsearch.Description = ("External astrophysical search")
                emcoinc_params.append(p_extsearch)

            ## Time Difference
            if ext_event.gpstime and obj.t_0:
               deltat = round(ext_event.gpstime - obj.t_0, 2)
               p_deltat = vp.Param(
                   "Time_Difference",
                   value=float(deltat),
                   ucd="meta.code",
                   ac=True,
               )
               p_deltat.Description = ("Time difference between GW candidate "
                                       "and external event, centered on the "
                                       "GW candidate")
               emcoinc_params.append(p_deltat)

            ## Temporal Coinc FAR
            if obj.time_coinc_far:
                p_coincfar = vp.Param(
                    "Time_Coincidence_FAR",
                    value=obj.time_coinc_far,
                    ucd="arith.rate;stat.falsealarm",
                    ac=True,
                    unit="Hz"
                )
                p_coincfar.Description = ("Estimated coincidence false alarm "
                                          "rate in Hz using timing")
                emcoinc_params.append(p_coincfar)

            ## Spatial-Temporal Coinc FAR
            if obj.space_coinc_far:
                p_coincfar_space = vp.Param(
                    "Time_Sky_Position_Coincidence_FAR",
                    value=obj.space_coinc_far,
                    ucd="arith.rate;stat.falsealarm",
                    ac=True,
                    unit="Hz"
                )
                p_coincfar_space.Description = ("Estimated coincidence false alarm "
                                                "rate in Hz using timing and sky "
                                                "position")
                emcoinc_params.append(p_coincfar_space)

            ## RAVEN combined sky map
            if voevent.combined_skymap_filename:
                ## Skymap group
                ### fits skymap URL
                fits_skymap_url_comb = build_absolute_uri(
                    reverse(fits_view_name, args=[graceid,
                                                  voevent.combined_skymap_filename]),
                    request
                )
                p_fits_url_comb = vp.Param(
                    "joint_skymap_fits",
                    value=fits_skymap_url_comb,
                    ucd="meta.ref.url",
                    dataType="string"
                )
                p_fits_url_comb.Description = "Combined GW-External Sky Map FITS"
                emcoinc_params.append(p_fits_url_comb)

            ## Create EMCOINC group
            emcoinc_group = vp.Group(
                emcoinc_params,
                name='External Coincidence',
                type='External Coincidence'  # keep this only for backwards compatibility
            )
            emcoinc_group.Description = \
                ("Properties of joint coincidence found by RAVEN")
            v.What.append(emcoinc_group)

    # initial and update VOEvents must have a skymap.
    # new feature (10/24/2016): preliminary VOEvents can have a skymap,
    # but they don't have to.
    if (voevent_type in ["initial", "update"] or 
       (voevent_type in ["preliminary", "earlywarning"] and voevent.skymap_filename != None)):

        ## Skymap group
        ### fits skymap URL
        fits_skymap_url = build_absolute_uri(
            reverse(fits_view_name, args=[graceid, voevent.skymap_filename]),
            request
        )
        p_fits_url = vp.Param(
            "skymap_fits",
            value=fits_skymap_url,
            ucd="meta.ref.url",
            dataType="string"
        )
        p_fits_url.Description = "Sky Map FITS"

        ### Create skymap group with params
        skymap_group = vp.Group(
            [p_fits_url],
            name="GW_SKYMAP",
            type="GW_SKYMAP",
        )

        ### Add to What
        v.What.append(skymap_group)

    ## Analysis specific attributes
    if voevent_type != 'retraction':
        ### Classification group (EM-Bright params; CBC only)
        em_bright_params = []
        source_properties_params = []
        if (isinstance(event, CoincInspiralEvent) and
            voevent_type != 'retraction'):

            # EM-Bright mass classifier information for CBC event candidates
            if voevent.prob_bns is not None:
                p_pbns = vp.Param(
                    "BNS",
                    value=voevent.prob_bns,
                    ucd="stat.probability",
                    ac=True
                )
                p_pbns.Description = \
                    ("Probability that the source is a binary neutron star "
                     "merger (both objects lighter than 3 solar masses)")
                em_bright_params.append(p_pbns)

            if voevent.prob_nsbh is not None:
                p_pnsbh = vp.Param(
                    "NSBH",
                    value=voevent.prob_nsbh,
                    ucd="stat.probability",
                    ac=True
                )
                p_pnsbh.Description = \
                    ("Probability that the source is a neutron star-black "
                     "merger (secondary lighter than 3 solar masses)")
                em_bright_params.append(p_pnsbh)

            if voevent.prob_bbh is not None:
                p_pbbh = vp.Param(
                    "BBH",
                    value=voevent.prob_bbh,
                    ucd="stat.probability",
                    ac=True
                )
                p_pbbh.Description = ("Probability that the source is a "
                                      "binary black hole merger (both objects "
                                      "heavier than 3 solar masses)")
                em_bright_params.append(p_pbbh)

            #if voevent.prob_mass_gap is not None:
            #    p_pmassgap = vp.Param(
            #        "MassGap",
            #        value=voevent.prob_mass_gap,
            #        ucd="stat.probability",
            #        ac=True
            #    )
            #    p_pmassgap.Description = ("Probability that the source has at "
            #                              "least one object between 3 and 5 "
            #                              "solar masses")
            #    em_bright_params.append(p_pmassgap)

            if voevent.prob_terrestrial is not None:
                p_pterr = vp.Param(
                    "Terrestrial",
                    value=voevent.prob_terrestrial,
                    ucd="stat.probability",
                    ac=True
                )
                p_pterr.Description = ("Probability that the source is "
                                       "terrestrial (i.e., a background noise "
                                       "fluctuation or a glitch)")
                em_bright_params.append(p_pterr)

            # Add to source properties group
            if voevent.prob_has_ns is not None:
                p_phasns = vp.Param(
                    name="HasNS",
                    value=voevent.prob_has_ns,
                    ucd="stat.probability",
                    ac=True
                )
                p_phasns.Description = ("Probability that at least one object "
                                        "in the binary has a mass that is "
                                        "less than 3 solar masses")
                source_properties_params.append(p_phasns)

            if voevent.prob_has_remnant is not None:
                p_phasremnant = vp.Param(
                    "HasRemnant",
                    value=voevent.prob_has_remnant,
                    ucd="stat.probability",
                    ac=True
                )
                p_phasremnant.Description = ("Probability that a nonzero mass "
                                             "was ejected outside the central "
                                             "remnant object")
                source_properties_params.append(p_phasremnant)
            if voevent.prob_has_mass_gap is not None:
                p_pmassgap = vp.Param(
                    "HasMassGap",
                    value=voevent.prob_has_mass_gap,
                    ucd="stat.probability",
                    ac=True
                )
                p_pmassgap.Description = ("Probability that the source has at "
                                          "least one object between 3 and 5 "
                                          "solar masses")
                source_properties_params.append(p_pmassgap)

        elif isinstance(event, MultiBurstEvent):
            ### Central frequency
            p_central_freq = vp.Param(
                "CentralFreq",
                value=float(event.central_freq),
                ucd="gw.frequency",
                unit="Hz",
                ac=True,
            )
            p_central_freq.Description = \
                "Central frequency of GW burst signal"
            v.What.append(p_central_freq)

            ### Duration
            p_duration = vp.Param(
                "Duration",
                value=float(event.duration),
                unit="s",
                ucd="time.duration",
                ac=True,
            )
            p_duration.Description = "Measured duration of GW burst signal"
            v.What.append(p_duration)

        elif isinstance(event, LalInferenceBurstEvent):
            p_freq = vp.Param(
                "frequency",
                value=float(event.frequency_mean),
                ucd="gw.frequency",
                unit="Hz",
                ac=True,
            )
            p_freq.Description = "Mean frequency of GW burst signal"
            v.What.append(p_freq)

            # Calculate the fluence. 
            # From Min-A Cho: fluence = pi*(c**3)*(freq**2)*(hrss_max**2)*(10**3)/(4*G)
            # Note that hrss here actually has units of s^(-1/2)
            # XXX obviously need to refactor here.
            try:
                fluence = pi * pow(c,3) * pow(event.frequency,2) 
                fluence = fluence * pow(event.hrss,2)
                fluence = fluence / (4.0*G)

                p_fluence = vp.Param(
                    "Fluence",
                    value=fluence,
                    ucd="gw.fluence",
                    unit="erg/cm^2",
                    ac=True
                )
                p_fluence.Description = "Estimated fluence of GW burst signal"
                v.What.append(p_fluence)
            except Exception as e:
                logger.exception(e)

        ## Create classification group
        classification_group = vp.Group(
            em_bright_params,
            name='Classification',
            type='Classification'  # keep this only for backwards compatibility
        )
        classification_group.Description = \
            ("Source classification: binary neutron star (BNS), neutron star-"
             "black hole (NSBH), binary black hole (BBH), or "
             "terrestrial (noise)")
        v.What.append(classification_group)

        ## Create properties group
        properties_group = vp.Group(
            source_properties_params,
            name='Properties',
            type='Properties'  # keep this only for backwards compatibility
        )
        properties_group.Description = \
            ("Qualitative properties of the source, conditioned on the "
             "assumption that the signal is an astrophysical compact binary "
             "merger")
        v.What.append(properties_group)

    # WhereWhen ###############################################################
    # NOTE: we use a fake ra, dec, err, and units for creating the coords
    # object.  We are required to provide them by the voeventparse code, but
    # our "format" for VOEvents didn't have a Position2D entry.  So to make
    # the code work but maintain the same format, we add fake information here,
    # then remove it later.
    coords = vp.Position2D(
        ra=1, dec=2, err=3, units='degrees',
        system=vp.definitions.sky_coord_system.utc_fk5_geo
    )
    observatory_id = 'LIGO Virgo'
    vp.add_where_when(
        v,
        coords,
        gpsToUtc(event.gpstime),
        observatory_id
    )
    v.WhereWhen.ObsDataLocation.ObservationLocation.AstroCoords.Time.TimeInstant.ISOTime += 'Z'
    # NOTE: now remove position 2D so the fake ra, dec, err, and units
    # don't show up.
    ol = v.WhereWhen.ObsDataLocation.ObservationLocation
    ol.AstroCoords.remove(ol.AstroCoords.Position2D)

    # Citations ###############################################################
    if obj.voevent_set.count() > 1:

        ## Loop over previous VOEvents for this event or superevent and
        ## add them to citations
        event_ivorns_list = []
        for ve in obj.voevent_set.all():
            # Oh, actually we need to exclude *this* voevent.
            if ve.N == voevent.N:
                continue

            # Get cite type
            if voevent_type == 'retraction':
                cite_type = vp.definitions.cite_types.retraction
            else:
                cite_type = vp.definitions.cite_types.supersedes

            # Set up event ivorn
            ei = vp.EventIvorn(ve.ivorn, cite_type)

            # Add event ivorn
            event_ivorns_list.append(ei)

        # Add citations
        vp.add_citations(
            v,
            event_ivorns_list
        )
        # Get description for citation
        desc = None
        if voevent_type == 'preliminary':
            desc = 'Initial localization is now available (preliminary)'
        elif voevent_type == 'initial':
            desc = 'Initial localization is now available'
        elif voevent_type == 'update':
            desc = 'Updated localization is now available'
        elif voevent_type == 'retraction':
            desc = 'Determined to not be a viable GW event candidate'
        elif voevent_type == 'earlywarning':
            desc = 'Early warning localization is now available'
        if desc is not None:
            v.Citations.Description = desc

    # Return the document as a string, along with the IVORN ###################
    xml = vp.dumps(v, pretty_print=True)
    return xml, v.get('ivorn')

