
from django.http import HttpResponseForbidden
from django.template import RequestContext
from django.shortcuts import render
from django.conf import settings

from .models import Event, Group, Search, Pipeline
from .permission_utils import filter_events_for_user
from .permission_utils import internal_user_required
from django.db.models import Q

from django.urls import reverse

from .models import CoincInspiralEvent
from search.forms import SimpleSearchForm
from search.query.events import parseQuery


from django.db.models import Max, Min
import numpy as np
import base64
import sys
from datetime import timedelta, datetime
from django.utils import timezone
import pytz
import json
from plotly.offline import plot
import plotly.graph_objects as go

plot_title = "Events Uploaded Since {0} UTC"
plot_sub_title = "<br><sup> Online, Production Events in the Last Seven Days </sup>"

plt_title = plot_title + plot_sub_title

days_back = 7

@internal_user_required
def histo(request):
    fig = go.Figure()

    # Get the timedelta and get it in a queryable form:
    t_now = timezone.now()
    date_cutoff = t_now - timedelta(days=days_back)


    all_events_latency = list(Event.objects.filter(created__gt=date_cutoff, reporting_latency__isnull=False).values_list('reporting_latency', flat=True))

    for pipeline in Pipeline.objects.filter(pipeline_type=Pipeline.PIPELINE_TYPE_SEARCH_PRODUCTION):
        pipeline_trace = list(Event.objects.filter(graceid__contains='G', 
                                  offline=False,
                                  created__gt=date_cutoff, 
                                  reporting_latency__isnull=False, 
                                  pipeline=pipeline).values_list('reporting_latency', flat=True))
        fig.add_trace(go.Histogram(x=pipeline_trace,
                                   name=pipeline.name))
    
    # The two histograms are drawn on top of another
    #fig.update_layout(barmode='stack',
    fig.update_layout(barmode='overlay',
            title={
                'text': plt_title.format(date_cutoff.strftime("%m/%d/%Y, %H:%M:%S")),
                'xanchor': 'center',
                'x':0.5,},
            xaxis_title="Reporting Latency (s)",
            yaxis_title="Number of Production Events",
            legend_title="Pipeline",
            paper_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(opacity=0.75)
    latency_plot_div = plot(fig, output_type='div')



    return render(request, 'gracedb/reports.html',
        context=
            {'latency_plot_div': latency_plot_div,
             'date_cutoff': date_cutoff}
        )

