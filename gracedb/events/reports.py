
from django.http import HttpResponseForbidden
from django.template import RequestContext
from django.shortcuts import render
from django.conf import settings
from django import forms

from .models import Event, Group, Search, Pipeline, Label
from superevents.models import Superevent, Labelling
from ligoauth.decorators import internal_user_required
from django.db.models import Q

from django.urls import reverse
from django.utils.decorators import method_decorator

from search.forms import SimpleSearchForm
from search.query.events import parseQuery

from django.db.models import Max, Min, Avg 
from django.db.models.aggregates import StdDev
from datetime import datetime, timedelta
from gpstime import gpstime
from django.utils import timezone
from plotly.io import to_html
from plotly.offline import plot
from tailslide import Median, Percentile

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

YEAR_RANGE = list(range(datetime.now().year, 2013, -1))
INITIAL_DAYS_BACK = 31

EVENT_SEARCH_CHOICES = (
    ('AllSky', 'AllSky'),
    ('EarlyWarning', 'EarlyWarning'),
    ('SSM', 'SSM'),
    ('BBH', 'BBH'),
    ('VTInjection', 'VTInjection'),
)

EVENT_SEARCH_CHOICES_INITAL = ['AllSky']

SUPEREVENT_CATEGORIES = (
    (Superevent.SUPEREVENT_CATEGORY_PRODUCTION, 'Production'),
    (Superevent.SUPEREVENT_CATEGORY_MDC, 'MDC'),
)

class lookback_days_form(forms.Form):
    start_date = forms.DateField(label='Start Date',
        widget=forms.SelectDateWidget(years=YEAR_RANGE),
                    )
    end_date = forms.DateField(label='End Date',
        widget=forms.SelectDateWidget(years=YEAR_RANGE),
        initial = datetime.now()
                    )

    searches_choice = forms.MultipleChoiceField(widget=forms.CheckboxSelectMultiple,
                          choices=EVENT_SEARCH_CHOICES,
                          required=False,
                          label='Event Searches',
                          initial=EVENT_SEARCH_CHOICES_INITAL)

    superevent_type = forms.ChoiceField(widget=forms.RadioSelect,
                          choices=SUPEREVENT_CATEGORIES,
                          label='Superevent Category',
                          initial=Superevent.SUPEREVENT_CATEGORY_PRODUCTION)
    

@internal_user_required
def reports_page_context(request):

    # start with a blank context dict: 
    context = {}

    if request.method == 'POST':
        form = lookback_days_form(request.POST)

        if form.is_valid():
            start_date = form.cleaned_data['start_date']
            start_date = datetime.combine(start_date, datetime.min.time())
            end_date = form.cleaned_data['end_date']
            end_date = datetime.combine(end_date, datetime.min.time())
            days_back = (end_date - start_date).days
            event_searches = form.cleaned_data['searches_choice']
            superevent_category=form.cleaned_data['superevent_type']

    else:
        days_back = INITIAL_DAYS_BACK
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        event_searches = EVENT_SEARCH_CHOICES_INITAL
        superevent_category = Superevent.SUPEREVENT_CATEGORY_PRODUCTION
        form = lookback_days_form(initial={'start_date': start_date})

    # update context with form:
    context.update({'form': form})

    # update context with histogram div:
    context.update({'hist': latency_histo(days_back, start_date, 
                                end_date, event_searches)})

    # update with the time-to-alert div:
    context.update({'tta': time_to_alert(start_date, end_date, superevent_category)}) 

    return render(request, 'gracedb/reports.html', context)


def time_to_alert(start_date, end_date, superevent_category):
    # Set up the query to get all production superevents within the date range
    # that have the GCN_PRELIM_SENT label applied:

    # Get the GCN_PRELIM_SENT label first so we only hit the db once:
    gcn = Label.objects.get(name='GCN_PRELIM_SENT')

    sevents = Superevent.objects.filter(category=superevent_category,
                 t_0__range=(gpstime.fromdatetime(start_date).gps(),
                             gpstime.fromdatetime(end_date).gps()),
                 labels=gcn,
              ).order_by('superevent_id')

    # Now get the GCN_PRELIM_SENT label objects:
    labs = Labelling.objects.filter(label=gcn, superevent__in=sevents).order_by('superevent__superevent_id')

    # Make lists of the relevant values. One has superevent_id and t_0, the
    # other has the created time of the gcn label (which is a proxy for
    # when the alert goes out). Everything should be ordered correctly, but
    # we're going to add a verification step just in case. 
    sevents_values = list(sevents.values_list('superevent_id', 't_0', 'created'))
    label_values = list(labs.values_list('superevent__superevent_id', 'created'))

    # Construct a list where each item looks like:
    # [superevent_id (string), created (datetime), time-to-alert (float)]
    #results = 
    if sevents_values:
        results = [[i[0][0], i[0][2], gpstime.fromdatetime(i[1][1]).gps() - float(i[0][1])] for i in zip(sevents_values, label_values) if i[0][0] == i[1][0]]
        np_results = np.array(results)
    else:
        np_results = np.zeros((1,3))

    
    # Try making a pandas dataframe:
    pd_results = pd.DataFrame(np_results,
                     columns=['superevent_id', 'created', 'time_to_alert'],
                     )


    # Make a scatter plot:
    scatter_fig = px.scatter(pd_results,
                         x='created',
                         y='time_to_alert',
                         hover_data='superevent_id',
                      )
    scatter_fig.update_traces(marker_size=10)

    scatter_fig.update_layout(title={
                                'text': 'Superevent Time-to-Alert',
                                'xanchor': 'center',
                                'x':0.5,},
                               xaxis_title="Date",
                               yaxis_title="Time-to-Alert (s)",
                               autosize=True,
                               paper_bgcolor='rgba(0, 0, 0, 0)',
                               margin={'l': 0, 'r': 0},
                    )


    return {'tta_plot_div': to_html(scatter_fig,
                                 include_plotlyjs=False,
                                 full_html=False,
                                 default_width='100%',),
            'tta_stats': {'med': pd_results['time_to_alert'].median(),
                          'nfp': pd_results['time_to_alert'].quantile(0.95)},
       }


def latency_histo(days_back, start_date, end_date, event_searches):
    plot_title = "Events Uploaded Between {start} and {end}".format(
                     start=start_date.strftime("%m/%d/%Y"),
                     end=end_date.strftime("%m/%d/%Y"),
                 )
    plot_sub_title = f"<br><sup> Online, Production Events in {days_back} Days </sup>"
    plt_title = plot_title + plot_sub_title

    fig = go.Figure()

    # Get the timedelta and get it in a queryable form:
    t_now = timezone.now()
    date_cutoff = t_now - timedelta(days=days_back)

    # Zero out the list of pipeline statistics:
    aggregated_stats =[]

    # Loop over pipelines that are determined to be "Production" search pipelines and 
    # retrieve data, and populate histograms:

    for pipeline in Pipeline.objects.filter(pipeline_type=Pipeline.PIPELINE_TYPE_SEARCH_PRODUCTION):

        # Generate the queryset for production (G) events, uploaded online, that have a 
        # valid value of reporting_latency. There has to be a way to combine these so you
        # hit the db once, but for now its just once for a list of values, and once for
        # aggregated values. 
        pipeline_query = Event.objects.filter(search__name__in=event_searches,
                                  offline=False,
                                  created__gt=date_cutoff,                                                                               reporting_latency__isnull=False,
                                  pipeline=pipeline).order_by('reporting_latency')

        # Get the list of values to generate the histogram:
        pipeline_trace = list(pipeline_query.values_list('reporting_latency', flat=True))

        fig.add_trace(go.Histogram(x=pipeline_trace,
                                   name=pipeline.name,
                                   xbins=dict(
                                       start=-10.0,
                                       end=120,
                                       size=0.25),
                                   ))

        # Update the statistics list with aggregated values. 
        aggregated_stats.append(pipeline_query.aggregate(med=Median('reporting_latency'),
                                           nfp=Percentile('reporting_latency', 0.95)))
        aggregated_stats[-1].update({'name': pipeline.name})
        if pipeline_query:
            aggregated_stats[-1].update({'min': pipeline_query.first().reporting_latency,
                                         'max': pipeline_query.last().reporting_latency,
                                         'min_gid': pipeline_query.first().graceid,
                                         'max_gid': pipeline_query.last().graceid,
                                         'count': pipeline_query.count(),
                                         })
        else:
            aggregated_stats[-1].update({'min': None,
                                         'max':None,
                                         'min_gid': None,
                                         'max_gid': None,
                                         'count': 0,
                                         })

    
    # The two histograms are drawn on top of another
    #fig.update_layout(barmode='stack',
    fig.update_layout(barmode='overlay',
            title={
                'text': plt_title,
                'xanchor': 'center',
                'x':0.5,},
            xaxis_title="Reporting Latency (s)",
            yaxis_title="Number of Production Events",
            legend_title="Pipeline",
            paper_bgcolor='rgba(0,0,0,0)')
    fig.update_traces(opacity=0.75)
    latency_plot_div = plot(fig, output_type='div')

    return {'latency_plot_div': latency_plot_div,
             'date_cutoff': date_cutoff,
             'pipeline_stats': aggregated_stats,}

