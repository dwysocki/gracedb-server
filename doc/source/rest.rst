.. _rest_interface:

==========================
Using the REST interface
==========================

.. _installing_the_client:

Installing the client 
====================================

The GraceDB client tools should already be installed at the LVC computing clusters.
However, if you want to interact with GraceDB from your own machine, you will need
to install the client tools yourself. The easiest way is to use ``pip`` to install
it from the `Python Package Index <https://pypi.python.org/pypi>`__::

    pip install ligo-gracedb

(See `here <https://pip.pypa.io/en/latest/installing.html>`__ for instructions in 
installing ``pip`` if it is not already available on your machine.) Additionally,
packages for Debian (``.deb``) and Scientific Linux (``.rpm``) are available by 
pointing your system to the appropriate repositories as described 
`here <https://wiki.ligo.org/DASWG/SoftwareDownloads>`__.
Then the client tools can be installed via::

    apt-get install python-ligo-gracedb

or ::

    yum install ligo-gracedb

Alternatively, the client can be built from source. Please note, however, that
the code at the head of the git repository may be volatile or unstable. The 
repository is publicly available via HTTPS::

    git clone https://git.ligo.org/lscsoft/gracedb-client.git

It is also available through SSH::

    git clone git@git.ligo.org:lscsoft/gracedb-client.git

In order to submit patches, you should fork the repository, implement your changes, and submit a merge request.
Patches should also be documented on the GraceDB Redmine `page <https://bugs.ligo.org/redmine/projects/gracedb>`__.

.. _rest_client_basic_usage:

Basic usage of the REST client
====================================

The documentation in this section will focus on the use of the Python REST client. The
alternative command-line client, ``gracedb`` is a simple wrapper on the REST client 
provided for convenience (see below, :ref:`command_line_client`) and is not as 
fully featured. 

.. NOTE::
    Before using the REST client, credentials for authentication must be available.
    Run ligo-proxy-init or, if using a robot certificate, set the environment 
    variables ``X509_USER_CERT`` and ``X509_USER_KEY`` (for more information, see :ref:`auth`).

.. XXX Probably would be good to actually show people how to set these environment variables.

The REST client is typically used in a script or in the Python interpreter to 
accomplish a specific task, such as creating a new event or retrieving information 
about events matching a query. The workflow involves importing the client class,
instantiating the client, and then calling the desired method::

    from ligo.gracedb.rest import GraceDb, HTTPError

    client = GraceDb()

    try:
        r = client.ping()
    except HTTPError, e:
        print e.message

    print "Response code: %d" % r.status
    print "Response content: %s" % r.json()    


In the above example, we merely ping the GraceDB server and examine the
response.  If there is an error (such as an authentication failure), the
``HTTPError`` exception will be thrown. If not, the response object contains a
status code and a response body in JSON. The ``json`` method on the response
object simply decodes the JSON content. In this particular case, the response
code should be 200 (meaning "OK") and the body contains a large dictionary
of information representing the `API Root resource <https://gracedb.ligo.org/apiweb/>`__.
Most of the examples below will ignore the error handling shown here for the 
sake of brevity.

In addition to ``ping``, the most important client methods are:

- ``events`` for accessing a list of events,
- ``files`` for downloading a file or list of files, and ``writeFile`` for uploading,
- ``logs`` for obtaining a list of log entries, and ``writeLog`` to create a new one,
- ``emobservations`` for obtaining a list of EM followup observations, and 
  ``writeEMObservation`` to create a new one,
- ``labels``, ``writeLabel``, and ``removeLabel`` for managing labels,
- ``tags``, ``createTag``, and ``deleteTag`` for managing tags.

Docstrings are available for most of the client methods. To see them, type 
``help(client.ping)`` (for example) in the Python interpreter.

.. _searching_for_events:

Searching for events
===================================

Suppose you are working on a script to search for all events matching a 
specific query and then to retrieve a piece of information about each event in
the results. For example, the following code retrieves the chirp 
mass for each ``gstlal`` event during ER5 with FAR less than 1.0E-4::

    from ligo.gracedb.rest import GraceDb
    client = GraceDb()

    # Retrieve an iterator for events matching a query.
    events = client.events('gstlal ER5 far < 1.0e-4')

    # For each event in the search results, add the graceid
    # and chirp mass to a dictionary.
    results = {}
    for event in events:
        graceid = event['graceid']
        mchirp  = event['extra_attributes']['CoincInspiral']['mchirp']
        results.update({ graceid: mchirp})

Note that the ``events`` method on the client returns an *iterator* on event
dictionaries rather than a list. The chirp mass is an attribute specific to the
inspiral event subclass, hence the different ways of accessing the ``graceid``
and the chirp mass.

But how did I know the structure of the event dictionary so that I could pull
out the chirp mass? The best way is to look at the structure of an example
event in the *browseable* REST API. Here some example events from the different
subclasses to demonstrate the structure of the event dictionaries.

- `Test gstlal MDC <https://gracedb.ligo.org/apiweb/events/T125738>`__ (a CBC event)
- `Test cWB MDC <https://gracedb.ligo.org/apiweb/events/T153811>`__ (a Burst event)
- `External Swift GRB <https://gracedb.ligo.org/apiweb/events/E160846>`__ (a GRB event)

Creating new events
====================================

To create a new event, use the ``createEvent`` method on the client. In this
example, a new ``gstlal`` event is created in the ``Test`` group from a 
file on disk::

    from ligo.gracedb.rest import GraceDb
    client = GraceDb()

    event_file = "/path/to/coinc.xml"
    r = client.createEvent("Test","gstlal", event_file, search="LowMass")
    event_dict = r.json()
    graceid = event_dict["graceid"]

The server response includes a JSON representation of the event, and the
event dictionary can thus be obtained as shown. In this example, the event
dictionary is used to get the ``graceid`` of the new event. 

.. NOTE::
    In order to create events in a group other than ``Test``, the user must
    be explicitly authorized. Thus, events in the ``CBC`` or ``Burst`` groups, 
    for example, can only be created by authorized users. For more information
    on authorization, see :ref:`auth`.

Now suppose that a subsequent analysis has updated the values in the original
``coinc.xml`` file. We can *replace* the original event since we know the 
``graceid``::

    new_event_file = "/path/to/new_coinc.xml"
    r = client.replaceEvent(graceid, new_event_file)

This has the effect of updating the values of the various database fields, but
the original version of the event file is kept and can be found in the full
event log.

Annotating events
======================================

As discussed in the :ref:`annotation_models` section, the term refers to pieces of 
information added to an event after the time of its creation. Most commonly,
these take the form of event log messages or electromagnetic observation
records (see :ref:`create_emobservation`). The following demonstrates how to 
add a log message to an existing event::

    from ligo.gracedb.rest import GraceDb
    client = GraceDb()

    graceid = 'T160779'
    message = 'This is a test of the emergency commenting system.'
    filename = '/path/to/my_plot.png'

    r = client.writeLog(graceid, message, filename, tagname='analyst_comments')

In this example, a plot is uploaded to the log messages of event 
``T160779`` with a text comment. The new log message is also tagged with
the ``analyst_comments`` tag, which displays the plot and comment in a 
special section for comments from (human) data analysts. The tag name
can actually be anything the user wants, but only a limited list of tags
are *blessed* in the sense that they affect the display of information.
For a reminder of which tags are blessed see :ref:`annotation_models`.

Tags can also be added and removed from existing annotations. See the
docstrings for the client methods ``createTag`` and ``deleteTag``.

Applying labels
====================================

To add a label to an event, the ``graceid`` of the event and the name
of the label must be known::

    from ligo.gracedb.rest import GraceDb
    client = GraceDb()

    graceid = 'T160779'
    label_name = 'DQV' # meaning data quality veto

    r = client.writeLabel(graceid, label_name)

Care should be taken when applying labels to non-test events, since this
affects the sending of alerts related to potential electromagnetic followup.
The following labels are currently in active use:

* ``INJ``: event results from an injection
* ``DQV``: data quality veto
* ``EM_READY``: approved for EM followup
* ``PE_READY``: parameter estimation results available
* ``H1OPS``, ``L1OPS``: IFO operator signoff requested
* ``H1OK``, ``L1OK``: IFO operator certifies the detector state *okay*
* ``H1NO``, ``L1NO``: detector state *not okay* at event time
* ``ADVREQ``: EM followup advocate signoff requested
* ``ADVOK``: EM followup advocate approves event
* ``ADVNO``: EM followup advocate rejects event

The following labels were added August 2016 in order to add new functionality to 
approval_processor:

* ``EM_Throttled``: event ignored due to too many submissions by corresponding pipeline
* ``EM_Selected``: most promising candidate out of set for single physical event
* ``EM_Superseded``: event passed over due to other more-promising candidate for same event. 

.. _command_line_client:

Coping with request rate limits
=====================================

GraceDB limits any individual user to no more than 1 event creation request or
10 annotation requests per second. This is to avoid situations where an
automated data analysis pipeline malfunctions and sends huge rates of requests
to GraceDB, crashing the server. If a user's request is *throttled* in this
way, the server returns a response with HTTP status ``429`` and reason ``TOO
MANY REQUESTS``. The recommended wait time is also included in the message, and
is available through the ``retry-after`` when using the GraceDB REST client. If
you have reason to believe that your request may be throttled, you can wrap it
in a ``while`` loop in the following way::

    from ligo.gracedb.rest import GraceDb, HTTPError
    import time
    import json

    gracedb = GraceDb()
    graceid = 'T123456'

    success = False
    while not success:
        try:
            r = gracedb.writeLog(graceid, "Hello, this is a log message.")
            success = True
        except HTTPError, e:
            try:
                rdict = json.loads(e.message)
                if 'retry-after' in rdict.keys():
                    time.sleep(int(rdict['retry-after']))
                    continue
                else:
                    break
            except:
                break

Using the command-line client
=====================================

The GraceDB command-line client, ``gracedb``, is essentially a thin 
wrapper on the Python client. The examples above could be repeated 
with the command-line client as follows (assuming ``bash``):: 

    # Create the new event and store the uid
    GRACEID="$(gracedb Test gstlal LowMass /path/to/coinc.xml)"

    # Replace the event
    gracedb replace $GRACEID /path/to/new_coinc.xml

    # Annotate an event with a plot
    COMMENT="This is a test of the emergency commenting system."
    gracedb --tag-name=analyst_comments upload T160779 /path/to/my_plot.png $COMMENT

    # Label an event
    gracedb label T160779 DQV

Type ``gracedb -h`` for detailed help with the command-line client.

.. _coding_against_api:

Coding against the GraceDB REST API
=======================================================

Some users may wish to code directly against the GraceDB REST API rather
than use the Python or command-line clients. In order to do this, the user
will need to know which resources are exposed by which URLs, and which HTTP
methods those URLs allow. Fortunately, the 
`Django REST Framework <http://www.django-rest-framework.org>`__ (on which
the GraceDB API is built) provides
a convenient *browseable* version of the API which serves as a reference. 
The root of the API can be found here:

`https://gracedb.ligo.org/apiweb/ <https://gracedb.ligo.org/apiweb/>`__

A glance at the upper-right hand corner shows that this URL supports only
``OPTIONS`` and ``GET``. The body is a collection of JSON information provided
by the root resource, including ``links``. One of these links points to the
event list resource:

`https://gracedb.ligo.org/apiweb/events/ <https://gracedb.ligo.org/apiweb/events/>`__

which also supports ``POST`` (see the bottom of the page). New events are 
created by ``POST``-ing to the event list resource. This results in a new
event with a unique URL. If the parameters of the event change, the event
can be replaced by a ``PUT`` request to that same event URL with the replacement
data in the body. In a similar manner,
new log messages are created by ``POST``-ing to the event log list associated
with a particular event. The data expected by these target URLs is not yet
documented here. However, the source code of the GraceDB Python client 
can be consulted for examples.

