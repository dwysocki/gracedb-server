import os

SUFFIXES_TO_STRIP = ['.gz', '.multiorder', '.fits']

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


def flexible_skymap_to_png(skymap_file, new_ext='.png'):
    """
    For a given skymap file, return the base filename with a new file
    extension (default .png).

    In O4, skymaps have transitioned from *.fits.gz to any number of options
    from Bilby (.fits, .fits,N, .fits.gz). In O3 we just replaced the
    .fits.gz string with .png, but that's currently broken.
    """

    file_version = None
    filename_is_base = False

    # Test to see if the versioning comma is included:
    if ',' in skymap_file:
        split_file = skymap_file.split(',')
        base_filename, file_version = split_file
    else:
        base_filename = skymap_file

    while not filename_is_base:
        stripped_base_filename, file_extension = os.path.splitext(base_filename)
        if not file_extension in SUFFIXES_TO_STRIP:
            filename_is_base = True
        else:
            base_filename = stripped_base_filename

    new_filename = base_filename + new_ext

    return new_filename, file_version
