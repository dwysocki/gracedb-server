================================
Preparing a new client release
================================

.. NOTE::
    The steps here are only suggestions. You will undoubtedly discover better 
    and/or different ways to go about this.

Develop
=======

Implement the features and bug fixes you wish to include in the new
client release. It's easiest to do this within a virtual environment on 
your workstation. That way you can make changes to the code and then::

    cd gracedb-client
    python setup.py install

which will install into your virtual environment. When you are satisfied 
with the changes, commit and push.

.. NOTE:: 
    It's a good idea to test this version on Scientific Linux and Debian
    at the clusters before proceeding. 
    The versions of Python there may be a bit behind the one on your workstation,
    and that can cause complications. I've been burned by this before.
    You can do it by cloning the ``gracedb-client`` package on a cluster
    headnode and building in a virtual environment as show above.

Changes for packaging
=====================

Update the source code for the new version number, and update the changelog.
Here are the files you will need to change:

* ``setup.py``: bump the version number
* ``debian/changelog``: list your changes in the prescribed format
* ``ligo-gracedb.spec``: check version, unmangled version, and release number
* ``ligo/gracedb/__init__.py``: update ``GIT_TAG``
* ``ligo/gracedb/cli.py``: update ``GIT_TAG``
* ``ligo/gracedb/test/test.py``: update the version number in the ``GIT_TAG`` test

After editing these files, make sure to commit and push.  Also make sure the
client still passes the unit tests::

    python setup.py install
    cd gracedb-client/ligo/gracedb/test
    unset TEST_SERVICE
    python test.py

Tag this version of the repo and push the tag::

    git tag --list
    git tag -a YOUR_GIT_TAG
    git push --tags

.. NOTE::
    Git tags look like this: ``gracedb-1.20-1``, where 1.20 is the version and
    the last number corresponds to the build number (here, 1).

Prepare to upload to PyPI
=========================

Clear everything out of the directory ``gracedb-client/dist`` and then
build the source tarball::

    python setup.py sdist

Log into ``testpypi.python.org`` and change the version number. Click on the package
name in the right-hand menu, then click 'edit' near the top. Bump the version 
number as appropriate, and then click 'Add Information' at the bottom.

Upload the package to the test PyPI instance.  This is easier if you install
the python package ``twine``. I tend to do this in a special virtual environment
used only for this purpose::

    deactivate
    cd
    cd my_virtual_envs
    virtualenv --system-site-packages pypi-upload
    source pypi-upload/bin/activate
    pip install twine

    cd /path/to/gracedb-client
    twine upload dist/*.gz -r test

Make sure that you can install and use the package from the test PyPI::

    deactivate
    cd 
    cd my_virtual_envs
    virtualenv --system-site-packages test
    source test/bin/activate
    pip install -i https://testpypi.python.org/pypi ligo-gracedb --upgrade

    cd /path/to/gracedb-client
    git pull
    cd ligo/gracedb/test
    python test.py
    cd ~/my_virtual_envs
    deactivate
    rm -f -r test

Log into ``pypi.python.org`` (the non-test instance) and update the version number
as you did above for the test instance.  Next, upload the package to the
regular, non-test PyPI::

    deactivate 
    cd ~/my_virtual_envs
    source pypi-upload/bin/activate
    cd /path/to/gracedb-client
    twine upload dist/*.gz

Lastly, make sure you can pip install the package::

    deactivate
    cd ~/my_virtual_envs
    virtualenv --system-site-packages test
    source test/bin/activate
    pip install ligo-gracedb
    deactivate
    rm -f -r test

Steps for LIGO packaging
========================

Move the source tarball to ``software.ligo.org``. I do this with a script
I obtained from Adam Mercer, ``lscsrc_new_file.sh``. I have added a version
of this to the GraceDB ``admin-tools`` repo::

    cd /path/to/gracedb-client/dist
    cp /path/to/admin-tools/releases/lscsrc_new_file.sh .
    ./lscsrc_new_file.sh ligo-gracedb-*gz

.. NOTE::
    You must run the script in the same directory where the tarball lives.
    Otherwise it will put it onto the server in a weird subdirectory rather
    than just the file.

Make sure that the file is accessible in the expected location, something
like ``http://software.ligo.org/lscsoft/source/ligo-gracedb-1.20.tar.gz``.

Send an email to the packagers notifying them of the new package. You will
probably want to include the information that you put into the changelog.
Here's an example of one that I sent::

    to daswg+announce@ligo.org

    There is a new release of the GraceDB client tools.

    New features are:
        Improved error handling for expired or missing credentials
        Improved error handling when server returns non-JSON response
        Added --use-basic-auth option to command-line client


    The release tag is: ligo-lvalert-1.20-1

    The source is available at:

    http://software.ligo.org/lscsoft/source/ligo-gracedb-1.20.tar.gz

    thanks!
    Branson

After the package is in the testing repo, look for the corresponding row in the 
`SCCB wiki <https://wiki.ligo.org/SCCB/WebHome>`__.
One of the packagers will hopefully have added it.

Once the new package is installed at the system level on the bleeding-edge
head nodes, test it on different OSes (probably ``ldas-pcdev4`` at CIT for
Scientific Linux and ``atlas9`` at AEI for Debian).

Update the SCCB wiki entry stating that the package has been tested on SL
and Debian and request that it be moved into production.

Forward the package announcement email to the SCCB with some additional text
notifying them that the package is waiting for their approval.  Here is an
example of one that I sent::

    to daswg+SCCB@ligo.org 

    dear SCCB,

    I have tested this release on ldas-pcdev4 @ CIT and atlas9 @ AEI. The
    release passes the unit tests, so I am requesting that it be moved 
    into production.

    best,
    Branson



