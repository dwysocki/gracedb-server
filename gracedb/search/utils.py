from django.http import HttpResponse, HttpResponseServerError, \
    HttpResponseBadRequest

from events.view_utils import assembleLigoLw

from glue.ligolw import utils


RESULTS_LIMIT = 1000


def get_search_results_as_ligolw(objects):

    if objects.count() > RESULTS_LIMIT:
        return HttpResponseBadRequest(("Sorry -- no more than {0} events "
            "currently allowed").format(RESULTS_LIMIT))

    # Only valid for events, not superevents
    if objects.model.__name__ == "Superevent":
        return HttpResponseBadRequest("LigoLw tables are not available "
            "for superevents")

    try:
        xmldoc = assembleLigoLw(objects)
    except IOError as e:
        msg = ("At least one of the query results has no associated coinc.xml "
            "file. LigoLw tables are only available for queries which return "
            "only coinc inspiral events. Please try your query again.")
        return HttpResponseBadRequest(msg)
    except Exception as e:
        msg = ("An error occured while trying to compile LigoLw "
            "results: {0}").format(e)
        return HttpResponseServerError(msg)

    response = HttpResponse(content_type='application/xml')
    response['Content-Disposition'] = 'attachment; filename=gracedb-query.xml'
    utils.write_fileobj(xmldoc, response)
    return response 
