import os
import six
import tempfile
import logging
import errno
import shutil
import mimetypes

from django.core.files.uploadedfile import InMemoryUploadedFile, \
    SimpleUploadedFile, TemporaryUploadedFile, UploadedFile

import logging
logger = logging.getLogger(__name__)


class FileVersionError(Exception):
    # Problem with file version (likely not an int)
    pass


class FileVersionNameError(Exception):
    # Problem with filename (likely has an extra comma somewhere in the
    # filename)
    pass


class VersionedFile(object):
    """
    Open a versioned file.

    VersionedFile(name [, mode [, version [, OTHER FILE ARGS]]]) -> file object
    """
    def __init__(self, name, *args, **kwargs):

        self.log = logging.getLogger('VersionedFile')

        if ',' in name:
            # XXX too strict.
            raise IOError("versioned file name cannot contain a ','")

        if len(args):
            mode = args[0]
        else:
            mode = kwargs.get('mode', "")

        if len(args) > 1:
            version = args[1]
            # Remove from arglist to prep for passing to parent class.
            args = args[:2]
        else:
            version = None
            if 'version' in kwargs:
                version = kwargs['version']
                # Remove from kwargs to prep for passing to parent class.
                del kwargs['version']

        self.writing = ('w' in mode) or ('a' in mode) or ('+' in mode)

        absname = os.path.abspath(name)
        self.absname = absname
        fullname = name
        self.fullname = fullname

        # If we are merely reading, just open the file as requested.
        # Easy Peasy.

        if not self.writing:
            actual_name = self._name_for_version(version)
            self.log.debug(
                    "opening file '{0}' with mode '{1}'"
                    .format(actual_name, mode))
            # XXX I, Branson, want version to be a property of the file object.
            # It is probably stupid to have the local 'version' too (i.e., the
            # one scoped inside of this __init__). But I'm reluctant to mess with
            # Brian's code too much.
            self.version = version
            self.file = open(actual_name, *args, **kwargs)

        # Otherwise...

        #  Specific version requsted?  For writing?
        #  I don't think so.
        if version is not None:
            #  XXX IOError appropriate here?
            e = IOError(
                "Cannot write to a specific version of a VersionedFile")
            e.errno = errno.EINVAL
            e.filename = fullname
            raise e

        #  XXX No appending.  Could conceivably copy the latest
        #  (or specified) version of the file, then open w/append.
        if 'a' in mode:
            #  XXX IOError appropriate here?
            e = IOError("Cannot (currently) append to a VersionedFile")
            e.errno = errno.EINVAL
            e.filename = fullname
            raise e

        version = max([-1] + self.known_versions()) + 1

        if os.path.exists(fullname) and not os.path.islink(fullname):
            # It is not versioned.  Versionize it.
            if version != 0:
                raise IOError("VersionedFile symlink inconsistency.")
            # XXX risky.  race condition.
            #os.rename(fullname, self._name_for_version(version))
            shutil.move(fullname, self._name_for_version(version))
            self._repoint_symlink()
            version += 1

        # Open file, which must not exist.

        failedAttempts = 0

        while failedAttempts < 5:
            actual_name = self._name_for_version(version)
            self.log.debug(
                "opening file '{0}' with mode '{1}'"
                .format(actual_name, mode))
            try:
                # os.O_EXCL causes the open to fail if the file already exists.
                fd = os.open(actual_name,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                        0o644)
                # re-open
                self.file = open(actual_name, *args, **kwargs)
                # lose fd we used to ensure file creation.
                os.close(fd)
                break
            except OSError as e:
                if e.errno != errno.EEXIST:
                    raise
            version += 1
            failedAttempts += 1

        if failedAttempts >= 5:
            raise IOError("Too many attempts to open file")
        # XXX As above in the writing case. We simply want version to 
        # be an accessible property of the file object.
        self.version = version

    def _name_for_version(self, version):
        if version is None:
            return self.fullname
        return self.construct_versioned_name(self.fullname, version)

    @staticmethod
    def construct_versioned_name(filename, version):
        return "{0},{1}".format(filename, version)

    @staticmethod
    def split_versioned_name(versioned_name):
        """
        Split a (possibly) versioned file name into file name and version.
        If filename doesn't include version (according to the convention that
        we expect), return None for the version.
        """
        result = versioned_name.split(',')
        if len(result) == 2:
            filename = result[0]
            version = result[1]

            # Version is a string here, try to convert it to an int
            try:
                version = int(version)
            except ValueError as e:
                raise FileVersionError('Bad version specifier')
        elif len(result) == 1:
            filename = result[0]
            version = None
        else:
            err = 'Filename {0} does not match versioning scheme'.format(
                versioned_name)
            raise FileVersionNameError(err)

        return filename, version

    def _repoint_symlink(self):
        # re-point symlink to latest version
        last_version = max(self.known_versions())
        # XXX Maybe ought to check that we are removing a symlink.
        try:
            # XXX Another race condition.  File will not exist for a very brief time.
            os.unlink(self.fullname)
        except OSError as e:
            # Do not care if file does not exist, otherwise raise exception.
            if e.errno != errno.ENOENT:
                raise
        name = os.path.basename(self._name_for_version(last_version))
        os.symlink(name, self.fullname)
        return

# XXX   This fails when renaming/mv-ing across devices.
        # XXX assumption: tempfile name will remain unique after closing
        tmp = tempfile.NamedTemporaryFile(delete=True)
        tmpname = tmp.name
        tmp.close()
        os.symlink(self._name_for_version(last_version), tmpname)
        #os.rename(tmp.name, self.fullname)
        shutil.move(tmp.name, self.fullname)

    def known_versions(self):
        path = self.absname
        d = os.path.dirname(path) or '.'
        name = os.path.basename(path)
        # XXX what if stuff after ',' is not an int.
        return [int(f.split(',')[1])
                for f in os.listdir(d) if f.startswith(name + ',')]

    def write(self, s):
        self.file.write(s)

    @property
    def closed(self):
        return self.file.closed

    def close(self):
        if self.writing:
            # no need to update symlink if we were only reading.
            # can cause trouble if we were reading a non-versioned
            # file -- trying to discover the lastest version fails
            # painfully. (max(known_versions()) => max([]))
            self._repoint_symlink()
        if not self.file.closed:
            self.file.close()

    def __del__(self):
        # XXX file does not have a __del__ method.  Should we?
        if not self.file.closed:
            self.file.close()

    @staticmethod
    def guess_mimetype(filename):
        TEXT_EXTENSIONS = ['.log', '.out']
        filename = VersionedFile.basename(filename)
        content_type, encoding = mimetypes.guess_type(filename)
        if content_type is None and '.' in filename:
            for ext in TEXT_EXTENSIONS:
                if filename.endswith(ext):
                    content_type = 'text/plain'
                    break
        return content_type, encoding

    @staticmethod
    def basename(filename):
        if ',' in filename:
            filename = filename.split(',')[0]
        return os.path.basename(filename)


def create_versioned_file(filename, file_dir, file_contents):

    # Get full file path
    full_path = os.path.join(file_dir, filename)

    # Create file
    if isinstance(file_contents, six.string_types):
        fdest = VersionedFile(full_path, 'w')
        fdest.write(file_contents)
    elif isinstance(file_contents, (UploadedFile, InMemoryUploadedFile,
                    TemporaryUploadedFile, SimpleUploadedFile, bytes)):
        fdest = VersionedFile(full_path, 'wb')
        for chunk in file_contents.chunks():
            fdest.write(chunk)
    fdest.close()

    return fdest.version
