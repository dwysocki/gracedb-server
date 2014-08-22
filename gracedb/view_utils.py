
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from django.utils.html import escape, urlize
from django.utils.safestring import mark_safe

from utils.vfile import VersionedFile
from views import view

import os
from django.conf import settings

from templatetags.scientific import scientific

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

GRACEDB_DATA_DIR = settings.GRACEDB_DATA_DIR

import json

def assembleLigoLw(objects):
    from glue.ligolw import ligolw
    # lsctables MUST be loaded before utils.
    from glue.ligolw import lsctables
    from glue.ligolw import utils
    from glue.ligolw.utils import ligolw_add

    xmldoc = ligolw.Document()
    for obj in objects:
        fname = os.path.join(GRACEDB_DATA_DIR, obj.graceid(), "private", "coinc.xml")
        utils.load_filename(fname, xmldoc=xmldoc)

    ligolw_add.reassign_ids(xmldoc)
    ligolw_add.merge_ligolws(xmldoc)
    ligolw_add.merge_compatible_tables(xmldoc)
    return xmldoc

def _saveUploadedFile(event, uploadedFile):
    # XXX Hardcoding.
    fname = os.path.join(GRACEDB_DATA_DIR, event.graceid(), "private", uploadedFile.name)
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
    response = HttpResponse(mimetype='application/json')

    #sortname = request.POST.get('sortname', None)
    #sortorder = request.POST.get('sortorder', 'desc')
    #page = int(request.POST.get('page', 1))
    #rp = int(request.POST.get('rp', 10))

    sortname = request.GET.get('sidx', None)    # get index row - i.e. user click to sort
    sortorder = request.GET.get('sord', 'desc') # get the direction
    page = int(request.GET.get('page', 1))      # get the requested page
    rp = int(request.GET.get('rows', 10))       # get how many rows we want to have into the grid

    if sortname:
        if sortorder == "desc":
            sortname = "-" + sortname
        objects = objects.order_by(sortname)

    start = (page-1) * rp
    rows = []
    total = objects.count()

    if total:
        total_pages = (total / rp) + 1
    else:
        total_pages = 0

    if page > total_pages:
        page = total_pages

    for object in objects[start:start+rp]:
        event_times = timeSelections(object.gpstime)
        created_times = timeSelections(object.created)
        rows.append(
            { 'id' : object.id,
              'cell': [ '<a href="%s">%s</a>' %
                            (reverse(view, args=[object.graceid()]), object.graceid()),
                         #Labels
                        " ".join(["""<span onmouseover="tooltip.show(tooltiptext('%s', '%s', '%s'));" onmouseout="tooltip.hide();"  style="color: %s"> %s </span>""" % (label.label.name, label.creator.username, label.created, label.label.defaultColor, label.label.name)
                                for label in object.labelling_set.all()]),
                        # Links to neighbors
                        ', '.join([
                            '<a href="%s">%s</a>' %
                            (reverse(view, args=[n.graceid()]), n.graceid())
                            for n in object.neighbors()
                        ]),
                        object.group.name,
                        object.get_analysisType_display(),

                        event_times.get('gps',""),
                        #event_times['utc'],

                        object.instruments,

                        scientific(object.far),

                        '<a href="%s">Data</a>' % object.weburl(),

                        #created_times['gps'],
                        created_times.get('utc',""),

                        "%s %s" % (object.submitter.first_name, object.submitter.last_name)

                      ]
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

def get_file(graceid, filename="event.log"):
    dirPrefix = GRACEDB_DATA_DIR
    logfilename = os.path.join(dirPrefix, graceid, "private", filename)
    contents = ""
    try:
        lines = open(logfilename, "r").readlines()
        contents = "<br/>".join([ escape(line) for line in lines])
        contents = mark_safe(urlize(contents))
    except Exception:
        contents = None
    return contents


