
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape
from django.contrib.auth.models import User
from django.core.exceptions import FieldError
from django.forms import ModelForm
from django.db.models import Q

from .models import Event, Group, Label
from .models import Pipeline, Search, Signoff
from .query import parseQuery, filter_for_labels

from pyparsing import ParseException

htmlEntityStar = "&#9733;"
htmlEntityRightPointingHand = "&#9758;"
htmlEntitySkullAndCrossbones = "&#9760;"
htmlEntityTriangularBuller = "&#8227;"
htmlEntityRightArrow = "&rarr;"
errorMarker = '<span style="color:red;">'+htmlEntityStar+'</span>'

class GraceQueryField(forms.CharField):

    def do_filtering(self, query_string):
        """Method for getting queryset based on a query string"""
        qs = Event.objects.filter(parseQuery(query_string))
        qs = filter_for_labels(qs, query_string)
        return qs

    def clean(self, queryString):
        queryString = forms.CharField.clean(self, queryString)
        try:
            qs = self.do_filtering(queryString)
            return qs.distinct()
        except ParseException, e:
            err = "Error: " + escape(e.pstr[:e.loc]) + errorMarker + escape(e.pstr[e.loc:])
            raise forms.ValidationError(mark_safe(err))
        except FieldError, e:
            # XXX error message can be more polished than this
            err = "Error: " + str(e)
            raise forms.ValidationError(mark_safe(err))
        except Exception, e:
            # What could this be and how can we handle it better? XXX
            raise forms.ValidationError(str(e)+str(type(e)))

