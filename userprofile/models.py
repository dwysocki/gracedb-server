
from django.db import models

from gracedb.models import User, Label, Event


#class Notification(models.Model):
#    user = models.ForeignKey(User, null=False)
#    onLabel = models.ManyToManyField(Label, blank=True)
#    onTypeCreate = models.CharField(max_length=20, choices=TYPES, blank=True)
#    onTypeChange = models.CharField(max_length=20, choices=TYPES, blank=True)
#    email = models.EmailField()

class AnalysisType(models.Model):
    # XXX Event.analysisType should probably point to this.
    #  The choice list thing is obnoxious for notifications to track
    code = models.CharField(max_length=20, unique=True)
    display = models.CharField(max_length=20, unique=True)

    def __unicode__(self):
        return self.display

def populateAnalysisType():
    lastError = None
    for code, display in Event.ANALYSIS_TYPE_CHOICES:
        try:
            atype = AnalysisType(code=code, display=display)
            atype.save()
        except Exception, e:
            lastError = e
    if lastError is not None:
        raise lastError

class Contact(models.Model):
    user = models.ForeignKey(User, null=False)
    desc = models.CharField(max_length=20)
    email = models.EmailField()

    def __unicode__(self):
        return "%s: %s" % (self.user.name, self.desc)

class Trigger(models.Model):
    TYPES = ( ("create", "create"), ("change","change"), ("label","label") )
    user = models.ForeignKey(User, null=False)
    triggerType = models.CharField(max_length=20, choices=TYPES, blank=True)
    labels = models.ManyToManyField(Label, blank=True)
    atypes = models.ManyToManyField(AnalysisType, blank=True, verbose_name="Analysis Types")
    contacts = models.ManyToManyField(Contact, blank=True)

    def __unicode__(self):
        return ("%s: %s") % (
            self.user.name,
            self.userlessDisplay()
        )

    def userlessDisplay(self):
        return ("(%s) & (%s) -> %s") % (
            "|".join([a.display for a in self.atypes.all()]) or "any type",
            "|".join([a.name for a in self.labels.all()]) or "creating",
            ",".join([x.desc for x in self.contacts.all()])
        )
