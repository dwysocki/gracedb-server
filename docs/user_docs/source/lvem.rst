=============================
Features for EM Collaboration
=============================

.. NOTE::

    This document describes access and features provided to members of
    collaborations which the LSC had an MOU with in O1 and O2. This access
    is maintained at present (August 2019), but may not be going forward.
    The information contained on this page will not be updated or
    maintained, and will eventually be removed.


On logging in
=============

A successful login is required in to access GraceDB events and upload 
followup information. The login process is the same as for the 
`LV-EM wiki <https://gw-astronomy.org/wiki/LV_EM/WebHome>`__: namely, 
click "LOGIN" at the upper right and then choose the login method
according to the identity you used for registering for LV-EM membership at
`gw-astronomy.org <https://gw-astronomy.org>`__. 

.. NOTE::

    Some users may have multiple identities available from the identity providers listed
    on the login page. However, only the identity used to register for LV-EM 
    will work for GraceDB access. For example, even though I have identities from
    LIGO, UW-Milwaukee, and Google, only my LIGO login will work for GraceDB since that 
    is the one I used to register for LV-EM membership. The reason is that
    there is no way (at present) to map these different identities to the same
    underlying user.


.. _basic_auth_for_lvem:

Scripted access for LV-EM members
============================================

Some processes need to access GraceDB in a *scripted* manner. For example,
an observational group might set up an automated process to listen for LIGO/Virgo GCN
notices and then download the skymaps for further processing
(see the `tutorial <http://nbviewer.ipython.org/github/lpsinger/ligo-virgo-emfollowup-tutorial/blob/master/ligo-virgo-emfollowup-tutorial.ipynb>`__). 
As these alerts could come at any time of the day or night, it is not 
generally possible for the user to go through the usual login sequence. Traditionally,
GraceDB has handled scripted access with X509 robot certificates or
robot Kerberos keytabs, but these may not be easily accessible to all 
LV-EM group members. 

Thus, there is an alternative using basic auth (a simple username-and-password
scheme). First, obtain a robotic
access password by navigating to `this page <https://gracedb.ligo.org/options/manage_password>`__
and clicking "Get me a password!" (or by clicking "OPTIONS" on the navigation
menu and then "Password Manager." Each time you click the button, you
will get a new basic auth password, and the old one will be lost. (Note 
that these passwords only last for 1 year.) The password is a 20 character
random sequence. 

.. NOTE::
    
    This robotic password does not affect the way in which you login to
    the GraceDB web interface. It is only for use with the REST interface
    as described in the examples below. You will need to continue logging
    into the web interface using the identity with which you registered for
    LV-EM membership.

Once you've obtained a robotic password, the best way to use it is to create
a ``.netrc`` file containing your username and password (with permissions ``0600``
to make sure that only you can read it). The ``.netrc`` file could look like this::

    machine   gracedb.ligo.org
    login     myself@institution.edu
    password  abc123.....

Place the resulting ``.netrc`` file in your home directory.
Once that's done, you should be able to access the GraceDB REST API
using any tool that supports basic auth. 
For example, you can use the GraceDB Python client::

    from ligo.gracedb.rest import GraceDb, HTTPError
 
    service_url = 'https://gracedb.ligo.org/api/'
    client = GraceDb(service_url, username='user', password='pass')
  
    try:
        r = client.ping()
    except HTTPError, e:
        print e.message
  
    print "Response code: %d" % r.status
    print "Response content: %s" % r.json() 

If you're not comfortable using Python for scripted access to GraceDB, it is
also possible to use ``curl`` to directly make requests to the server with the
same basic auth credentials. Some examples of using curl are available 
`here <https://gw-astronomy.org/wiki/LV_EM/TechInfo>`__.


Downloading a skymap
======================
The GraceDB Python client can be used to download
files from Gracedb or add comments, plots, or observation records (see 
the next section). Here, we'll
show an example of downloading a skymap. Suppose we know that a particular
GraceDB event (``T125738``) has a skymap file called ``bayestar.fits.gz``.
This file can be retrieved in the following way::

    from ligo.gracedb.rest import GraceDbBasic

    grace_id = 'T125738'            # identifier for the event
    filename = 'bayestar.fits.gz'  # filename of desired skymap

    # Prepend with grace_id for output filename
    out_filename = grace_id + '_' + filename

    # Instantiate the GraceDB client
    service_url = 'https://gracedb.ligo.org/api/'
    client = GraceDbBasic(service_url)

    # Grab the file from the server and write it 
    out_file = open(out_filename, "w")
    r = client.files(grace_id, filename)
    out_file.write(r.read())
    out_file.close()


.. _create_emobservation:

Reporting coordinates of followup observations
===============================================
In the following example, the GraceDB Python client is used to create an 
observation record consisting of three separate footprints::

    # Define the parameters of the observation to be reported
    grace_id      = 'M158044'           # the event's UID
    group         = 'CRTS'              # the MOU group 
    comment       = 'hello my friend'   # free text comment
    raList        = [123.0,124.0,125.0] # RAs of centers (degrees)
    decList       = [10.0,11.0,13.0]    # Dec of centers (degrees)
    startTimeList = [                   # beginnings of exposures (UTC)
        '2015-05-31T12:45:00',
        '2015-05-31T12:49:00',
        '2015-05-31T12:53:00']
    raWidthList   = 10.0       # list (or one for all) of widths in RA (degrees)
    decWidthList  = 10.0       # list (or one for all) of widths in Dec (degrees)
    durationList  = 20.0       # list (or one for all) of exposure times in sec

    # Instantiate the GraceDB client
    client = GraceDbBasic()

    # Write the EMObservation record to GraceDB
    r = client.writeEMObservation(grace_id, group, raList, raWidthList,
        decList, decWidthList, startTimeList, durationList, comment)

    if r.status == 201:       # 201 means 'Created'
        print 'Success!'

Note that the start times are always assumed to be in UTC. For users not
familiar with Python, there are several other options available for uploading
observation records:

- by using the webform on each event page (scroll down to the 'EM Observations'
  section and click on 'add observation record'). However, this method requires
  by-hand data entry.  

- by ``curl``-ing directly against the EM observation
  resource in the API (`example <https://gw-astronomy.org/wiki/LV_EM/CurlUploadFootprints>`__) 

- by email (not yet available, but in the works)

If you discover a mistake in your observation record, the best way to correct
it is to submit a new observation record with corrected values and request that
the old one be deleted. Please send an email to uwm-help@cgca.uwm.edu with
something like "delete GraceDB EMObservation" in the subject line. Tell us
which entry you'd like deleted, and we'll take care of it.  In the future, we
are hoping to make these observation records editable by the submitter.

.. For more on the GraceDB event page and creating EM observation records, see `this <https://www.youtube.com/watch?v=oIJE4dTISs4>`__  helpful video by Roy Williams.
.. There is a companion video on the SkymapViewer `here <https://www.youtube.com/watch?v=ydXUD9KIN98>`__.
