
import os
import tempfile
import logging
import errno
import shutil


class VersionedFile(file):
    """Open a versioned file.

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
            file.__init__(self, actual_name, *args, **kwargs)
            return

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
                        0644)
                # re-open
                file.__init__(self, actual_name, *args, **kwargs)
                # lose fd we used to ensure file creation.
                os.close(fd)
                break
            except OSError, e:
                if e.error != errno.EEXIST:
                    raise
            version += 1
            failedAttempts += 1

        if failedAttempts >= 5:
            raise IOError("Too many attempts to open file")

    def _name_for_version(self, version):
        if version is None:
            return self.fullname
        return "{0},{1}".format(self.fullname, version)

    def _repoint_symlink(self):
        # re-point symlink to latest version
        last_version = max(self.known_versions())
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

    def close(self):
        if self.writing:
            # no need to update symlink if we were only reading.
            # can cause trouble if we were reading a non-versioned
            # file -- trying to discover the lastest version fails
            # painfully. (max(known_versions()) => max([]))
            self._repoint_symlink()
        if not self.closed:
            file.close(self)

    def __del__(self):
        # XXX file does not have a __del__ method.  Should we?
        if not self.closed:
            self.close()
