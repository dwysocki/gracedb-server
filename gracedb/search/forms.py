from __future__ import absolute_import
import os
import logging
from pyparsing import ParseException

from django import forms
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from django.utils.html import escape

from events.models import Event
from superevents.models import Superevent
from .fields import GraceQueryField
from .query.events import parseQuery
from .query.superevents import parseSupereventQuery
from .query.labels import filter_for_labels

# Set up logger
logger = logging.getLogger(__name__)

htmlEntityStar = "&#9733;"
errorMarker = '<span style="color:red;">'+htmlEntityStar+'</span>'

# Helpful status messages:
created_vs_t0 = 'Invalid query. Hint: date queries on the created: field take the form YYYY-MM-DD .. ' \
        'YYYY-MM-DD. Date queries with gpstime are supported using the t_0: field'

si_prefixes = ['si.', 'singleinspiral.']


# Helper function to capture superevent created vs t_0 gpstime queries 
# and return it to the user:
def se_gpstime_parseerror(err):
    if "ParseResults" in str(err) and 'miltime' in str(err):
        return created_vs_t0
    else:
        return err

class MainSearchForm(forms.Form):
    QUERY_TYPE_EVENT = 'E'
    QUERY_TYPE_SUPEREVENT = 'S'
    QUERY_TYPE_CHOICES = (
        (QUERY_TYPE_EVENT, 'Events'),
        (QUERY_TYPE_SUPEREVENT, 'Superevents'),
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
        attrs={'size': 40,
               'class': 'form-control',
               'placeholder': 'Enter query'
               }
        ))
    query_type = forms.ChoiceField(required=True,
        choices=QUERY_TYPE_CHOICES, label="Search for", initial='S',
        widget=forms.Select(
            attrs={'class': 'form-control',
                   'style': 'width:fit-content;'}
        ))
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
            qs = filter_for_labels(qs, query_string)
            # Hack to remove duplicate singleinspiral results:
            if any(s in query_string for s in si_prefixes):
               qs = qs.distinct()
            cleaned_data['query'] = qs
            return cleaned_data
        except ParseException as e:
            err = "Error: invalid query. (" + escape(e.pstr[:e.loc]) + \
                errorMarker + escape(e.pstr[e.loc:]) + ")"
            raise forms.ValidationError({'query': mark_safe(err)})
        except KeyError as e:
            raise forms.ValidationError(se_gpstime_parseerror(e))
        except Exception as e:
            # What could this be and how can we handle it better? XXX
            logger.error('{t}: {e}'.format(t=str(type(e)), e=str(e)))
            raise forms.ValidationError({'query': str(e)})


# NOTE: this form is from the old events-only search, but is used in several
# other places.  We should remove it once the events rework is done.
class SimpleSearchForm(forms.Form):
    query = GraceQueryField(required=False,
        widget=forms.TextInput(attrs={'size': 60}))
    get_neighbors = forms.BooleanField(required=False)
