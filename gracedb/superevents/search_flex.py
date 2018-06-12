from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.urls import reverse as django_reverse

from events.templatetags.scientific import scientific
from events.templatetags.timeutil import timeSelections

import os
import json
import logging
logger = logging.getLogger(__name__)

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

# The maximum number of rows to be returned by flexigridResponse
# in the event that the user asks for all of them.
MAX_FLEXI_ROWS = 250


def flexigridResponse(request, objects):
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
        total_pages = 1
        page = 1
        end = total-1

        if total > MAX_FLEXI_ROWS:
            return HttpResponseBadRequest("Too many rows! Please try loading a smaller number.")

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
            str(object.preferred_event.graceid()),
            " ".join([ev.graceid() for ev in object.get_internal_events()]),
            " ".join([ev.graceid() for ev in object.get_external_events()]),
            t_start_times.get('gps', ""),
            t_0_times.get('gps', ""),
            t_end_times.get('gps', ""),
            str(object.is_gw),
            '<a href="%s">Data</a>' % '#', # TODO: fix this #object.weburl(),
            created_times.get('utc', ""),
            "%s %s" % (object.submitter.first_name, object.submitter.last_name)
        ]

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
