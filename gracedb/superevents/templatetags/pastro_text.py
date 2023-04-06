from django import template
from django.utils.safestring import mark_safe
import json
import pathlib

from events.models import Event

register = template.Library()
pastro_file_template = "{pipeline}.p_astro.json"
html_format = '<span style="font-weight: bold">p_{source}</span>= {value}'

@register.filter(is_safe=True)
def pastro_text(graceid):
    try:
        ev = Event.getByGraceid(graceid)
    except:
        return "Event {} does not exist".format(graceid)

    pastro_file_name = pastro_file_template.format(pipeline=ev.pipeline.name.lower())
    pastro_file = pathlib.Path(ev.datadir, pastro_file_name)

    try:
        with open(pastro_file, 'r') as f:
            data = json.load(f)
    except IOError:
        return "File {} not found or could not be opened".format(pastro_file_name)
    except json.JSONDecodeError:
        return "Could not json-decode file {}".format(pastro_file_name)

    return mark_safe(', '.join([html_format.format(source=i,
        value=round(data[i], 6)) for i in data]))

