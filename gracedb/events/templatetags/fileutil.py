from django import template
from django.conf import settings

from django.utils.safestring import mark_safe
from core.urls import build_absolute_uri
import os 

# Register the new template tag:
register = template.Library()

# This is the template for each row of the file table:
template = """<tr>
              <td> {filename} </td>
              <td> {created} </td>
              <td> {submitter} </td>
              <td> {size} </td>
              </td>
              </tr>"""

# A link template:
link_template = '<a href="{url}">{filename}</a>'

# time format:
time_fmt = '%Y-%m-%d %H:%M:%S'

@register.simple_tag
def file_table_detail(log_list, datadir, uid):

    # Zero out the response:
    rv = ""

    # If there's nothing in the list, just return something blank:
    if not log_list:
        return rv

    # Get the base files uri from the first log message:
    base_fileurl = os.path.dirname(log_list.first().fileurl())

    # Get the file names of possible symlinks. This is a list of unique
    # filenames, without the versioning. They should all be symlinks in 
    # the way gracedb handles files, but we're going to check anyway.
    possible_symlinks = log_list.order_by('filename').values_list(
        'filename', flat=True).distinct()

    for f in possible_symlinks:
        # Get the list of versioned files with the same filename:
        related_files = log_list.filter(filename=f).order_by('-file_version')

        # Get the target of the symlink, and start to construct row tables:
        full_file_path = os.path.join(datadir, f)

        # Check to see if it's a symlink, and construct a link to the target.
        # This is really just a sanity check, since there should be a link
        # for every file that gets uploaded. 
        if os.path.islink(full_file_path):
            link_target = os.path.basename(os.path.realpath(full_file_path))

        # Loop over the list of log objects that contain the visible files:

        for l in related_files:

            # Does the target of this file's symlink point to the file in this
            # log message? Then construct a formatted row with both links. This
            # provides some redundant information, but I think it's informative
            # to know where the link actually points to.
            if l.versioned_filename == link_target:

                # Construct the link to symlinked file:
                sym_link = event_file_link(filename = f, 
                               fileurl = base_fileurl,
                               symlink = True,
                               bold=True)

                # Construct the link to the linked file:
                target_file = event_file_link(filename = l.versioned_filename,
                                  fileurl=base_fileurl)

                # Now that we have both links, output the row with the created
                # time, submitter, and file size of the target file, not the
                # link:
                rv += template.format(filename = sym_link + " &#8594; " + target_file,
                                created = l.created.strftime(time_fmt),
                                submitter = l.issuer.get_full_name(),
                                size = kb_decimals(l, datadir))

            # Now constuct a table row for the file.
            link = event_file_link(filename=l.versioned_filename,
                      fileurl=base_fileurl)
            rv += template.format(filename=link,
                    created=l.created.strftime(time_fmt),
                    submitter=l.issuer.get_full_name(),
                    size=kb_decimals(l, datadir))

    return mark_safe(rv)

def event_file_link(filename, fileurl, symlink=False, bold=False):
    url = build_absolute_uri(os.path.join(fileurl, filename))
    if symlink:
        url = url.split(',')[0]

    link = link_template.format(url=url, filename=filename)

    if bold:
        link = "<b>"+link+"</b>"

    return link

def kb_decimals(log, datadir, decimals=2):
    return round(os.path.getsize(os.path.join(datadir, 
         log.versioned_filename)) / 1024, decimals)
