from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape
from .models import Event, Group, Label
from .models import Pipeline, Search, Signoff
from django.contrib.auth.models import User
from django.core.exceptions import FieldError
from django.forms import ModelForm

from .fields import GraceQueryField
from .query import parseQuery, filter_for_labels
from pyparsing import ParseException

htmlEntityStar = "&#9733;"
htmlEntityRightPointingHand = "&#9758;"
htmlEntitySkullAndCrossbones = "&#9760;"
htmlEntityTriangularBuller = "&#8227;"
htmlEntityRightArrow = "&rarr;"

errorMarker = '<span style="color:red;">'+htmlEntityStar+'</span>'

class SimpleSearchForm(forms.Form):
    query = GraceQueryField(required=False, widget=forms.TextInput(attrs={'size':60})) 
    get_neighbors = forms.BooleanField(required=False)

class CreateEventForm(forms.Form):
    eventFile = forms.FileField()
    group = forms.ModelChoiceField(queryset=Group.objects.all(), to_field_name='name')
    pipeline = forms.ModelChoiceField(queryset=Pipeline.objects.all(), to_field_name='name')
    search = forms.ModelChoiceField(queryset=Search.objects.all(), to_field_name='name',
        required=False)
    # List of labels as a comma-separated string
    labels = forms.ModelMultipleChoiceField(queryset=Label.objects.all(),
        required=False, to_field_name='name')

    # Offline boolean. required=False means that if the user
    # doesn't provide a value, we use the default defined in models.py.
    # This ensures backwards-compatibility for client versions which
    # don't specify this parameter.
    offline = forms.BooleanField(required=False)

class EventSearchForm(forms.Form):

    graceidStart = forms.CharField(required=False)
    graceidEnd = forms.CharField(required=False)
    group = forms.ModelChoiceField(queryset=Group.objects.all(),
        required=False)
    pipeline = forms.ModelChoiceField(queryset=Pipeline.objects.all(),
        required=False)
    search = forms.ModelChoiceField(queryset=Search.objects.all(),
        required=False)
    gpsStart = forms.IntegerField(min_value=0, required=False, label="GPS Start")
    gpsEnd = forms.IntegerField(min_value=0, required=False, label="GPS End")
    submitter = forms.ModelChoiceField(required=False,
        queryset=User.objects.exclude(event__isnull=True) \
        .order_by('last_name', 'first_name'))

    labels = forms.ModelMultipleChoiceField(queryset=Label.objects.all(),
        required=False)
    get_neighbors = forms.BooleanField(required=False)

    offline = forms.NullBooleanField(
        required=False,
        help_text=("Select \"Unknown\" to search for both online and offline "
            "events.")
    )

class SignoffForm(ModelForm):
    class Meta:
        model = Signoff
        fields = [ 'status', 'comment' ] 
