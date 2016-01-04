
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden
#from django.contrib.sites.models import Site
from django.utils.html import strip_tags

from models import Event, EventLog
from forms import SimpleSearchForm

from utils.vfile import VersionedFile

from view_logic import create_label, _createLog
from view_utils import assembleLigoLw
from permission_utils import filter_events_for_user, user_has_perm, internal_user_required

import os
from django.conf import settings

# XXX This should be configurable / moddable or something
MAX_QUERY_RESULTS = 1000

import json

@internal_user_required
def cli_search(request):
    assert request.user
    form = SimpleSearchForm(request.POST)
    if form.is_valid():
        objects = form.cleaned_data['query']
        objects = filter_events_for_user(objects, request.user, 'view') 

        if 'ligolw' in request.POST or 'ligolw' in request.GET:
            from glue.ligolw import utils
            if objects.count() > 1000:
                return HttpResponseBadRequest("Too many events.")
            xmldoc = assembleLigoLw(objects)
            response = HttpResponse(content_type='application/xml')
            response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
            utils.write_fileobj(xmldoc, response)
            response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
            return response

        accessFun = {
            "labels" : lambda e: \
                ",".join([labelling.label.name for labelling in e.labelling_set.all()]),
            "pipeline" : lambda e: e.pipeline.name,
            #"search"  : lambda e: e.search.name or "",
            "search"  : lambda e: e.search.name if e.search else "",
            "gpstime" : lambda e: str(e.gpstime) or "",
            "created" : lambda e: e.created.isoformat(),
            "dataurl" : lambda e: e.weburl(),
            "graceid" : lambda e: e.graceid(),
            "group" : lambda e: e.group.name,
        }
        defaultAccess = lambda e, a: str(getattr(e,a,None) or "")

        defaultColumns = "graceid,labels,group,pipeline,search,far,gpstime,created,dataurl"
        columns = request.POST.get('columns')
        if not columns:
            columns = defaultColumns
        columns = columns.split(',')

        header = "#" + "\t".join(columns)
        outTable = [header]
        for e in objects:
            row = [ accessFun.get(column, lambda e: defaultAccess(e,column))(e) for column in columns ]
            outTable.append("\t".join(row))
        d = {'output': "\n".join(outTable)}
    else:
        d = {'error': ""}
        for key in form.errors:
            d['error'] += "%s: %s\n" % (key, strip_tags(form.errors[key]))
    response = HttpResponse(content_type='application/javascript')
    msg = json.dumps(d)
    response['Content-length'] = len(msg)
    response.write(msg)
    response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
    return response

@internal_user_required
def cli_label(request):
    graceid = request.POST.get('graceid')
    labelName = request.POST.get('label')

    doxmpp = request.POST.get('alert') == "True"
    event = graceid and Event.getByGraceid(graceid)

    if not user_has_perm(request.user, 'change', event):
        return HttpResponseForbidden()

    d = create_label(event, request, labelName, doXMPP=doxmpp)

    msg = str(d)
    response = HttpResponse(content_type='application/json')
    response.write(msg)
    response['Content-length'] = len(msg)

    response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
    return response

@internal_user_required
def cli_tag(request):
    raise Exception("tag is not implemented.  Maybe you're thinking of 'label'?")
    graceid = request.POST.get('graceid')
    tagname = request.POST.get('tag')

    event = graceid and Event.getByGraceid(graceid)

    if not user_has_perm(request.user, 'change', event):
        return HttpResponseForbidden()

    event.add_tag(tagname)
    msg = str({})
    response = HttpResponse(content_type='application/json')
    response.write(msg)
    response['Content-length'] = len(msg)

    response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
    return response

@internal_user_required
def ping(request):
    #ack = "(%s) " % Site.objects.get_current()
    ack = "(%s/%s) " % (request.META['SERVER_NAME'], settings.CONFIG_NAME)
    ack += request.POST.get('ack', None) or request.GET.get('ack','ACK')

    from templatetags.timeutil import utc
    if 'cli_version' in request.POST:
        response = HttpResponse(content_type='application/json')
        d = {'output': ack}
        if 'extended' in request.POST:
            latest = Event.objects.order_by("-id")[0]
            if user_has_perm(request.user, 'view', latest):
                d['latest'] = {}
                d['latest']['id'] = latest.graceid()
                d['latest']['created'] = str(utc(latest.created))
        d =  json.dumps(d)
        response.write(d)
        response['Content-length'] = len(d)
    else:
        # Old client
        response = HttpResponse(content_type='text/plain')
        response.write(ack)
        response['Content-length'] = len(ack)
    response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
    return response

@internal_user_required
def upload(request):
    graceid = request.POST.get('graceid', None)
    comment = request.POST.get('comment', None)
    uploadedfile = request.FILES['upload']

    try:
        event = graceid and Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        event = None

    if not event:
        return HttpResponseBadRequest("Event does not exist.")
    if not user_has_perm(request.user, 'change', event):
        return HttpResponseForbidden()

    if 'cli_version' in request.POST:
        response = _createLog(request, graceid, comment, uploadedfile)
        response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
        return response
    # else: old, old client
    response = HttpResponse(content_type='text/plain')
    # uploadedFile.{name/chunks()}
    try:
        event = graceid and Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        event = None
    if not (comment and uploadedfile and graceid):
        msg = "ERROR: missing arg(s)"
    elif not event:
        msg = "ERROR: Event '%s' does not exist" % graceid
    else:
        #event issuer comment
        # XXX Note:  filename or comment oughta have a version
        log = EventLog(event=event,
                       issuer=request.user,
                       filename=uploadedfile.name,
                       comment=comment)
        try:
            log.save()
            msg = "OK"
        except:
            msg = "ERROR: problem creating log entry"
        try:
            # XXX
            # Badnesses:
            #   Same hardcoded path in multiple places.
            fname = os.path.join(event.datadir(), uploadedfile.name)
            f = VersionedFile(fname, 'w')
            for chunk in uploadedfile.chunks():
                f.write(chunk)
            f.close()
            log.file_version = f.version
            log.save()
        except Exception, e:
            msg = "ERROR: could not save file " + fname + " " + str(e)
            log.delete()
    response = HttpResponse(content_type='text/plain')
    response.write(msg)
    response['Content-length'] = len(msg)
    response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
    return response

@internal_user_required
def log(request):
    message = request.POST.get('message')
    graceid = request.POST.get('graceid')

    try:
        event = graceid and Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        event = None

    if not event:
        return HttpResponseBadRequest("Event does not exist.")
    if not user_has_perm(request.user, 'change', event):
        return HttpResponseForbidden()

    if 'cli_version' in request.POST:
        response = _createLog(request, graceid, message)
        response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
        return response

    # old, old client only
    response = HttpResponse(content_type='text/plain')
    try:
        event = graceid and Event.getByGraceid(graceid)
    except Event.DoesNotExist:
        event = None

    if not (message and graceid):
        msg = "ERROR: missing arg(s)"
    elif not event:
        msg = "ERROR: Event '%s' does not exist" % graceid
    else:
        #event issuer comment
        log = EventLog(event=event, issuer=request.user, comment=message)
        try:
            log.save()
            msg = "OK"
        except:
            msg = "ERROR: problem creating log entry"

    response = HttpResponse(content_type='text/plain')
    response.write(msg)
    response['Content-length'] = len(msg)
    response['Warning'] = '299 - "The /cli URLs are deprecated and will be removed on March 8, 2016." "2016-01-12:10:30:00.000"'
    return response
