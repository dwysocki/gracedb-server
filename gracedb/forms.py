
from django import forms
from models import Event, User, Group

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

    graceidStart = forms.CharField(required=False)
    graceidEnd = forms.CharField(required=False)
    group = forms.ChoiceField(choices=groupChoices, required=False)
    type = forms.ChoiceField(choices=typeChoices, required=False)
    gpsStart = forms.IntegerField(min_value=0, required=False, label="GPS Start")
    gpsEnd = forms.IntegerField(min_value=0, required=False, label="GPS End")
    submitter = forms.ChoiceField(choices=submitterChoices, required=False)

