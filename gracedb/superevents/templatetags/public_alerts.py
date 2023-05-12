from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe

from core.urls import build_absolute_uri

register = template.Library()

o3_deepomegascan_fmt = '''
<a href="https://ldas-jobs.ligo-la.caltech.edu/~detchar/dqr/events/{sid}/L1deepomegascan/" target="_blank">&Omega; L1</a><br/>
<a href="https://ldas-jobs.ligo-wa.caltech.edu/~detchar/dqr/events/{sid}/H1deepomegascan/" target="_blank">&Omega; H1</a>
'''

o4_ifo_wscan_link = '<a href="{img_uri}" target="_blank">&Omega; {ifo}</a>'

# In O3, DQR produced a "deepomegascan" that's linked on caltech's cluser,
# but in O4 the quickest way to get those images is to link to the omegascan
# that's already on gracedb. this function will produce an HTML formatted string 
# that gets returned and pasted in the table.
@register.filter(is_safe=True)
def omegascan_links(superevent, run):
    w_html = ''
    if run == 'O3':
        return mark_safe(o3_deepomegascan_fmt.format(sid=superevent.superevent_id))
    else:
        link_list = []
        for filename in set(superevent.log_set.filter(filename__contains='omegascan').values_list('filename', flat=True)):
            # get the absolute uri for the file:
            file_url = build_absolute_uri(reverse('api:default:superevents:superevent-file-detail',
                           args=[superevent.superevent_id, filename]))

            # try and get the ifo name. it's assumed that it's {ifo}_omegascan.png
            ifo = filename.split('_')[0]

            # Construct the link, add it to the list
            link_list.append(o4_ifo_wscan_link.format(img_uri=file_url, ifo=ifo))
        return mark_safe('<br/>'.join(link_list))

    return mark_safe(w_html)
