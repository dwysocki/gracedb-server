from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.utils.html import escape
from django.views.decorators.http import require_POST, require_GET

from .forms import MainSearchForm
from .utils import get_search_results_as_ligolw
from core.http import check_and_serve_file

from events.view_utils import flexigridResponse as events_flex
from superevents.search_flex import flexigridResponse as superevents_flex

import os
import logging
logger = logging.getLogger(__name__)


@require_GET
def search(request):

    # Set up context
    context = {}

    if "query" in request.GET:
        form = MainSearchForm(request.GET)
        raw_query = request.GET['query']

        if form.is_valid():
            objects = form.cleaned_data.get('query')
            query_type = form.cleaned_data.get('query_type')
            get_neighbors = form.cleaned_data.get('get_neighbors')
            _format = form.cleaned_data.get('results_format')

            # TODO:
            # Filter objects for user

            # Get call from template for populating flexigrid table
            if _format == 'F':
                # Flex format
                if query_type == 'S':
                    # Superevent query
                    flex_func = superevents_flex
                elif query_type == 'E':
                    # Event query
                    flex_func = events_flex
                else:
                    # TODO: raise error
                    pass 
                return flex_func(request, objects)
            elif _format == 'L':
                # LIGOLW format
                return get_search_results_as_ligolw(objects)

            context['title'] = "Query results"
            context['objs'] = objects
            context['raw_query'] = raw_query
            context['query_type'] = query_type
            context['get_neighbors'] = get_neighbors
    else:
        form = MainSearchForm()

    # Update context
    context['form'] = form

    return render(request, 'search/query.html', context=context)
