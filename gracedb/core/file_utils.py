import os
import logging
from retry import retry

# Set up logger
logger = logging.getLogger(__name__)

# This is a bandaid to overcome some very very 
# intermittent errors we've been seeing on AWS. 
# I'm going to let this play on playground and test 
# and if it doesn't fail castastropically, I'll
# move it into production before the root cause 
# can be determined.

@retry(tries=5, delay=0.25, logger=logger)
def get_file_list(logs, file_dir):
    """
    For a queryset of logs (corresponding to a single event or superevent),
    get a list of filenames, including non-versioned symlinks.

    If there is a question of access/view permissions for different files,
    they should be filtered *before* being passed to this function.
    """

    # Logs which have files attached
    file_logs = logs.exclude(filename='')

    # List of full versioned filenames
    file_list = [l.versioned_filename for l in file_logs]

    # Get list of possible symlinked files by getting the distinct
    # unversioned filenames from the list of logs with files
    possible_symlinks = file_logs.order_by('filename').values_list(
        'filename', flat=True).distinct()

    # Iterate over possible symlinks
    for s in possible_symlinks:
        # Get full path
        full_path = os.path.join(file_dir, s)

        # If the path is a symlink, get the file it points to (which should
        # be versioned).  Check if that file is in the file_list already:
        # if so, then the symlink can be included in the list, as well.
        if os.path.islink(full_path):
            pointed_to = os.path.basename(os.path.realpath(full_path))
            if pointed_to in file_list:
                file_list.append(s)

    return file_list
