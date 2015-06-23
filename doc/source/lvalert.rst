=====================================
Integration with LVAlert
=====================================

Introduction
===============================================

GraceDB uses `LVAlert
<https://www.lsc-group.phys.uwm.edu/daswg/projects/lvalert.html>`_ to send
alerts to listeners within the LVC.  The content of the LVAlert message is
designed to convey actionable information about a state change in GraceDB,
whether it involves the creation of a new event, or the updating or labeling of
an existing one.

.. NOTE::
    An LVAlert message is sent out for *any* new event or annotation that arrives in the 
    GraceDB database. This means that
    a message volumes may be very high under certain circumstances, and 
    appropriate filtering is required in order for LVAlert to be useful.

Listening to specific event streams
==============================================

When a user runs ``lvalert_listen``, she/he will receive messages over all **nodes** to 
which she/he is subscribed. The node names consist of at least two elements::

    <group_name>_<pipeline_name>

In other words, the (lower-cased) names of the Group and Pipeline separated by an 
underscore. For example, the node ``burst_cwb`` would catch all messages relating to
events in the Burst group from the cWB pipeline. One can also specify the search name::

    <group_name>_<pipeline_name>_<search_name>

which has the effect of narrowing down the messages to only those related to a specific
search. For example, the node ``burst_cwb_allsky`` will contain messages relating to the
AllSky search, but not the MDC search. GraceDB tries to send a message to all applicable
nodes. Thus, a message sent to the node ``burst_cwb_allsky`` will *also* be sent to the
node ``burst_cwb``. This property allows the user to filter by search at the level of
specifying LVAlert processing scripts for individual nodes.

To see the names of all available nodes, simply execute::

    lvalert_admin -a username -b password -i

LVAlert message contents
================================================

GraceDB sends messages as a JSON-encoded dictionary. The dictionary contains the
following keys:

- ``uid``: the unique ID (a.k.a. ``graceid``) of the relevant event
- ``alert_type``: ``new``, ``update``, or ``label``
- ``description``: a text description (if applicable)
- ``file``: a URL for the relevant file (if applicable)
- ``object``: a dictionary representing the relevant object

For example, when a new event is created, an LVAlert message is created 
with alert type ``new``, and the ``object`` is just the JSON representation of 
of the event provided by the REST interface (see :ref:`searching_for_events`).
Below are examples of the possible types of LVAlert message. These were generated
by creating a new event, adding a couple of log messages, creating a Preliminary
VOEvent, and applying the DQV label (in that order).

New event::

    {
      "alert_type": "new", 
      "description": "", 
      "file": "https://gracedb.ligo.org/events/T129911/files/coinc.xml", 
      "object": {
        "created": "2015-06-17 22:10:43 UTC", 
        "extra_attributes": {
          "CoincInspiral": {
            "combined_far": 3.772326334623149e-14, 
            "end_time": 968929613, 
            "end_time_ns": 817383681, 
            "false_alarm_rate": 3.654963804145501e-08, 
            "ifos": "H1,L1", 
            "mass": 2.621732950210571, 
            "mchirp": 1.139938473701477, 
            "minimum_duration": null, 
            "snr": 19.73621083881572
          }
        }, 
        "far": 3.772326334623149e-14, 
        "gpstime": 968929613.8173836, 
        "graceid": "T129911", 
        "group": "Test", 
        "instruments": "H1,L1", 
        "labels": {}, 
        "likelihood": 8.33784842725385e+44, 
        "links": {
          "embb": "https://gracedb.ligo.org/api/events/T129911/embb/", 
          "filemeta": "https://gracedb.ligo.org/api/events/T129911/filemeta/", 
          "files": "https://gracedb.ligo.org/api/events/T129911/files/", 
          "labels": "https://gracedb.ligo.org/api/events/T129911/labels/", 
          "log": "https://gracedb.ligo.org/api/events/T129911/log/", 
          "neighbors": "https://gracedb.ligo.org/api/events/T129911/neighbors/", 
          "self": "https://gracedb.ligo.org/api/events/T129911", 
          "tags": "https://gracedb.ligo.org/api/events/T129911/tag/"
        }, 
        "nevents": 2, 
        "pipeline": "gstlal", 
        "search": "MDC", 
        "submitter": "branson.stephens@LIGO.ORG"
      }, 
      "uid": "T129911"
    }


Log message without file::

    {
      "alert_type": "update", 
      "description": "LOG: This is a test.", 
      "file": "", 
      "object": {
        "N": 4, 
        "comment": "This is a test.", 
        "created": "2015-06-17T17:10:43.381117", 
        "file": null, 
        "file_version": null, 
        "filename": "", 
        "issuer": {
          "display_name": "Branson Stephens", 
          "username": "branson.stephens@LIGO.ORG"
        }, 
        "self": "https://gracedb.ligo.org/api/events/T129911/log/4", 
        "tag_names": [
          "analyst_comments"
        ], 
        "tags": "https://gracedb.ligo.org/api/events/T129911/log/4/tag/"
      }, 
      "uid": "T129911"
    }


Log message with a file::

    {
      "alert_type": "update", 
      "description": "UPLOAD: bayestar.fits This is a file.", 
      "file": "bayestar.fits", 
      "object": {
        "N": 6, 
        "comment": "This is a file.", 
        "created": "2015-06-17T17:10:43.980188", 
        "file": "https://gracedb.ligo.org/api/events/T129911/files/bayestar.fits%2C0", 
        "file_version": 0, 
        "filename": "bayestar.fits", 
        "issuer": {
          "display_name": "Branson Stephens", 
          "username": "branson.stephens@LIGO.ORG"
        }, 
        "self": "https://gracedb.ligo.org/api/events/T129911/log/6", 
        "tag_names": [
          "sky_loc"
        ], 
        "tags": "https://gracedb.ligo.org/api/events/T129911/log/6/tag/"
      }, 
      "uid": "T129911"
    }
 
New VOEvent created::

    {
      "alert_type": "update", 
      "description": "VOEVENT: T129911-1-Preliminary.xml", 
      "file": "T129911-1-Preliminary.xml", 
      "object": {
        "N": 1, 
        "created": "2015-06-17T17:10:44.172876", 
        "file": "https://gracedb.ligo.org/api/events/T129911/files/T129911-1-Preliminary.xml%2C0", 
        "file_version": 0, 
        "filename": "T129911-1-Preliminary.xml", 
        "issuer": {
          "display_name": "Branson Stephens", 
          "username": "branson.stephens@LIGO.ORG"
        }, 
        "ivorn": "ivo://gwnet/gcn_sender#T129911-1-Preliminary", 
        "self": "https://gracedb.ligo.org/api/events/T129911/voevent/1", 
        "text": "<voevent text>", 
        "voevent_type": "PR"
      }, 
      "uid": "T129911"
    }

New DQV label applied::

    {
      "alert_type": "label", 
      "description": "DQV", 
      "file": "", 
      "uid": "T129911"
    }

.. XXX what kind of alert does a replacement trigger?

Receiving and Parsing LVAlert messages
====================================================

The LVAlert client tools include the ``lvalert_listen`` executable, which can be used to
receive and respond to LVAlert messages::

    lvalert_listen -a username -b password -c /path/to/lvalert_config.ini

The ``-c`` (configuration file) option allows you to specify an executable script to be called 
each time a message arrives over a particular node. Suppose one is only interested in
events from the burst group, cWB pipeline, and MDC search. Then the 
``lvalert_config.ini`` file could look like this::

    [burst_cwb_mdc]
    executable = /path/to/mdc_event_handler

And the script ``mdc_event_handler`` could be any script that is prepared to receive the
LVAlert message contents through standard input. Here is an example in Python::

    #!/usr/bin/env python
    import json
    from sys import stdin

    # Load the LVAlert message contents into a dictionary
    streamdata = json.loads(stdin.read())

    # Do something with new events having FAR below threshold
    alert_type = streamdata['alert_type']

    if alert_type == 'new':
        # The object is a serialized event. Get the FAR
        far = streamdata['object']['far']

        if far < 1.e-6:
            # Do some interesting processing
            pass

Further reading on LVAlert
=====================================================

Further information on using LVAlert can be found on the
`LVAlert Project Page <https://www.lsc-group.phys.uwm.edu/daswg/projects/lvalert.html>`_
and the `LVAlert Howto <https://www.lsc-group.phys.uwm.edu/daswg/docs/howto/lvalert-howto.html>`_.
