from __future__ import absolute_import
from pyparsing import ParseException

from django import forms
from django.core.exceptions import FieldError
from django.utils.safestring import mark_safe
from django.utils.html import escape

from search.query.events import parseQuery
from search.query.labels import filter_for_labels
from events.models import Event

htmlEntityStar = "&#9733;"
errorMarker = '<span style="color:red;">'+htmlEntityStar+'</span>'
si_prefixes = ['si.', 'singleinspiral.']


# NOTE: this is only used in SimpleSearchForm and should be removed
# when that form is removed.
class GraceQueryField(forms.CharField):

    def do_filtering(self, query_string):
        """Method for getting queryset based on a query string"""
        qs = Event.objects.filter(parseQuery(query_string))
        qs = filter_for_labels(qs, query_string)
        # Hack to remove duplicate singleinspiral results:
        if any(s in query_string for s in si_prefixes):
           qs = qs.distinct()
        return qs

    def clean(self, queryString):
        queryString = forms.CharField.clean(self, queryString)
        try:
            qs = self.do_filtering(queryString)
            return qs
        except ParseException as e:
            err = "Error: " + escape(e.pstr[:e.loc]) + errorMarker + escape(e.pstr[e.loc:])
            raise forms.ValidationError(mark_safe(err))
        except FieldError as e:
            # XXX error message can be more polished than this
            err = "Error: " + str(e)
            raise forms.ValidationError(mark_safe(err))
        except Exception as e:
            # What could this be and how can we handle it better? XXX
            raise forms.ValidationError(str(e)+str(type(e)))

