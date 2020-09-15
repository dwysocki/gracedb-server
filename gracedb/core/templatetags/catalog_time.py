from lal import gpstime
from django import template

register = template.Library()

@register.simple_tag
def lal_gps_to_utc(catalog_utc):
    t = gpstime.gps_to_utc(catalog_utc)
    s = t.strftime('%Y-%m-%d %H:%M:%S')
    return s
