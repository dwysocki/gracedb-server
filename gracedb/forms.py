
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

    uidStart = forms.CharField(required=False)
    uidEnd = forms.CharField(required=False)
    group = forms.ChoiceField(choices=groupChoices, required=False)
    type = forms.ChoiceField(choices=typeChoices, required=False)
    submitter = forms.ChoiceField(choices=submitterChoices, required=False)

    ligoApproved = forms.BooleanField(initial=False, required=False, label="LIGO Approved Only")
    virgoApproved = forms.BooleanField(initial=False, required=False, label="Virgo Approved Only")

