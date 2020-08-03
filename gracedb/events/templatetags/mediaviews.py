from django import template
from django.conf import settings

from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

#Django filtering stuff:
import operator
from django.db.models import Q
from functools import reduce

from events.models import Event, Tag
from gracedb.core.urls import build_absolute_uri
import os

register = template.Library()

# Define some stuff:
blessed_tag_priority_order = [
    'analyst_comments',
    'psd',
    'data_quality',
    'public',
    'sky_loc',
    'background',
    'ext_coinc',
    'strain',
    'tfplots',
    'sig_info',
    'audio',
    'em_follow',
]


# This section is for image formatting purposes. I want to assign 
# "blessed" file extensions, and then set up a django Q-filter. 
# Then, define which images get displayed as high aspect-ratio. 
# This is a little hacky, but I didn't take the time to learn how to 
# incorporate javascript or the django.core.files.images models. If 
# pipelines want to upload new images that are a different aspect ratio, 
# add its name to the blessed list, or figure out a better way :-/

img_file_extensions = ['.png','.jpg','.jpeg','.gif']
images_filter = reduce(operator.or_, (Q(filename__contains=ex) for ex in img_file_extensions))

wide_image_names = ['omegascan','coherence', 'em_bright']
wide_filter = reduce(operator.or_, (Q(filename__contains=name) for name in wide_image_names))

#styles, etc

button_template = """<button class="btn btn-primary" 
                      type="button" 
                      data-toggle="collapse" 
                      data-target="#{}" 
                      aria-expanded="true" 
                      aria-controls="{}">
                         {} 
                      </button>
"""

embedded_button_template = """<button class="btn btn-secondary btn-sm" 
                      type="button" 
                      data-toggle="collapse" 
                      data-target="#{}" 
                      aria-expanded="true" 
                      aria-controls="{}">
                         Collapse {} 
                      </button>
"""
collapsed_card_template = """
<p><div class="collapse show" id="{}">
  <div class="card card-body">
    <div class="card-header log-card-header text-left">
      <h6>{}</h6>
    </div>
   {}
  </div>
  <br>
   {}
</div></p>
"""

img_style_template = """max-height= 250px;
"""

image_card_div = """
<div class="card my-3 log-comment-card">
  <div class="card-header log-comment-card-header text-left">
    <h7>Log Image</h7>
  </div>
  <a href="{}" data-toggle="lightbox" data-type="image" data-gallery="{}">
  <img class="card-img-top img-fluid" src="{}" style="width:auto;"/>
  </a>
      <div class="card-body">
        <hr width="50%"/>
        {}
      </div>
    </div>
"""

comment_card_div = """
<div class="card my-3 log-comment-card">
  <div class="card-header log-comment-card-header text-left">
    <h7>Log Comment</h7>
  </div>
  <div class="card-body">
    <p class="card-text">{}</p>
    <hr width="50%"/>
    <footer class="blockquote-footer">{}</footer>
  </div>
</div>
"""

image_card_caption = """{} <footer class="blockquote-footer"> Submitted by {} on {} </footer>"""

comment_card_title = """Submitted by {} on {} """

def card_content(tagged_log_list, tag_name):
    # Takes in a list of log messages that are tagged. 
    # First deal with images. Check if extension is in allowed
    # list of extensions:
    rv =""""""

   # First, wide images:
    for l in tagged_log_list.filter(images_filter & wide_filter):
        rv += img_div(l,tag_name)

   # deal with "normal" (non-wide) images.
    rv += """<div class="card-deck">"""
    for l in tagged_log_list.filter(images_filter & ~ wide_filter):
        rv += img_div(l,tag_name)
    rv += """</div>"""

   # now make a table for tagged non-image log entries,
   # like tables.

    for l in tagged_log_list.filter(~images_filter):
        rv_title = comment_card_title.format(l.issuer.get_full_name(),
                              l.created.strftime("%B %-d, %Y %H:%M:%S %Z"))

        # Append the log message on the comment card
        msg = l.comment

        # Include a link the tagged file, if applicable.
        if l.filename:
            msg += """ (<a href="{}">{}</a>)""".format(build_absolute_uri(l.fileurl()),
                                                       l.filename)
        
        rv += comment_card_div.format(msg, rv_title)

   

    return rv

def img_div(logline, tag_name):
    rv = """"""
    # Construct caption:
    comment = image_card_caption.format(logline.comment,
                                  logline.issuer.get_full_name(),
                                  logline.created.strftime("%B %-d, %Y %H:%M:%S %Z"))


    # Construct absolute uri:
    img_uri = build_absolute_uri(logline.fileurl())

    # Format div:
    rv = image_card_div.format(img_uri, 
                         tag_name,
                         img_uri, 
                         comment)
    return rv

@register.filter
def logboxes(log_list, autoescape=None):
    if autoescape:
        esc = conditional_escape
    else:
        esc = lambda x: x


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

    for tag_name in blessed_tag_priority_order:
        # retrieve the tag object:
        tag, created  = Tag.objects.get_or_create(name=tag_name)
        #tag = Tag.objects.get(name=tag_name)

        # Filter the log list that contain the tag:
        tagged_log_list = log_list.filter(tags=tag)
        
        # If there are log entries, then construct buttons
        # and a box:
        
        if tagged_log_list:
            rv_buttons += button_template.format(tag_name,
                    tag_name,
                    tag.displayName)
            
            rv_section += collapsed_card_template.format(tag_name,
                    tag.displayName,
                    card_content(tagged_log_list, tag_name),
                    embedded_button_template.format(tag_name,
                        tag_name,
                        tag.displayName))

    # append the response after cycling through all the tags
    rv += rv_buttons + rv_section
        
    return mark_safe(rv)

logboxes.needs_autoescape = True

# Filter that filters a queryset of log entries 
# and a tag name (most likely 'public') and then 
# returns all the logs that have that tag.
@register.filter
def filter_logs(log_list, tag_name=None, autoescape=None):
    if tag_name:
        tag, created = Tag.objects.get_or_create(name=tag_name)
        log_list = log_list.filter(tags=tag) 

    return log_list 

@register.filter
def tag_selecter(name, autoescape=None):
    rv = """"""
    rv += """<select class="form-control" multiple="multiple"
                      name="{}">""".format(name)
    for tag_name in blessed_tag_priority_order:
        # retrieve the tag object:
        tag, created  = Tag.objects.get_or_create(name=tag_name)
        rv += """<option value="{}">{}</option>""".format(tag_name, tag.displayName)
    rv += """</select>"""

    return mark_safe(rv)
