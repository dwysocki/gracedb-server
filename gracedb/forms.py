
from django import forms
from models import Event, User, Group, Label

from query import parseQuery, ParseException

class GraceQueryField(forms.CharField):
    def clean(self, queryString):
        from django.db.models import Q
        queryString = forms.CharField.clean(self, queryString)
        try:
            return parseQuery(queryString)
        except ParseException, e:
            raise forms.ValidationError("Error near (*): "+ e.markInputline("(*)"))
        except Exception, e:
            # What could this be and how can we handle it better? XXX
            raise forms.ValidationError(str(e))

class SimpleSearchForm(forms.Form):
    query = GraceQueryField(required=True, widget=forms.TextInput(attrs={'size':60}))


class CreateEventForm(forms.Form):
    groupChoices = [("","")]+[(g.name, g.name) for g in Group.objects.all()]
    typeChoices= [("","")]+list(Event.ANALYSIS_TYPE_CHOICES)

    eventFile  = forms.FileField()
    group = forms.ChoiceField(groupChoices)
    type = forms.ChoiceField(choices=typeChoices)


class EventSearchForm(forms.Form):
    groupChoices = [("","")]+[(g.name, g.name) for g in Group.objects.all()]

    typeChoices= [("","")]+list(Event.ANALYSIS_TYPE_CHOICES)

    submitterIds = Event.objects.values_list('submitter',flat=True).distinct()
    submitterList = User.objects.filter(id__in=submitterIds).order_by('name')
    submitterChoices = [("","")]+ [ (u.id, u.name) for u in submitterList]

    labelChoices = [ ("hi%d"%n,"bye%d"%n) for n in [1,2,3]]
    labelChoices = [ (label.id, label.name) for label in Label.objects.all() ]

    graceidStart = forms.CharField(required=False)
    graceidEnd = forms.CharField(required=False)
    group = forms.ChoiceField(choices=groupChoices, required=False)
    type = forms.ChoiceField(choices=typeChoices, required=False)
    gpsStart = forms.IntegerField(min_value=0, required=False, label="GPS Start")
    gpsEnd = forms.IntegerField(min_value=0, required=False, label="GPS End")
    submitter = forms.ChoiceField(choices=submitterChoices, required=False)

    labels = forms.MultipleChoiceField(choices=labelChoices, required=False)
