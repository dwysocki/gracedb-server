from django import forms
from django.utils.translation import ugettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import escape

from events.models import Event
from events.query import parseQuery, filter_for_labels
from superevents.models import Superevent
from superevents.query import parseSupereventQuery

from pyparsing import ParseException

import os
import logging
logger = logging.getLogger(__name__)

htmlEntityStar = "&#9733;"
errorMarker = '<span style="color:red;">'+htmlEntityStar+'</span>'


class MainSearchForm(forms.Form):
    QUERY_TYPE_EVENT = 'E'
    QUERY_TYPE_SUPEREVENT = 'S'
    QUERY_TYPE_CHOICES = (
        (QUERY_TYPE_EVENT, 'Event'),
        (QUERY_TYPE_SUPEREVENT, 'Superevent'),
    )
    FORMAT_CHOICE_STANDARD = 'S'
    FORMAT_CHOICE_FLEXIGRID = 'F'
    FORMAT_CHOICE_LIGOLW = 'L'
    FORMAT_CHOICES = (
        ('S', 'standard'),
        ('F', 'flexigrid'),
        ('L', 'ligolw'),
    )

    query = forms.CharField(required=False, widget=forms.TextInput(
        attrs={'size': 60}))
    query_type = forms.ChoiceField(required=True,
        choices=QUERY_TYPE_CHOICES, label="Search for", initial='E')
    get_neighbors = forms.BooleanField(required=False,
        help_text="(Events only)")
    results_format = forms.ChoiceField(required=False, initial='S',
        choices=FORMAT_CHOICES, widget=forms.HiddenInput())

    def clean(self):
        # Do base class clean and just return if there are any errors already
        cleaned_data = super(MainSearchForm, self).clean()
        if self.errors:
            return cleaned_data

        # Get cleaned data
        query_string = self.cleaned_data.get('query')
        query_type = self.cleaned_data.get('query_type')

        # Set attributes based on object type
        # Add fields to use with select_related and prefetch_related
        # for optimization
        if query_type == 'S':
            model = Superevent
            parse_func = parseSupereventQuery
            s_rel = ['preferred_event__group', 'submitter']
            p_rel = ['labelling_set__label', 'labelling_set__creator']
        elif query_type == 'E':
            model = Event
            parse_func = parseQuery
            s_rel = ['group', 'pipeline', 'search', 'submitter']
            p_rel = ['labelling_set__label', 'labelling_set__creator']

        # Don't need to check anything else here, can expect data to be good
        # thanks to base class clean

        # Parse query and get resulting objects
        try:
            qs = model.objects.filter(parse_func(query_string)) \
                .select_related(*s_rel).prefetch_related(*p_rel)
            qs = filter_for_labels(qs, query_string).distinct()
            cleaned_data['query'] = qs
            return cleaned_data
        except ParseException as e:
            err = "Error: invalid query. (" + escape(e.pstr[:e.loc]) + \
                errorMarker + escape(e.pstr[e.loc:]) + ")"
            raise forms.ValidationError({'query': mark_safe(err)})
        except Exception as e:
            # What could this be and how can we handle it better? XXX
            logger.error('{t}: {e}'.format(t=str(type(e)), e=str(e)))
            raise forms.ValidationError(str(e))
