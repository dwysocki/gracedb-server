from django.http import HttpResponse
from django.template import RequestContext
from django.shortcuts import render_to_response

from gracedb.gracedb.models import Event

from django.db import connection, transaction

import gviz_api
from datetime import datetime

def index(request):

    # foo = Event.objects.raw("select date_format(date, '%Y-%m') as month, sum(quantity) as hours from hourentries group by date_format(date, '%Y-%m') order by date;")

#   q = "SELECT * from gracedb_event LIMIT 10"
#   q = "SELECT date_format(created, '%%Y-%%m') as month, COUNT(*) AS total FROM gracedb_event GROUP BY date_format(created, '%%Y-%%m') order by created"

#   cursor = connection.cursor()
#   cursor.execute(q)

#   desc = cursor.description
#   foo = [ dict(zip([col[0] for col in desc], row))
#                       for row in cursor.fetchall()
#                           ]
    foo = "I AM THE FOO"

    return render_to_response(
            'gracedb/datas.html',
            {'thing' : str(foo)},
            context_instance=RequestContext(request))

def source(request):
    tq = request.GET.get('tq',"")
    tqx = request.GET.get('tqx',"")

    atypes = ["OM", "LM"]
    atypes = [shortname for (shortname, _) in Event.ANALYSIS_TYPE_CHOICES]

    description = [ ("Year", "string"), ]

    buffy = []

    things = dict(zip(atypes, [{}]*len(atypes)))
    things = {}
    dates = set()
    for t in atypes:
        description.append( (t, "number") )
        q = "SELECT date_format(created, '%%Y-%%m') as month, COUNT(*) AS total FROM gracedb_event WHERE analysisType = %s GROUP BY date_format(created, '%%Y-%%m')"
        cursor = connection.cursor()
        cursor.execute(q, [t])
        d = {}
        for row in cursor.fetchall():
            n = int(row[1])
            d[str(row[0])] = n
            dates.update([row[0]])
            buffy.append(row)
        things[t] = d
        cursor.close()
# THINGS
#  {'OM': {u'2010-01': 37, u'2011-08': 1, u'2010-08': 5193, u'2010-07': 1085, u'2011-11': 1, u'2010-04': 433, u'2011-12': 3, u'2009-07': 10, u'2009-06': 5, u'2010-03': 528, u'2010-02': 307, u'2009-10': 109, u'2009-11': 281, u'2009-12': 1, u'2010-06': 221, u'2010-09': 4018, u'2010-05': 519, u'2012-01': 3, u'2010-10': 1871, u'2009-08': 149}, 'LM': {u'2010-01': 37, u'2011-08': 1, u'2010-08': 5193, u'2010-07': 1085, u'2011-11': 1, u'2010-04': 433, u'2011-12': 3, u'2009-07': 10, u'2009-06': 5, u'2010-03': 528, u'2010-02': 307, u'2009-10': 109, u'2009-11': 281, u'2009-12': 1, u'2010-06': 221, u'2010-09': 4018, u'2010-05': 519, u'2012-01': 3, u'2010-10': 1871, u'2009-08': 149}}

# BUFFY
# [(u'2009-06', 1L), (u'2009-07', 69L), (u'2009-08', 149L), (u'2009-10', 109L), (u'2009-11', 281L), (u'2009-12', 243L), (u'2010-01', 37L), (u'2010-02', 307L), (u'2010-03', 528L), (u'2010-04', 433L), (u'2010-05', 519L), (u'2010-06', 221L), (u'2010-07', 262L), (u'2010-08', 902L), (u'2010-09', 962L), (u'2010-10', 318L), (u'2011-11', 4L), (u'2009-06', 5L), (u'2009-07', 10L), (u'2009-12', 1L), (u'2010-07', 1085L), (u'2010-08', 5193L), (u'2010-09', 4018L), (u'2010-10', 1871L), (u'2011-08', 1L), (u'2011-11', 1L), (u'2011-12', 3L), (u'2012-01', 3L)]

    data_table = gviz_api.DataTable(description)

    data = [
        ["2011-01", 33, 44],
        ["2011-02", 43, 24],
        ["2011-03", 38, 34],
    ]

    dates = list(dates)
    dates.sort()

    data = []
    for date in dates:
        row = [date]
        for t in atypes:
            try:
                row.append(things[t][date])
            except:
                row.append(0)
        data.append(row)

    data_table.LoadData(data)
    #return HttpResponse(str(dates))
    #return HttpResponse(str(data))
    return HttpResponse(data_table.ToResponse(tqx=tqx))

def sourcea(request):

#   description = [
#       ("year", "string", "year"),
#       ("first", "number", "first"),
#       ("second", "number", "second"),
#   ]
#   data_table = gviz_api.DataTable(description)
#   data_table.LoadData([
#       [2001, 1,3],
#       [2002, 2,4],
#       [2003, 3,5],
#   ])
#   return HttpResponse(data_table.ToResponse(columns_order=("year", "first", "second")))

    tq = request.GET.get('tq',"")
    tqx = request.GET.get('tqx',"")

    description = {
        "month": ("date", "Month"),
        "type": ("string", "Type"),
        "total": ("number", "Total Events"),
    }
    data_table = gviz_api.DataTable(description)

    q = "SELECT date_format(created, '%%Y-%%m') as month, analysisType, COUNT(*) AS total FROM gracedb_event GROUP BY date_format(created, '%%Y-%%m'),analysisType order by created"

    cursor = connection.cursor()
    cursor.execute(q)

    def blarg(d):
        year, month = d.split('-')
        return datetime(int(year), int(month), 1)

#   for row in cursor.fetchall():
#       data_table.addRow([blarg(row[0]), row[1], row[2]])
    data = [
        #{ "month": row[0], "total": row[1] } for row in cursor.fetchall()
        { "month": blarg(row[0]), "type": row[1], "total": row[2] } for row in cursor.fetchall()
    ]
    data_table.LoadData(data)

    return HttpResponse(data_table.ToResponse(columns_order=("month", "type", "total"), tqx=tqx))
    return HttpResponse(data_table.ToResponse(tqx=tqx))

def sourcex(request):

    description = {"name": ("string", "Name"),
                   "salary": ("number", "Salary"),
                   "full_time": ("boolean", "Full Time Employee")}
    data = [{"name": "Mike", "salary": (10000, "$10,000"), "full_time": True},
            {"name": "Jim", "salary": (800, "$800"), "full_time": False},
            {"name": "Alice", "salary": (12500, "$12,500"), "full_time": True},
            {"name": "Bob", "salary": (7000, "$7,000"), "full_time": True}]

    data_table = gviz_api.DataTable(description)
    data_table.LoadData(data)
    #print "Content-type: text/plain"
    #print
    #print data_table.ToJSonResponse(columns_order=("name", "salary", "full_time"),
    #                                order_by="salary")
    return HttpResponse(data_table.ToResponse(columns_order=("name", "salary", "full_time"), order_by="salary", tqx=tqx))

