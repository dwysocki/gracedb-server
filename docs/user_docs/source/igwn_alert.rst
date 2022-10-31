=========================================
igwn-alert notifications (LVK users only)
=========================================

Introduction
============
igwn-alert is a Kafka-based messaging platform used within the LVK.
This document will describe how GraceDB uses igwn-alert, which topics it manages and publishes to, and the content of igwn-alert messages sent by GraceDB. GraceDB uses `igwn-alert <https://igwn-alert.readthedocs.io/>`__ to send alerts to listeners within the LVK when.

Some helpful resources for installing and configuring igwn-alert are:

- Main `igwn-alert client <https://igwn-alert.readthedocs.io/>`__
- igwn-alert `user guide <https://igwn-alert.readthedocs.io/en/latest/guide.html>`__
- `Tutorial <https://igwn-alert.readthedocs.io/en/latest/guide.html#responding-to-igwn-alert-messages>`__ on setting up igwn-alert and configuring your listener.


igwn-alert and GraceDB
======================
Generally speaking, GraceDB uses igwn-alert to send "push" notifications about different actions that may be taken on the service.
Users can subscribe to different topics (more below) to receive these notifications, filter their content, and optionally trigger follow-up processes, like data quality checks, parameter estimation, and more.
The content of an igwn-alert message is designed to convey actionable information about a state change in GraceDB, including event creation, annotation, and other actions.

.. NOTE::
    An igwn-alert message is sent out for *any* new event or annotation that arrives in the GraceDB database.
    This means that message volumes may be very high under certain circumstances, and listeners should be constructed to appropriately filter the messages.


igwn-alert topics managed by GraceDB
====================================
By running the ``igwn-alert`` command-line tool, you will receive messages over all **topics** to which you have a listen permission, analogous to a subscription.
There are two types of topics to which GraceDB broadcasts alerts: event topics and superevent topics.

Instance Groups
---------------

The following topic names are universal across each instance of GraceDB
(production, playground, test). However, each instance's topics names are
prepended by the instance name (gracedb, gracedb-playground, gracedb-test) and a
".". For example, the ``cbc_gstlal`` topic for GraceDB Playground is listed in
the subscription interface as:

    ``gracedb-playground.cbc_gstlal``

And can be evoked in the command line tool by specifying the instance with the
optional ``group`` flag as in the following command:

    ``igwn-alert -g gracedb-playground listen cbc_gstlal``



Event topics
------------
Event topic names consist of at least two elements::

    <group_name>_<pipeline_name>

In other words, the (lower-cased) names of the Group and Pipeline separated by an underscore.
For example, the topic ``cbc_gstlal`` would catch all messages relating to events in the CBC group from the gstlal pipeline.
One can also specify the search name::

    <group_name>_<pipeline_name>_<search_name>

which has the effect of narrowing down the messages to only those related to a specific search.
For example, the topic ``cbc_gstlal_allsky`` will contain messages relating to the AllSky search, but not the MDC search.

It is important to note that GraceDB will send an igwn-alert to all topics which match the parameters of the event in question.
For example, the creation of a Burst-cWB-AllSky event will result in messages being sent to the ``burst_cwb_allsky`` topic, as well as the more generic ``burst_cwb`` topic.
This feature allows the user to filter according to search by specifying different igwn-alert processing scripts for different topics.


Superevent topics
-----------------
There are only three superevent topics; one for each category of superevent:

- ``superevent``
- ``test_superevent``
- ``mdc_superevent``

Most users will be interested in the ``superevent`` topic in order to receive igwn-alerts about real GW candidates.


Contents of igwn-alerts sent by GraceDB
=======================================
GraceDB sends igwn-alert messages as a JSON-encoded dictionary.
This dictionary contains the following keys:

- ``alert_type``: short string representing the action which triggered the alert.  Examples: ``new``, ``update``, ``label_added``, etc.  All alert types are shown in the tables below.
- ``data``: a dictionary representing the relevant object (label, log message, etc.)
- ``object``: a dictionary representing the corresponding "parent" object (i.e., the event or superevent which a log, label, etc. is attached to).
- ``uid``: the unique ID of the relevant event or superevent

Below, we describe the alert contents in more detail.
Examples of the various ``data``/``object`` dictionaries are available in :ref:`models`.
See :ref:`below<example_permissions_list>` for one additional example (list of permissions).


Event alerts
------------
For alerts related to events, the following things are always true:

- ``uid`` is always the event's ``graceid`` (example: G123456).
- ``object`` is always a dictionary corresponding to the event which is affected by the label, log, VOEvent, etc.

The following table shows the ``alert_type`` and ``data`` for different actions:

+-------------------------+---------------------------------+---------------------------------------------------------+
| ``alert_type``          | ``data``                        | Occurs when                                             |
+=========================+=================================+=========================================================+
| added_to_superevent     | event dictionary                | event is added to a superevent                          |
+-------------------------+---------------------------------+---------------------------------------------------------+
| embb_event_log          | EMBB event log dictionary       | EM bulletin board event log is created for event        |
+-------------------------+---------------------------------+---------------------------------------------------------+
| emobservation           | emobservation dictionary        | EM observation is created for event                     |
+-------------------------+---------------------------------+---------------------------------------------------------+
| exposed                 | list of permission dictionaries | internal-only event is exposed to LV-EM                 |
+-------------------------+---------------------------------+---------------------------------------------------------+
| hidden                  | list of permission dictionaries | LV-EM viewable event is marked as internal-only         |
+-------------------------+---------------------------------+---------------------------------------------------------+
| label_added             | label dictionary                | label is added to event                                 |
+-------------------------+---------------------------------+---------------------------------------------------------+
| label_removed           | label dictionary                | label is removed from event                             |
+-------------------------+---------------------------------+---------------------------------------------------------+
| log                     | log dictionary                  | log message is added to event (may include file upload) |
+-------------------------+---------------------------------+---------------------------------------------------------+
| new                     | event dictionary                | event is created                                        |
+-------------------------+---------------------------------+---------------------------------------------------------+
| removed_as_preferred    | event dictionary                | event is no longer the preferred event for a superevent |
+-------------------------+---------------------------------+---------------------------------------------------------+
| removed_from_superevent | event dictionary                | event is removed from a superevent                      |
+-------------------------+---------------------------------+---------------------------------------------------------+
| selected_as_preferred   | event dictionary                | event is selected as preferred event for a superevent   |
+-------------------------+---------------------------------+---------------------------------------------------------+
| signoff_created         | signoff dictionary              | signoff is created for event                            |
+-------------------------+---------------------------------+---------------------------------------------------------+
| signoff_deleted         | signoff dictionary              | event signoff is deleted                                |
+-------------------------+---------------------------------+---------------------------------------------------------+
| signoff_updated         | signoff dictionary              | event signoff is updated                                |
+-------------------------+---------------------------------+---------------------------------------------------------+
| update                  | event dictionary                | event is "replaced" by upload of a new event file       |
+-------------------------+---------------------------------+---------------------------------------------------------+
| voevent                 | VOEvent dictionary              | VOEvent is created for event                            |
+-------------------------+---------------------------------+---------------------------------------------------------+


Superevent alerts
-----------------
For alerts related to superevents, the following things are always true:

- ``uid`` is always the superevent's ``superevent_id`` (example: S800106D).
- ``object`` is always a dictionary corresponding to the superevent which is affected by the label, log, VOEvent, etc.


The following table shows the ``alert_type`` and ``data`` for different actions:

+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| ``alert_type``          | ``data``                        | Occurs when                                                                                 |
+=========================+=================================+=============================================================================================+
| confirmed_as_gw         | superevent dictionary           | superevent is upgraded to GW status                                                         |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| embb_event_log          | EMBB event log dictionary       | EM bulletin board event log is created for event                                            |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| emobservation           | emobservation dictionary        | EM observation is created for superevent                                                    |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| event_added             | superevent dictionary           | an event is added to superevent                                                             |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| event_removed           | superevent dictionary           | an event is removed from superevent                                                         |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| exposed                 | list of permission dictionaries | internal-only superevent is exposed to LV-EM and public                                     |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| hidden                  | list of permission dictionaries | public superevent is marked as internal-only                                                |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| label_added             | label dictionary                | label is added to superevent                                                                |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| label_removed           | label dictionary                | label is removed from superevent                                                            |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| log                     | log dictionary                  | log message is added to superevent (may include file upload)                                |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| new                     | superevent dictionary           | superevent is created                                                                       |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| signoff_created         | signoff dictionary              | signoff is created for superevent                                                           |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| signoff_deleted         | signoff dictionary              | superevent signoff is deleted                                                               |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| signoff_updated         | signoff dictionary              | superevent signoff is updated                                                               |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| update                  | superevent dictionary           | superevent is updated (``t_start``, ``t_0``, ``t_end``, or ``preferred_event`` are changed) |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+
| voevent                 | VOEvent dictionary              | VOEvent is created for superevent                                                           |
+-------------------------+---------------------------------+---------------------------------------------------------------------------------------------+

.. _example_permissions_list:

Example: list of permission dictionaries
----------------------------------------
.. literalinclude:: dicts/permissions.list
  :language: JSON
