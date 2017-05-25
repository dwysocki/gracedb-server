
from django import forms
from django.utils.safestring import mark_safe
from django.utils.html import escape
from models import Event, Group, Label
from models import Pipeline, Search, Signoff
from django.contrib.auth.models import User
from django.core.exceptions import FieldError
from django.forms import ModelForm

from query import parseQuery, filter_for_labels
from pyparsing import ParseException

htmlEntityStar = "&#9733;"
htmlEntityRightPointingHand = "&#9758;"
htmlEntitySkullAndCrossbones = "&#9760;"
htmlEntityTriangularBuller = "&#8227;"
htmlEntityRightArrow = "&rarr;"

errorMarker = '<span style="color:red;">'+htmlEntityStar+'</span>'

class GraceQueryField(forms.CharField):
    def clean(self, queryString):
        from django.db.models import Q
        queryString = forms.CharField.clean(self, queryString)
        try:
            #return Event.objects.filter(parseQuery(queryString)).distinct()
            qs = Event.objects.filter(parseQuery(queryString))
            qs = filter_for_labels(qs, queryString)
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

class SimpleSearchForm(forms.Form):
    query = GraceQueryField(required=False, widget=forms.TextInput(attrs={'size':60})) 
    get_neighbors = forms.BooleanField(required=False)

class CreateEventForm(forms.Form):
    groupChoices = [("","")]+[(g.name, g.name) for g in Group.objects.all()]
    #typeChoices= [("","")]+list(Event.ANALYSIS_TYPE_CHOICES)
    pipelineChoices = [("","")]+[(p.name, p.name) for p in Pipeline.objects.all()]
    searchChoices = [("","")]+[(s.name, s.name) for s in Search.objects.all()]

    eventFile = forms.FileField()
    group = forms.ChoiceField(groupChoices)
    pipeline = forms.ChoiceField(pipelineChoices)
    search = forms.ChoiceField(searchChoices, required=False)
    # List of labels as a comma-separated string
    labels = forms.CharField(required=False)
    #type = forms.ChoiceField(choices=typeChoices)

    # Offline boolean. required=False means that if the user
    # doesn't provide a value, we use the default defined in models.py.
    # This ensures backwards-compatibility for client versions which
    # don't specify this parameter.
    offline = forms.BooleanField(required=False)

class EventSearchForm(forms.Form):
    groupChoices = [("","")]+[(g.name, g.name) for g in Group.objects.all()]
    pipelineChoices = [("","")]+[(p.name, p.name) for p in Pipeline.objects.all()]
    searchChoices = [("","")]+[(s.name, s.name) for s in Search.objects.all()]

    #typeChoices= [("","")]+list(Event.ANALYSIS_TYPE_CHOICES)

    submitterIds = Event.objects.values_list('submitter',flat=True).distinct()
    submitterList = User.objects.filter(id__in=submitterIds).order_by('last_name', 'first_name')
    submitterChoices = [("","")]+ \
            [ (u.id, u"{0} {1}".format(u.first_name, u.last_name)) for u in submitterList]

    labelChoices = [ ("hi%d"%n,"bye%d"%n) for n in [1,2,3]]
    labelChoices = [ (label.id, label.name) for label in Label.objects.all() ]

    graceidStart = forms.CharField(required=False)
    graceidEnd = forms.CharField(required=False)
    group = forms.ChoiceField(choices=groupChoices, required=False)
    #type = forms.ChoiceField(choices=typeChoices, required=False)
    pipeline = forms.ChoiceField(choices=pipelineChoices, required=False)
    search = forms.ChoiceField(choices=searchChoices, required=False)
    gpsStart = forms.IntegerField(min_value=0, required=False, label="GPS Start")
    gpsEnd = forms.IntegerField(min_value=0, required=False, label="GPS End")
    submitter = forms.ChoiceField(choices=submitterChoices, required=False)

    labels = forms.MultipleChoiceField(choices=labelChoices, required=False)
    get_neighbors = forms.BooleanField(required=False)

class SignoffForm(ModelForm):
    class Meta:
        model = Signoff
        fields = [ 'status', 'comment' ] 
