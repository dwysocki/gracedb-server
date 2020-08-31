import logging

from django import forms
from django.conf import settings
from django.http import HttpResponse, HttpResponseBadRequest
from django.shortcuts import render
from django.views.decorators.http import require_GET

from guardian.shortcuts import get_objects_for_user

from .forms import MainSearchForm
from .response import get_search_results_as_ligolw, event_datatables_response, \
    superevent_datatables_response

# Set up logger
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

            # Filter objects for user
            if query_type == 'S':
                view_perm = 'superevents.view_superevent'
            elif query_type == 'E':
                view_perm = 'events.view_event'
            else:
                return HttpResponseBadRequest(
                    "query_type should be 'S' or 'E'")
            objects = get_objects_for_user(request.user, view_perm, objects)

            # Get call from template for populating datatable
            if _format == 'F':
                if not request.is_ajax():
                    err_msg = ("You have tried to access an internal view "
                        "which is used for generating JavaScript search "
                        "results. Set 'results_format' to 'S' in your "
                        "query parameters.")
                    return HttpResponseBadRequest(err_msg)
                # datatable format
                if query_type == 'S':
                    # Superevent query
                    flex_func = superevent_datatables_response
                elif query_type == 'E':
                    # Event query
                    flex_func = event_datatables_response
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
        # Initial page with no query
        form = MainSearchForm()

    # Update context
    context['form'] = form

    return render(request, 'search/query.html', context=context)


@require_GET
def latest(request):

    # Set up context
    context = {}

    if "query" in request.GET:
        form = MainSearchForm(request.GET)
    else:
        form = MainSearchForm({'query': "", 'query_type': 'S'})

    # Hide get_neighbors widget
    form.fields['get_neighbors'].widget = forms.HiddenInput()

    if form.is_valid():
        objects = form.cleaned_data.get('query')
        query_type = form.cleaned_data.get('query_type')
        get_neighbors = form.cleaned_data.get('get_neighbors')

        # Determine object type and order by id (equivalent to
        # ordering by creation time and might be faster).
        # Also determine which permission is used for filtering
        # the full queryset for viewing
        if query_type == 'E':
            objects_key = 'events'
            view_perm = 'events.view_event'
        elif query_type == 'S':
            objects_key = 'superevents'
            view_perm = 'superevents.view_superevent'
        else:
            return HttpResponseBadRequest(
                "query_type should be 'S' or 'E'")

        # Filter objects for user and add to context, sorted in reverse
        # chronological order of submission
        objects = get_objects_for_user(request.user, view_perm, objects)
        context[objects_key] = \
            objects.order_by('-id')[:settings.LATEST_RESULTS_NUMBER]

    # Update form to have query and errors (if they exist)
    context['form'] = form

    return render(request, 'search/latest.html', context=context)
