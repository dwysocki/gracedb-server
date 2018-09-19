.. _client_release:

================================
Preparing a new client release
================================

*Last updated 26 June 2017*

This section describes how to prepare new releases of ``gracedb-client`` and ``lvalert-client``.
We use ``gracedb-client`` as an example throughout and provide specifics when a particular step is different for each package.

.. NOTE::
    The steps here are only suggestions. You will undoubtedly discover better 
    and/or different ways to go about this.

Development
===========

Implement the features and bug fixes you wish to include in the new
client release. It's easiest to do this within a virtual environment on 
your workstation. That way you can make changes to the code and then::

    cd gracedb-client
    python setup.py develop

which will install the code into your virtual environment and update it with any changes you make.
When you are satisfied with the changes, commit and push.

Testing
=======

It's a good idea to test your new version on Scientific Linux (ldas-pcdev4 at CIT) and Debian (atlas9 on ATLAS) before proceeding.
The versions of Python there may be a bit behind the one on your workstation, and that can cause complications.
I've been burned by this before.
You can do it by cloning the package's git repository on a cluster headnode and building in a virtual environment::

    mkdir gracedb_testing
    cd gracedb_testing
    git clone https://git.ligo.org/lscsoft/gracedb-client.git
    cd gracedb-client
    PYTHONPATH=. python ligo/gracedb/test/test.py
    PYTHONPATH=. GRACEDB='python bin/gracedb' ./ligo/gracedb/test/test.sh

    virtualenv gracedb_virtualenv --system-site-packages
    source gracedb_virtualenv/bin/activate
    cd gracedb-client
    python setup.py develop
    cd ligo/gracedb/test
    python test.py

For ``gracedb-client``, you should run the unit tests; any other tests you may want to run should be added to the unit tests if not already present.
For ``lvalert-client``, test basic functions like subscribing/unsubscribing from a node, sending and receiving messages, etc., as well as anything specific that you may have modified when adding new features.

Changes for packaging
=====================

Update the source code for the new version number, and update the changelog.
Here are the files you will need to change:

gracedb-client
----------------

* ``debian/changelog``: list your changes in the prescribed format
* ``ligo-gracedb.spec``: check version, unmangled version, and release number
* ``ligo/gracedb/version.py``: update version

lvalert-client
----------------

* ``setup.py``: bump the version number
* ``debian/changelog``: list your changes in the prescribed format
* ``ligo-lvalert.spec``: check version, unmangled version, and release number

.. NOTE::
    Updating ``debian/changelog``: ``DEBEMAIL="Albert Einstein <albert.einstein@ligo.org>" dch -v 1.24-1``.
    Make sure to mimic the formatting exactly!

Final steps
-----------

After editing these files, make sure to commit and push.
For ``gracedb-client``, make sure the client still passes the unit tests.
Go to the root of the repository and see ``ligo/gracedb/test/README`` for 
more instructions on running the unit tests.

Tag this version of the repo and push the tag::

    git tag --list
    git tag -a "gracedb-1.24-1" -m "notes on your changes"
    git push --tags

.. NOTE::
    Git tags look like this: ``gracedb-1.24-1``, where 1 is the major version and 24 is the minor version. The last number corresponds to the build number (here, 1). Sometimes the format goes as 1.24.0-1, where 0 is typically referred to as the patch number.

Uploading to PyPI
=====================

Configure your machine
----------------------
The simplest way to upload to PyPI is with the Python package ``twine``.
First, get an account on both `PyPI <https://pypi.python.org/pypi>`__ and `test PyPI <https://testpypi.python.org/pypi>`__.
Then, create a ``$HOME/.pypirc`` file that looks like::

    [distutils]
    index-servers=
        pypi
        testpypi

    [pypi]
    username = username1
    password = userpassword1

    [testpypi]
    repository = https://test.pypi.org/legacy/
    username = username2
    password = userpassword2

This will be used below when uploading the packages.

.. NOTE::
    No repository is needed for the main PyPi if you're using twine 1.8.0+.
    If you aren't, set repository = https://upload.pypi.org/legacy/.

Preparing the release
---------------------

To build the package and upload it to PyPi testing::

    # Check out the new tag
    git checkout gracedb-1.24-1

    # Clean up your repository
    git clean -dxf

    # Build the source tarball
    python setup.py sdist bdist_wheel

    # Upload to test PyPI
    twine upload dist/* -r testpypi

Testing
-------
Make sure that you can install and use the package from the test PyPI.
Login to one of the LIGO clusters and do the following:

.. code-block:: bash

    # Set up virtual environment with install from test PyPi
    mkdir gracedb_testing
    cd gracedb_testing
    virtualenv --system-site-packages test
    source test/bin/activate
    pip install -i https://test.pypi.org/simple/ ligo-gracedb --upgrade

    # Clone the git repository (needed for git tag unittest to work)
    git clone https://git@git.ligo.org/lscsoft/gracedb-client.git

    # Check out tag
    cd gracedb-client
    git checkout gracedb-1.24-1

    # Run tests
    cd ligo/gracedb/test
    python test.py
    ./test.sh

    # Cleanup
    deactivate
    cd ../
    rm -rf gracedb_testing

Final upload
------------
This step should only be done **after** the release has gone through the entire
LIGO packaging and SCCB approval process (see below).

Upload to the real PyPI::

    twine upload dist/* -r pypi

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

Uploading the source
--------------------
Move the source tarball to ``software.ligo.org``. I do this with a script
I obtained from Adam Mercer, ``lscsrc_new_file.sh``.
I have added a version of this to the GraceDB ``admin-tools`` repo::

    cd /path/to/gracedb-client/dist
    cp /path/to/admin-tools/releases/lscsrc_new_file.sh .
    ./lscsrc_new_file.sh ligo-gracedb-*gz

.. NOTE::
    You must run the script in the same directory where the tarball lives.
    Otherwise it will put it onto the server in a weird subdirectory rather
    than just uploading the file directly.

Make sure that the file is accessible in the expected location, something
like ``http://software.ligo.org/lscsoft/source/ligo-gracedb-1.24.tar.gz``.

SCCB packaging and approval
---------------------------
Create a new issue on the `SCCB project page <https://bugs.ligo.org/redmine/projects/sccb>`__.
The title of the issue should be the name of the tag (ex: ``ligo-gracedb-1.24-1``).
The description should include an overview of the new features or modifications along with a list of the tests you have performed.
An example is shown below::

    Requesting deb and rpm packaging for ligo-gracedb-1.24-1.
    A source tarball has been uploaded to the usual location.
    A diff of the code changes is here: https://git.ligo.org/lscsoft/gracedb-client/compare/gracedb-1.23-1...gracedb-1.24-1

    This release includes:

    * Improved method for checking .netrc file permissions.
    * Added capability of creating events with labels initially attached, rather than having to add them as a separate step and generate multiple LVAlerts.
    * Added "offline" boolean parameter when creating an event. This parameter signifies whether the event was identified by an offline search (True) or online/low-latency search (False). Default: offline=False, which is identical to the current behavior.

    I've tested this release extensively, including:

    * Attempting to use several combinations of "bad" inputs for both labels and the "offline" parameter and ensuring that it fails appropriately (without contacting the server)
    * Running the unit tests (some of which were added in this patch)

Leave the issue status as 'New' to begin with.
The package builders will create packages for Scientific Linux and Debian; after it's deployed to the test machines (atlas9 on ATLAS and ldas-pcdev4 at CIT), someone will set the status to 'Testing'.
Run your tests on these machines if you didn't do it already; then update the issue's status to 'Requested'.
The SCCB members will vote and set the status to 'Approved' after it's approved.
After approval, the package will be deployed during the next maintenance period and the admins will set the category to 'Production' and the status to 'Closed'.

.. NOTE::
    You should submit a package for building and approval by Thursday at the very latest if you want it to be moved into production during maintenance on the following Tuesday.

