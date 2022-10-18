===================================
Querying for events and superevents
===================================

Introduction
===============================================

This section gives an introduction to searches in GraceDB.
Searches can be done from the "Search" and "Latest" pages in the web interface or through the API when using the ``ligo-gracedb`` client package.
In the web interface, use the dropdown menu to set the search type (superevent or event).
When doing a search through the API with the client package, use the ``events()`` and ``superevents()`` methods to query for events and superevents, respectively.

Queries sometimes have a keyword, which may or may not be required.
In general, a query looks like ``keyword: value``.
Multiple attributes can be included in a query (ex: ``key1: val1 key2: val``).
The sections below show different attributes that can be queried on and the corresponding syntax.

Some information on combining queries is provided at the end.


Event queries
=============
**NOTE:** clicking the 'Get neighbors' checkbox will result in an additional neighbors query for each item in the search results, and the neighbors are thus shown in the results table. However, this causes the overall query to take longer, which is why it is un-checked by default.

By instruments
--------------
Order matters, because the instruments are stored in the database as a string.
Examples:

- ``instruments: "H1,L1,V1"``
- ``instruments: "V1,L1"``

By false alarm rate
-------------------
- ``far < 1e-7``
- ``far: 3.6823e-4``
- ``far >= 2e-9``

By event attributes
-------------------
Relational and range queries can be made on selected event attributes.
Examples:

- ``singleinspiral.mchirp >= 0.5 & singleinspiral.eff_distance in 0.0,55``
- ``(si.channel = "DMT-STRAIN" | si.channel = "DMT-PAIN") & si.snr < 5``
- ``mb.snr in 1,3 & mb.central_freq > 1000``

Attributes in the common event object (e.g. ``gpstime``, ``far``, ``instruments``) do not need qualifiers.
Attributes specific to inspiral or burst events, for example, require qualification.
Abbreviations are available: ``si`` for ``singleinspiral``, ``ci`` for coincinspiral and ``mb`` for ``multiburst``.

By GPS time
-----------
Specify an exact GPS time, or a range.
Integers will be assumed to be GPS times, making the ``gpstime`` keyword optional.
Examples:

- ``899999000 .. 999999999``
- ``gpstime: 899999000.0 .. 999999999.9``

By creation time
----------------
Creation time may be indicated by an exact time or a range.
Date/times are in the format ``2009-10-20 13:00:00`` (must be UTC).
If the time is omitted, it is assumed to be ``00:00:00``.
Dates may also consist of certain variants of English-like phrases.
The ``created`` keyword is optional.
Examples:

- ``created: 2009-10-08 .. 2009-12-04 16:00:00``
- ``yesterday..now``
- ``created: 1 week ago .. now``

.. warning::
    Due to a bug in GraceDB, it is recommended that you always include the
    ``created`` keyword, as some queries fail without it.


By graceid
----------
Graceids can be specified either individually, or as a range.
The ``gid`` keyword is optional.
Examples:

- ``gid: G2011``
- ``G2011 .. G3000``
- ``G2011 G2032 G2033``

By group, pipeline, and search
------------------------------
The ``group``, ``pipeline``, and ``search`` keywords are optional.
Names are case-insensitive.
Note that events in the Test group and MDC search will not be shown unless explicitly requested.
Examples:

- ``CBC Burst``
- ``group: Test pipeline: cwb``
- ``Burst cwb search: AllSky``

By label
--------
You may search for events with a particular label or set of labels.
The ``label`` keyword is optional.
Label names can be combined with binary AND: '&' or ',' or binary OR: '|'.
For N labels, there must be exactly N-1 binary operators (parentheses are not allowed).
Additionally, any of the labels in a query string can be negated with '~' or '-'. 
Examples:

- ``label: INJ``
- ``EM_READY & ADVOK``
- ``H1OK | L1OK & ~INJ & ~DQV``

See :ref:`labels` for a list of current labels.

By submitter
------------
To specify events from a given submitter, indicate the name of the submitter in **double quotes**.
The ``submitter`` keyword is optional.
While LIGO user names are predictable, most events are submitted through robot accounts and are not as predictable.
This is probably a defect that ought to be remedied.
Examples:

- ``"waveburst"``
- ``submitter: "joss.whedon@ligo.org"``

By superevent status
--------------------
Use the ``in_superevent`` keyword to specify events which are/are not part of any superevent.
Use the ``superevent`` keyword to specify events which are part of a specific superevent.
Use the ``is_preferred_event`` keyword to specify events which are/are not preferred events for any superevent.
Examples:

- ``in_superevent: True``
- ``in_superevent: False``
- ``superevent: S180525c``
- ``is_preferred_event: True``
- ``is_preferred_event: False``


Superevent queries
==================
Many of the queries for superevents are identical to that of events.
Only production superevents are returned by default.
See :ref:`superevent_query_category` for information on specifying Test or MDC superevents.


By id
-----
The keywords ``id`` or ``superevent_id`` are optional.
You can search by a superevent's S-type ID or its GW ID (if it has one).
See :ref:`superevent_date_ids` for more information on superevent IDs.
Examples:

- ``id: S180525a``
- ``superevent_id: S170817b``
- ``GW180428C``
- ``TS181212xz``


.. _superevent_query_category:

By category
-----------
Specify a superevent category (Production, Test, or MDC).
Only production superevents are returned by default.
The keyword ``category`` is optional.
Examples:

- ``Test``
- ``category: MDC``

By GPS time
-----------
Same as for event queries, with keywords ``gpstime`` or ``t_0``.

By other time attributes
------------------------
Queries based on the ``t_start`` and ``t_end`` attributes are also available and require the corresponding keywords.
Examples:

- ``t_start: 899999000``
- ``t_end: 899999000.0 .. 900000000.0``


By preferred event graceids
---------------------------
Specify an event graceid or range of event graceids with keyword ``preferred_event`` to get all superevents with corresponding preferred events.
Examples:

- ``preferred_event: G123456``
- ``preferred_event: G123456 .. G123500``


By event graceids
-----------------
Specify a graceid or range of graceids with keyword ``event`` to get all superevents which contain the corresponding event(s).
Examples:

- ``event: G123456``
- ``event: G123456 .. G123500``

By GW status
------------
Query for superevents which are confirmed as GWs or not with the ``is_gw`` keyword.
Examples:

- ``is_gw: True``
- ``is_gw: False``

By creation time
----------------
Same as for events.

By submitter
------------
Same as for events.

By label
--------
Same as for events.

By public status
----------------
Use the ``is_public`` or ``is_exposed`` keywords.
Examples:

- ``is_public: True``
- ``is_exposed: True``

Or, just add either "public" or "internal" to your query.

By preferred event FAR
----------------------
Examples:

- ``far < 1e-5``
- ``FAR >= 0.01``
- ``far in 1e-7, 2.5e-6``


Combining queries
=================
Queries can be combined by separating them with a space.
This effectively "AND"s them.
Do not use binary operators like '&' or '|' except between labels in a label-based query or in a query on selected event attributes (see examples above).
