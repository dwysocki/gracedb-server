from django.db import models
import datetime
import thread
import string

def lettersToInt( str ):
    """turn a string of letters into a base 26 number"""
    return reduce( lambda x, y: 26*x + y, map( string.lowercase.index, str ))

def intToLetters( i, str='' ):
    """convert a number into a string of lowercase letters"""
    if i == 0:
        return str or 'a'
    else:
        return intToLetters( i/26, string.lowercase[i%26] + str )

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    principal = models.CharField(max_length=100)
    dn = models.CharField(max_length=100)
    unixid = models.CharField(max_length=25)

    class Meta:
        ordering = ["name"]

    def __unicode__(self):
        return self.name


class Group(models.Model):
    name = models.CharField(max_length=20)
    managers = models.ManyToManyField(User)
    def __unicode__(self):
        return self.name


class Event(models.Model):
    ANALYSIS_TYPE_CHOICES = (
        ("LM",  "LowMass"),
        ("HM",  "HighMass"),
        ("GRB", "GRB"),
        ("RD",  "Ringdown"),
        ("OM",  "Omega"),
        ("Q",   "Q"),
        ("X",   "X"),
        ("CWB", "CWB"),
        ("MBTA", "MBTAOnline"),
    )
    submitter = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group)
    analysisType = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)

    # XXX Deprecated.  Only useful for old test data.
    # Remove this when it won't freak people out to lose
    # old date encoded uids.
    uid = models.CharField(max_length=20, unique=False, default="")

    class Meta:
        ordering = ["-id"]

    def graceid(self):
        if self.uid:
            return self.uid
        return "G%04d" % self.id

    def weburl(self):
        return "https://ldas-jobs.phys.uwm.edu/gracedb/data/%s" % self.graceid()

    def wikiurl(self):
        return "https://www.lsc-group.phys.uwm.edu/twiki/bin/view/Sandbox/%s" % self.graceid()

    def clusterurl(self):
        #return "pcdev1.phys.uwm.edu:/archive/gracedb/data/%s" % self.graceid()
        return "file://pcdev1.phys.uwm.edu/archive/gracedb/data/%s" % self.graceid()

    def ligoApproved(self):
        return self.approval_set.filter(approvingCollaboration='L').count()

    def virgoApproved(self):
        return self.approval_set.filter(approvingCollaboration='V').count()

    @classmethod
    def getByGraceid(cls, id):
        if not id: return None
        if id[0] == "G":
            return cls.objects.get(id=int(id[1:]))
        return cls.objects.get(uid=id)

class Approval(models.Model):
    COLLABORATION_CHOICES = ( ('L','LIGO'), ('V','Virgo'), )
    approver = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    approvedEvent = models.ForeignKey(Event, null=False)
    approvingCollaboration = models.CharField(max_length=1, choices=COLLABORATION_CHOICES)

