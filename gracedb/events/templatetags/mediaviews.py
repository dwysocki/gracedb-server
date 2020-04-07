from django import template
from django.conf import settings

from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

from events.models import Event, Tag
from gracedb.core.urls import build_absolute_uri
import os

register = template.Library()

# Define some stuff:
blessed_tag_priority_order = [
    'analyst_comments',
    'psd',
    'data_quality',
    'sky_loc',
    'background',
    'ext_coinc',
    'strain',
    'tfplots',
    'sig_info',
    'audio',
]

img_file_extensions = ['.png','.jpg','.jpeg','.gif']

#styles, etc

button_template = """<button class="btn btn-primary" 
                      type="button" 
                      data-toggle="collapse" 
                      data-target="#{}" 
                      aria-expanded="false" 
                      aria-controls="{}">
                         {} 
                      </button>
"""

collapse_template = """<p><div class="collapse" id="{}">
  <div class="card card-body">
   <table class="table table-sm table-detail table-hover" id="subsec_table">
     <thead class="thead-light">
        <tr>
        <th colspan="23" class="table-detail-th"> <h6>{}</h6> </th>
     </thead>
        </tr>
    </table>
   {}
  </div>
</div></p>
"""

img_style_template = """max-height;
"""

image_card_div = """<div class="card">
  <img class="card-img-top img-fluid" src="{}" />
      <div class="card-block">
        <p class="card-text">{}</p>
      </div>
    </div>
"""

image_card_caption = """{}. Submitted by {} on {}"""

def card_content(tagged_log_list):
    # Takes in a list of log messages that are tagged. 
    # First deal with images. Check if extension is in allowed
    # list of extensions:
    rv =""""""
    for l in tagged_log_list:
        if os.path.splitext(l.filename)[1] in img_file_extensions:
            rv += img_div(l)

    return rv

def img_div(logline):
    rv = """"""
    # Construct caption:
    comment = image_card_caption.format(logline.comment,
                                  logline.issuer.username,
                                  logline.created.strftime("%B %-d, %Y %H:%M:%S %Z"))


    # Construct absolute uri:
    img_uri = build_absolute_uri(logline.fileurl())

    # Format div:
    rv = image_card_div.format(img_uri, comment)
    return rv
     
    


@register.filter
def logboxes(obj, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x

    #rv = "{}".format(obj.graceid)

    # clear the response for the buttons, and 
    # for the collapsable sections. The next step
    # is to loop through the blessed tags list, 
    # query the logset for logs that contain the tag,
    # and if they're present, then construct a button
    # and a collapsed/exapnded log section. 

    rv = """"""
    rv_buttons = """"""
    rv_section = """"""

    # First fetch the complete log list as a
    # queryset object. This should reduce the number of 
    # database queries. 

    log_list = obj.eventlog_set.all()

    for tag_name in blessed_tag_priority_order:
        # retrieve the tag object:
        tag = Tag.objects.get(name=tag_name)

        # Filter the log list that contain the tag:
        tagged_log_list = log_list.filter(tags=tag)

        # If there are log entries, then construct buttons
        # and a box:

        if tagged_log_list:
            rv_buttons += button_template.format(tag_name,
                                              tag_name,
                                              tag.displayName)

            rv_section += collapse_template.format(tag_name,
                                              tag.displayName,
                                              card_content(tagged_log_list))


    rv += rv_buttons + rv_section

    return mark_safe(rv)

logboxes.needs_autoescape = True
