.. _models:

==========================
Data Models
==========================

What characterizes an event?
=====================================

The different types of events in GraceDB are distinguished by the following parameters:

- ``Group``: the working group responsible for finding the candidate
    - values: ``CBC``, ``Burst``, ``Detchar``, ``External``, ``Test`` 
- ``Pipeline``: the data analysis software tool used make the detection 
    - values: ``MBTA``, ``MBTAOnline``, ``CWB``, ``CWB2G``, ``gstlal``, ``pycbc``, ``spiir``, ``HardwareInjection``, ``Fermi``, ``Swift``, ``INTEGRAL``, ``AGILE``, ``SNEWS``, ``oLIB``, ``MLy``
- ``Search``: the search activity which led to the detection 
    - values: ``AllSky``, ``AllSkyLong``, ``LowMass``, ``HighMass``, ``GRB``, ``Supernova``, ``MDC``, ``BBH``, ``EarlyWarning``, ``IMBH``, ``SubGRB``, ``SubGRBTargeted``

An individual "event stream" is specified by setting the values of these three parameters.
For example, choosing ``Group=CBC``, ``Pipeline=gstlal``, and ``Search=LowMass`` selects the event stream consisting of low-mass inspiral events detected by the gstlal pipeline from the CBC group.
This framework was chosen in order avoid situations where events from different sources would overlap in searches and alerts. 

.. _base_event_model:

Base event model
----------------

In addition to the three parameters described above, there are additional common attributes for all events.
These are:

- ``submitter``: the user who submitted the event
- ``created``: the time at which the event was created
- ``instruments``: the interferometers involved in the detection
- ``far``: the false alarm rate in Hz
- ``gpstime``: the time at which the event occurred (a.k.a. "Event time")
- ``reporting_latency``: defined as the time difference between when an event lands
  on GraceDB (``created``) and the reported ``gpstime`` (in seconds)
- ``superevent``: the ``superevent_id`` of the event' parent superevent, if
  applicable
- ``superevent_neighbours``: superevents currently in GraceDB whose ``t_0`` is
  within a set time window of the event's ``gpstime`` (currently ± 100s). Value
  is a dictionary, whose key is the ``superevent_id`` and value is the
  :ref:`superevent dictionary<superevent_data_model>`

The base event class was created with GW events in mind, so not all of the fields will be applicable for any given event.
For example, ``instruments`` and ``far`` do not apply to a Swift GRB event.

Event subclasses
----------------

Most events also have pipeline-specific attributes, and these are reflected in event subclasses.
For example, the ``gstlal`` pipeline produces an estimate for the chirp mass, which is represented in the ``CoincInspiral`` event subclass.

.. _annotation_models:

Serialized events
-----------------------------
Event objects are serialized into JSON format in responses from the API and in igwn-alert messages.
Here, we show some examples for the different event subclasses.

CBC pipelines (gstlal, spiir, PyCBC, MBTAOnline)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: dicts/event_cbc.json
  :language: JSON
  :force:

CWB
~~~

.. literalinclude:: dicts/event_cwb.json
  :language: JSON

oLIB
~~~~

.. literalinclude:: dicts/event_olib.json
  :language: JSON


External
~~~~~~~~

.. literalinclude:: dicts/event_external.json
  :language: JSON


Superevents
===========

What is a superevent?
---------------------
In reality, what we called "events" above might be better characterized as "triggers", since different analysis pipelines may detect the same physical GW event and submit it to GraceDB.
In order to collect the information about a single physical event in one place, reduce the amount of follow-up processing needed, and issue alerts about only one GraceDB entry per physical event, we have created the "superevent" data model.

A `downstream process <https://rtd.igwn.org/projects/gwcelery/en/latest/index.html>`__ separate from GraceDB listens for event creations, analyzes their attributes, and determines how to aggregate events into superevents.

.. _superevent_data_model:

Data model
----------
The main attributes of the superevent data model are:

- ``superevent_id``: a unique date-based ID (Example: ``S180912b``; more information below in :ref:`superevent_date_ids`)
- ``gw_id``: a unique date-based ID only assigned to superevents which are confirmed GWs (Example: ``GW180915BC``; more information below in :ref:`superevent_date_ids`)
- ``category``: superevent category (``Production``, ``Test``, or ``MDC``); more information below in :ref:`superevent_categories` 
- ``gw_events``: list of graceids corresponding to Event objects which are part of this superevent and were submitted by GW analysis pipelines
- ``preferred_event``: the ``graceid`` of the superevent's preferred event
- ``preferred_event_data``: the :ref:`event dictionary<base_event_model>` of the
  superevent preferred event
- ``em_events``: list of graceids corresponding to Event objects which are part of this superevent and are in the "External" group (i.e., were observed by electromagnetic or neutrino telescopes)
- ``created``:  time at which the superevent was created
- ``submitter``: user who created the superevent
- ``t_start``: time corresponding to start of window for grouping events into this superevent
- ``t_end``: time corresponding to end of window for grouping events into this superevent
- ``t_0``: best estimate of time at which the GW event occurred

Serialized superevent
~~~~~~~~~~~~~~~~~~~~~

Here is an example of a superevent which has been serialized into a JSON:

.. literalinclude:: dicts/superevent.json
  :language: JSON


.. _superevent_categories:

Categories
----------

There are three categories of superevents:

- ``Production``: "real" superevents which correspond to potential GW events
- ``Test``: used for generic testing superevent creation, annotation, etc.
- ``MDC``: generated as part of the mock data challenge (MDC), which comprises a constant stream of events which are sent to GraceDB for testing by internal and LV-EM users

Each category of superevent may only contain events of the corresponding type; i.e., ``Production`` superevents may only contain production (G, E, and H-type) events, ``Test`` superevents may only contain test (T-type) events, and ``MDC`` superevents may only contain MDC (M-type) events.

Letter suffixes for superevent date-based IDs are also calculated independently for each superevent category (see :ref:`superevent_date_ids`).

.. _superevent_date_ids:

Date-based IDs
--------------

We generate IDs for superevents based on the date of their occurrence, at the time of creation.
These IDs have three parts:

- Prefix
- Six digit (``YYMMDD``) date string
- Letter suffix

A few examples are:

- ``S180920abc``
- ``TS180717b``
- ``GW170817A``

Prefix
~~~~~~

The prefix is determined by the superevent's "status" (is it marked as a "confirmed GW" or not) and its category.
A superevent's category will **never** change, but its status can, resulting in a prefix change.
When this happens, the superevent will be accessible (via URLs, the API, searches, etc.) by both its old and new IDs.

+----------------+--------------------+--------------+
| Category       | Not a confirmed GW | Confirmed GW |
+================+====================+==============+
| ``Production`` | S                  | GW           |
+----------------+--------------------+--------------+
| ``Test``       | TS                 | TGW          |
+----------------+--------------------+--------------+
| ``MDC``        | MS                 | MGW          |
+----------------+--------------------+--------------+

Date string
~~~~~~~~~~~

The date string is determined by the superevent's value for ``t_0`` at creation.
This is converted from GPS to UTC time and turned into a ``YYMMDD`` string.
Note that a superevent's ``t_0`` value may change as additional events are added to it, but this will not change the date string in the superevent's ID.

Because these date strings are only 6 digits, they are degenerate over a period of 100 years.
We currently define this period to run from 1980-01-01 00:00:00 UTC to 2079-12-31 23:59:59 UTC.

If GraceDB is still around at that point, we will probably have to switch to four-digit years.

Letter suffix
~~~~~~~~~~~~~

The letter suffix is determined by the chronological ordering of superevents observed on a given date by **creation time in GraceDB**, *not* by the occurence time of the actual GW event.
This is because a unique ID must be determined at creation time and it is not realistic to recalculate it every time a new superevent is created.

The letter suffix just corresponds to the superevent's number within this chronological ordering.
To be explicit: 1 = ``a``, 2 = ``b``, 27 = ``aa``, and so on.

This suffix is calculated **independently** for each category of superevent.
This means that the first ``Production`` superevent for a given date will have a suffix of ``a``, and so will the first ``Test`` superevent for that date.
In this case, ID uniqueness is preserved by the fact that these categories have different prefixes.

When a superevent is confirmed as a GW, a new letter suffix is determined based on how many superevents for the same date have already been confirmed as a GW.
Again, this is dependent on the chronological ordering of the time at which this confirmation action takes place, and not by the occurrence time of the actual GW event.
Uppercase letters are used for suffixes for confirmed GWs.

Example scenario
~~~~~~~~~~~~~~~~

Here's a hypothetical series of superevent creations occurring on March 31, 2018:

- A ``Production`` superevent is created at 12:00:00 UTC with a ``t_0`` corresponding to 11:30:00 UTC
- Another ``Production`` superevent is created at 12:05:00 with a ``t_0`` corresponding to 11:00:00 UTC
- A ``Test`` superevent is created at 12:10:00 with a ``t_0`` corresponding to 12:05:00 UTC
- A third ``Production`` superevent is created at 12:15:00 with a ``t_0`` corresponding to 10:00:00 UTC

The resulting set of superevent IDs will be:

+---------------------+---------------+----------------+---------------+
| Creation time (UTC) | ``t_0`` (UTC) | Category       | Superevent ID |
+=====================+===============+================+===============+
| 12:00:00            | 11:30:00      | ``Production`` | ``S180331a``  |
+---------------------+---------------+----------------+---------------+
| 12:05:00            | 11:00:00      | ``Production`` | ``S180331b``  |
+---------------------+---------------+----------------+---------------+
| 12:10:00            | 12:05:00      | ``Test``       | ``TS180331a`` |
+---------------------+---------------+----------------+---------------+
| 12:15:00            | 10:00:00      | ``Production`` | ``S180331c``  |
+---------------------+---------------+----------------+---------------+

Now let's say S180331b is confirmed as a GW at 13:00:00 UTC and S180331a is confirmed as a GW at 13:05:00 UTC.
This would result in the following superevent IDs:

+---------------------+---------------+----------------+---------------+
| Creation time (UTC) | ``t_0`` (UTC) | Category       | Superevent ID |
+=====================+===============+================+===============+
| 12:00:00            | 11:30:00      | ``Production`` | ``GW180331B`` |
+---------------------+---------------+----------------+---------------+
| 12:05:00            | 11:00:00      | ``Production`` | ``GW180331A`` |
+---------------------+---------------+----------------+---------------+
| 12:10:00            | 12:05:00      | ``Test``       | ``TS180331a`` |
+---------------------+---------------+----------------+---------------+
| 12:15:00            | 10:00:00      | ``Production`` | ``S180331c``  |
+---------------------+---------------+----------------+---------------+

Note that the "upgraded" superevents would still be accessible through the web interface, API calls, searches, etc. by **either** of their IDs.

Annotations
=======================

*Annotations* are pieces of information about an event or superevent that that are added after the event or superevent is created.
They are often the results of followup processes, but are sometimes also provided by the same data analysis pipeline that initially generated the event.
The most common type of annotation is an *log message* with the following fields:

- ``submitter``: the user who created the log message
- ``created``: the time at which the log message was created
- ``filename``: the name of the attached file (if applicable)
- ``file_version``: the specific version of the file for this message
- ``comment``: the log message text

If the uploaded file is an image, it is displayed along with the comment in the GraceDB event or superevent page.
Log messages can also be *tagged* in order to give other users an idea of the thematic category to which the message belongs.
Users can invent arbitrary tags, but the following set have a special status, as they affect the display of information in the event page (i.e., they are *"blessed"*):

- ``analyst_comments``: Analyst Comments
- ``em_follow``: EM Followup
- ``psd``:  Noise Curves
- ``data_quality``: Data Quality
- ``sky_loc``: Sky Localization
- ``background``: Background Information
- ``ext_coinc``: External Coincidence
- ``strain``: Strain Data
- ``tfplots``: Time-Frequency Info
- ``pe``: Parameter Estimation
- ``sig_info``: Significance Info
- ``audio``: Sound Files

Other types of annotations are labels, VOEvent objects, EM observation records, and signoffs.

Serialized annotations
----------------------

Here we show some examples of annotations which have ben serialized into JSON format.
These annotations are basically identical whether they are attached to an event or superevent, and these examples show some of each case.

Log
~~~
.. literalinclude:: dicts/log.json
  :language: JSON

Label
~~~~~
.. literalinclude:: dicts/label.json
  :language: JSON

Signoff
~~~~~~~
.. literalinclude:: dicts/signoff.json
  :language: JSON

Notes:
- ``status``: can be "OK" or "NO"
- ``signoff_type``: can be "ADV" (EM advocate) or "OP" (instrument control room operator)
- ``instrument``: two-letter instrument code, like "H1", "L1", "V1", etc.  For advocate signoffs, this is an empty string.

EMObservation
~~~~~~~~~~~~~
.. literalinclude:: dicts/emobservation.json
  :language: JSON

VOEvent
~~~~~~~
.. literalinclude:: dicts/voevent.json
  :language: JSON
