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

class Genid:
    # XXX dear heaven this is awful.
    def __init__(self):
        self.lastCalledDate = datetime.datetime.now().date()

        # XXX Find latest suffix from Event table
        self.next = 0
        self.lock = thread.allocate_lock()
        prefix = self.lastCalledDate.strftime('%y%m%d')
        plen = len(prefix)
        analyses = Event.objects.filter(uid__contains=prefix)
        if len(analyses) >0:
            self.next = 1 + max([lettersToInt(a.uid[plen:]) for a in analyses])
    
    def __call__(self):
        self.lock.acquire()
        today = datetime.datetime.now().date()
        assert (today >= self.lastCalledDate)
        if today != self.lastCalledDate:
            self.next = 0
            self.lastCalledDate = today
        prefix = datetime.datetime.now().strftime('%y%m%d')
        rv = prefix + intToLetters(self.next)
        self.next += 1
        self.lock.release()
        return rv

# XXX Yarg.
_genid = None
def genid():
    global _genid
    if not _genid: _genid = Genid()
    return _genid()



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
        ("MBTA", "MBTA Online"),
    )
    uid = models.CharField(max_length=20, unique=True, default=genid)
    submitter = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    group = models.ForeignKey(Group)
    analysisType = models.CharField(max_length=20, choices=ANALYSIS_TYPE_CHOICES)
    def weburl(self):
        return "https://ldas-jobs.phys.uwm.edu/gracedb/data/%s" % self.uid

    def wikiurl(self):
        return "https://www.lsc-group.phys.uwm.edu/twiki/bin/view/Sandbox/%s" % self.uid

    def clusterurl(self):
        #return "pcdev1.phys.uwm.edu:/archive/gracedb/data/%s" % self.uid
        return "file://pcdev1.phys.uwm.edu/archive/gracedb/data/%s" % self.uid

    def ligoApproved(self):
        return self.approval_set.filter(approvingCollaboration='L').count()

    def virgoApproved(self):
        return self.approval_set.filter(approvingCollaboration='V').count()

class Approval(models.Model):
    COLLABORATION_CHOICES = ( ('L','LIGO'), ('V','Virgo'), )
    approver = models.ForeignKey(User)
    created = models.DateTimeField(auto_now_add=True)
    approvedEvent = models.ForeignKey(Event, null=False)
    approvingCollaboration = models.CharField(max_length=1, choices=COLLABORATION_CHOICES)

