
from django.http import HttpResponseForbidden
from django.template import RequestContext
from django.shortcuts import render
from django.conf import settings

from .models import Event, Group, Search
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


@internal_user_required
def histo(request):

    days_back = 7
    x0 = np.random.randn(2000)
    x1 = np.random.randn(2000) + 1

    fig = go.Figure()
    fig.add_trace(go.Histogram(x=x0))
    fig.add_trace(go.Histogram(x=x1))
    
    # The two histograms are drawn on top of another
    fig.update_layout(barmode='stack')
    latency_plot_div = plot(fig, output_type='div')



    return render(request, 'gracedb/reports.html',
        context=
            {'latency_plot_div': latency_plot_div}
        )

