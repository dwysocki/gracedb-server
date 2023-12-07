import json
import logging
from pyparsing import Keyword, CaselessKeyword, oneOf, Literal, Or, \
    OneOrMore, ZeroOrMore, Optional, Suppress

from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse, HttpResponseBadRequest, \
    HttpResponseServerError
from django.urls import reverse as django_reverse

from ligo.lw import utils as ligolw_utils

from events.models import Label
from events.permission_utils import is_external
from events.templatetags.scientific import scientific
from events.templatetags.timeutil import timeSelections
from events.view_utils import assembleLigoLw

# Set up logger
logger = logging.getLogger(__name__)

# The maximum number of rows to be returned by flexigridResponse
# in the event that the user asks for all of them.
MAX_FLEXI_ROWS = 250

# Limit on number of LIGOLW results
RESULTS_LIMIT = 1000

# Define some response templates:
LABEL_HTML_TEMPLATE = '<span style="color: {}">{}</span>'
EVENT_HTTP_TEMPLATE = '<a href="{}">{}</a>'

def get_search_results_as_ligolw(objects):

    if objects.count() > RESULTS_LIMIT:
        return HttpResponseBadRequest(("Sorry -- no more than {0} events "
            "currently allowed").format(RESULTS_LIMIT))

    # Only valid for events, not superevents
    if objects.model.__name__ == "Superevent":
        return HttpResponseBadRequest("LigoLw tables are not available "
            "for superevents")

    try:
        xmldoc = assembleLigoLw(objects)
    except IOError as e:
        msg = ("At least one of the query results has no associated coinc.xml "
            "file. LigoLw tables are only available for queries which return "
            "only coinc inspiral events. Please try your query again.")
        return HttpResponseBadRequest(msg)
    except Exception as e:
        msg = ("An error occured while trying to compile LigoLw "
            "results: {0}").format(e)
        return HttpResponseServerError(msg)

    response = HttpResponse(content_type='application/xml')
    response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
    ligolw_utils.write_fileobj(xmldoc, response)
    return response


def superevent_flexigrid_response(request, objects):
    response = HttpResponse(content_type='application/json')

    sortname = request.GET.get('sidx', None)    # get index row - i.e. user click to sort
    sortorder = request.GET.get('sord', 'desc') # get the direction
    page = int(request.GET.get('page', 1))      # get the requested page
    rp = int(request.GET.get('rows', 10))       # get how many rows we want to have into the grid

    # select related objects to reduce the number of queries.
    objects = objects.select_related('submitter', 'preferred_event')
    objects = objects.prefetch_related('events', 'labels')

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
        total_pages = 1 if (total > 0) else 0
        page = 1
        end = max(total, 0)

        if total > MAX_FLEXI_ROWS:
            return HttpResponseBadRequest("Too many rows! Please try loading a smaller number.")

    # Function for constructing HTML link to event page from graceid
    ev_link = lambda gid: '<a href="{url}">{graceid}</a>'.format(
        url=django_reverse("view", args=[gid]), graceid=gid)

    for object in objects[start:end]:
        t_start_times = timeSelections(object.t_start)
        t_0_times = timeSelections(object.t_0)
        t_end_times = timeSelections(object.t_end)
        created_times = timeSelections(object.created)

        cell_values = [
            '<a href="{0}">{1}</a>'.format(
                django_reverse("superevents:view", args=[
                object.superevent_id]), object.superevent_id),
            #Labels
            " ".join(["""<span onmouseover="tooltip.show(tooltiptext('%s', '%s', '%s'));" onmouseout="tooltip.hide();" style="color: %s"> %s </span>""" % (label.label.name, label.creator.username, label.created, label.label.defaultColor, label.label.name) for label in object.labelling_set.all()]),
            str(object.far),
            t_start_times.get('gps', ""),
            t_0_times.get('gps', ""),
            t_end_times.get('gps', ""),
            str(object.is_gw),
            '<a href="%s">Data</a>' % '#', # TODO: fix this #object.weburl(),
            created_times.get('utc', ""),
            "%s %s" % (object.submitter.first_name, object.submitter.last_name)
        ]
        if request.user.is_authenticated:
            cell_values.insert(3, ev_link(object.preferred_event.graceid))
            cell_values.insert(4, ", ".join([ev_link(ev.graceid) for ev in
                object.get_internal_events()]))
            cell_values.insert(5, ", ".join([ev_link(ev.graceid) for ev in
                object.get_external_events()]))

        rows.append({
            'id' : object.id,
            'cell': cell_values,
        })

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

    return response


def event_flexigrid_response(request, objects):
    response = HttpResponse(content_type='application/json')

    sortname = request.GET.get('sidx', None)    # get index row - i.e. user click to sort
    sortorder = request.GET.get('sord', 'desc') # get the direction
    page = int(request.GET.get('page', 1))      # get the requested page
    rp = int(request.GET.get('rows', 10))       # get how many rows we want to have into the grid

    get_neighbors = request.GET.get('get_neighbors', False) # whether to retrieve the neighbors
    if get_neighbors in ['True', 'true', 'T', 't', 1, '1']:
        get_neighbors = True
    else:
        get_neighbors = False

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
        total_pages = 1 if (total > 0) else 0
        page = 1
        end = max(total, 0)

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
                            (django_reverse("view", args=[object.graceid]), object.graceid),
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
                (django_reverse("view", args=[n.graceid]), n.graceid) for n in object.neighbors()]))

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

    return response

def superevent_datatables_response(request, objects):
    response = HttpResponse(content_type='application/json')
    # The column order is: (omitting the 'links')
    #  1. UID
    #  2. Labels
    #  3. FAR
    #  4. Preferred Event
    #  5. GW Events
    #  6. t_0
    #  7. Submitted
    #  8. Submitted By

    # select related objects to reduce the number of queries.
    objects = objects.select_related('submitter', 'preferred_event')
    objects = objects.prefetch_related('events', 'labels')

    # Initialize 'data':
    num_objects = objects.count()
    data =[None] * num_objects

    # Loop through objects:
    for row_num, s in enumerate(objects):
        row = [None] * 8
        # Column 1, UID:
        row[0] = EVENT_HTTP_TEMPLATE.format(
            django_reverse("superevents:view", args=[s.superevent_id]),
            s.superevent_id)

        # Column 2, Labels:
        row[1] = " ".join([LABEL_HTML_TEMPLATE.format(a.label.defaultColor, a.label.name) for a in s.labelling_set.all()])

        # Column 3, FAR:
        row[2] = s.far

        # Column 4, Preferred Event:
        row[3] = EVENT_HTTP_TEMPLATE.format(
            django_reverse("view", args=[s.preferred_event.graceid,]),
            s.preferred_event.graceid)

        # Column 5, GW Events:
        row[4] = ' '.join([EVENT_HTTP_TEMPLATE.format(
             django_reverse("view", args=[a.graceid]),
             a.graceid) for a in s.events.all()])

        # Column 6,  t_0:
        row[5] = str(round(s.t_0,3))

        # Column 7, Submission Time:
        row[6] = timeSelections(s.created)['utc']

        # Column 8, Submitted By:
        row[7] = s.submitter.get_full_name()

        # Add the row to the data output:
        data[row_num] = row

    msg = json.dumps({"data": data})
    response['Content-length'] = len(msg)
    response.write(msg)

    return response

def event_datatables_response(request, objects): 
    response = HttpResponse(content_type='application/json')
    # The column order is: (omitting the 'links')
    #  1. UID
    #  2. Labels
    #  3. Group
    #  4. Pipeline
    #  5. Search
    #  6. Event Time
    #  7. Instruments
    #  8. FAR
    #  9. Submitted
    # 10. Submitted By

    # select related objects to reduce the number of queries.
    objects = objects.select_related('group', 'pipeline', 'search', 'submitter')

    # Initialize 'data':
    num_objects = objects.count()
    data =[None] * num_objects

    # Determine if this is an external request: 
    ext_req = is_external(request.user)

    for row_num, e in enumerate(objects):
        row = [None] * 10
        # Column 1, UID:
        row[0] = EVENT_HTTP_TEMPLATE.format(
            django_reverse("view", args=[e.graceid,]),
            e.graceid)

        # Column 2, Labels:
        row[1] = " ".join([LABEL_HTML_TEMPLATE.format(a.label.defaultColor, a.label.name) for a in e.labelling_set.all()])

        # Column 3, Group:
        row[2] = e.group.name

        # Column 4, Pipeline
        row[3] = e.pipeline.name

        # Column 5, Search (might be empty):
        if e.search:
            search_name = e.search.name
        else:
            search_name = ' '
        row[4] = search_name

        # Column 6, Event Time:
        row[5] = timeSelections(e.gpstime).get('gps')

        # Column 7, Instruments:
        row[6] = e.instruments

        # Coluimn 8, FAR: Note, the switch is in here to hide the "true" FAR from 
        # external searches. 
        display_far = scientific(e.far)
        if e.far and ext_req:
            if e.far < settings.VOEVENT_FAR_FLOOR:
                display_far = "< %s" % scientific(settings.VOEVENT_FAR_FLOOR)
        row[7] = display_far

        # Column 9, Submitted:
        row[8] = timeSelections(e.created)['utc']

        # Column 10, Submitted By:
        row[9] = e.submitter.get_full_name()

        # Add the row to the data output:
        data[row_num] = row

    msg = json.dumps({"data": data})
    response['Content-length'] = len(msg)
    response.write(msg)

    return response
