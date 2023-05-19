from django import template
from django.utils.safestring import mark_safe
import json
import pathlib

from events.models import Event

register = template.Library()

# Some formatting options:
pastro_file_template = "{pipeline}.p_astro.json"
html_format = '<span style="font-weight: bold">{prob}{source}</span>= {value}'


# Display the contents of a json file associated with a g-event. 
# data_file is either: 'p_astro' or 'em_bright'.
# optionally, append ',newline' to show each value on its own line
# optionally, append ',clean' to remove zero values from the file
# optionally, append ',showprob' to put a 'p_' in front of the quantity
@register.filter(is_safe=True)
def json_text(graceid, data_format):

    # Get the associated event. If not, return an error.
    try:
        ev = Event.getByGraceid(graceid)
    except:
        return "Event {} does not exist".format(graceid)

    # Format the remaining arguments:
    args = data_format.split(',')

    # the filename is the first value. get the name of the file, 
    # and format the input filename as needed:
    input_file = args[0].strip()
    if input_file == 'p_astro':
        json_file_name = pastro_file_template.format(pipeline=ev.pipeline.name.lower())
    elif input_file == 'em_bright':
        json_file_name = 'em_bright.json'
    else:
        return "Unrecognized input file."

    # See if we're doing newlines or clean or whatever.
    newline=clean=showprob=False
    if len(args) > 1:
        extra_args = [i.strip() for i in args[1:]]

        if 'newline' in extra_args: newline=True
        if 'clean' in extra_args: clean=True
        if 'showprob' in extra_args: showprob=True

    # define input file path and open it: 
    json_file = pathlib.Path(ev.datadir, json_file_name)

    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
    except IOError:
        return "File {} not found or could not be opened".format(json_file_name)
    except json.JSONDecodeError:
        return "Could not json-decode file {}".format(json_file_name)

    # Formatting stuff:
    if newline:
        join_char = '<br>'
    else:
        join_char = ', '

    # get rid of zero values:
    if clean:
        data = {x:y for x,y in data.items() if y != 0}

    if showprob:
        prob = 'p_'
    else:
        prob = ''

    return mark_safe(join_char.join([html_format.format(prob=prob, source=i,
        value=round(data[i], 6)) for i in data]))
