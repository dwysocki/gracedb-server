
# Taken from VOEventLib example code, which is:
# Copyright 2010 Roy D. Williams
# then modified
"""
buildVOEvent: Creates a complex VOEvent with tables
See the VOEvent specification for details
http://www.ivoa.net/Documents/latest/VOEvent.html
"""

from VOEventLib.VOEvent import VOEvent, Who, What, Author, Param
from VOEventLib.Vutil import makeWhereWhen, stringVOEvent

# XXX ER2.utils.  utils is in project directory.  ugh.
from utils import gpsToUtc
from django.conf import settings
from django.core.urlresolvers import reverse

def buildVOEvent(gevent, request=None, description=None, role=None):

    objid = gevent.graceid()

    ############ VOEvent header ############################
    v = VOEvent.VOEvent(version="2.0")
    v.set_ivorn(settings.SKYALERT_IVORN_PATTERN % objid)
    v.set_role(role or settings.SKYALERT_ROLE)
    v.set_Description(description or settings.SKYALERT_DESCRIPTION)

    ############ Who ############################
    w = Who()
    a = Author()
    a.add_contactName("LIGO Scientific Consortium")
    a.add_contactEmail("postmaster@ligo.org")
    w.set_Author(a)
    v.set_Who(w)

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

    # params related to the event. None are in Groups.
    p = Param(name="gracedbid", ucd="meta.id", value="%s"% objid)
    p.set_Description(["Identifier assigned by gracedb"])
    w.add_Param(p)

    p = Param(name="gpstime", ucd="time.epoch", dataType="int",  value=str(gevent.gpstime))
    p.set_Description(["GPS time of the trigger"])
    w.add_Param(p)

    p = Param(name="likelihood", ucd="stat.likelihood", dataType="float",  value=str(gevent.likelihood))
    p.set_Description(["Likelihood"])
    w.add_Param(p)

    # For GCN / SkyAlert.
    #
    # pipeline  dataType="string"   ucd=
    # FAR       dataType="float"    ucd=arith.rate   unit="Hz"
    # DQ level  dataType="?"        ucd=
    # IFO list  dataType="string"   ucd=
    # URL to skymap   Reference/URL

    p = Param(name="analysistype", dataType="string", value=str(gevent.get_analysisType_display()))
    p.set_Description(["LIGO analysis which produced this result"])
    w.add_Param(p)

    try:
        p = Param(name="far", dataType="float", ucd="arith.rate", unit="Hz", value=float(gevent.far))
        p.set_Description(["False Alarm Rate"])
        w.add_Param(p)
    except:
        pass

    p = Param(name="ifolist", dataType="string", value=str(gevent.instruments))
    p.set_Description(["Interferometers"])
    w.add_Param(p)

    # Skymaps
    #  Four of them, per Roy Williams.  (FITS and PNG) x  (x509 auth and Shib auth)

    # relative URLs
    x509_fits_skymap_url = reverse("download", args=[gevent.graceid(), "general/bayestar/skymap.fits"])
    x509_png_skymap_url = reverse("download", args=[gevent.graceid(), "general/bayestar/skymap.png"])

    # XXX gracedb.ligo.org urls.  they are a little problematic.
    # they do not do mime-types correctly and they do not let go of the connection for some reason.
    #shib_fits_skymap_url = reverse("file", args=[gevent.graceid(), "general/bayestar/skymap.fits"])
    #shib_png_skymap_url = reverse("file", args=[gevent.graceid(), "general/bayestar/skymap.png"])

    # Old sad bad ldad-jobs urls
    shib_fits_skymap_url = gevent.weburl() + "/general/bayestar/skymap.fits"
    shib_png_skymap_url  = gevent.weburl() + "/general/bayestar/skymap.png"

    # Need request to build absolute URL
    # XXX should probably be an error if we can't give the full absolute url.
    if request:

        # Shib URL
        # https://gracedb.ligo.org/events/G43582/files/skymap_G43582.png

        x509_fits_skymap_url = request.build_absolute_uri(x509_fits_skymap_url)
        x509_png_skymap_url = request.build_absolute_uri(x509_png_skymap_url)

        shib_fits_skymap_url = request.build_absolute_uri(shib_fits_skymap_url)
        shib_png_skymap_url = request.build_absolute_uri(shib_png_skymap_url)

        p = Param(name="skymap_png_x509", ucd="meta.ref.url", value=x509_png_skymap_url)
        p.set_Description(["Sky Map image X509 protected"])
        w.add_Param(p)

        p = Param(name="skymap_fits_x509", ucd="meta.ref.url", value=x509_fits_skymap_url)
        p.set_Description(["Sky Map FITS X509 protected"])
        w.add_Param(p)

        p = Param(name="skymap_png_shib", ucd="meta.ref.url", value=shib_png_skymap_url)
        p.set_Description(["Sky Map image Shibboleth protected"])
        w.add_Param(p)

        p = Param(name="skymap_fits_shib", ucd="meta.ref.url", value=shib_fits_skymap_url)
        p.set_Description(["Sky Map FITS Shibboleth protected"])
        w.add_Param(p)

#   if request:
#       # XXX should probably be an error if we can't give the full url.
#       skymap_url = request.build_absolute_uri(skymap_url)
#   p = Param(name="skymap_png", value=skymap_url)
#   p.set_Description(["Sky Map Image"])
#   #p.set_Reference([Reference(uri=skymap_url)])
#   w.add_Param(p)


    v.set_What(w)

    ############ Wherewhen ############################
    wwd = {'observatory':     'LIGO',
           'coord_system':    'UTC-FK5-GEO',
           # XXX time format
           'time':            str(gpsToUtc(gevent.gpstime).isoformat())[:-6],   #'1918-11-11T11:11:11',
           'timeError':       1.0,
           'longitude':       123.45,
           'latitude':        67.89,
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

def submitToSkyalert(gevent, validate_only=False):
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

    dict['xmlText'] = buildVOEvent(gevent)
    params = urllib.urlencode(dict)
    f = urllib.urlopen(url, params)
    result = f.read()
    return result


