=============================
Features for EM Collaboration
=============================

On logging in
=============

Users must be logged in for access to GraceDB events and for permission to 
upload followup information. Please use the same identity you used when you
registered at gw-astronomy.org.

.. _basic_auth_for_lvem:

Scripted access for LV-EM members
============================================

.. Rationale: Non-LVC collaborators may not have ready access to robot certificates or keytabs.

Under construction.

Downloading a skymap
======================

Under construction.

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

To use the ``GraceDbBasic`` client, the user needs to already have a basic auth
password for scripted access, and to have put this in a protected ``.netrc`` file
(see :ref:`basic_auth_for_lvem`).

For users not familiar with Python, there are several other options available for 
uploading observation records:

- by using the webform on each event page (scroll down to the 'EM Observations'
  section and click on 'add observation record'). However, this method requires
  by-hand data entry.  

- by ``curl``-ing directly against the EM observation
  resource in the API (for an example, see 
  `here <https://gw-astronomy.org/wiki/LV_EM/CurlUploadFootprints>`_) 

- by coding against the GraceDB REST API 
  in one's own favorite language. If you choose to go this route, please
  consider sending us your script or posting it in the LV-EM wiki Technical Info
  page for the benefit of other users. See :ref:`coding_against_api`.  

- by email (not yet availabe, but in the works)

For more on the GraceBD event page and creating EM observation records, see 
`this <https://www.youtube.com/watch?v=oIJE4dTISs4>`_  helpful video
by Roy Williams.  There is a companion video on the SkymapViewer 
`here <https://www.youtube.com/watch?v=ydXUD9KIN98>`_.
