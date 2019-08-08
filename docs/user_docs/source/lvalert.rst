======================================
LVAlert notifications (LVC users only)
======================================

Introduction
============
LVAlert (LIGO-Virgo Alert system) is an XMPP-based messaging platform used within the LVC.
This document will describe how GraceDB uses LVAlert, which nodes it manages and publishes to, and the content of LVAlert messages sent by GraceDB.
.. GraceDB uses `LVAlert <https://wiki.ligo.org/Computing/DASWG/LVAlert>`__ to send alerts to listeners within the LVC when.

Some helpful resources for installing and configuring LVAlert are:

- Main ligo-lvalert `documentation <https://lscsoft.docs.ligo.org/lvalert/index.html>`__
- ligo-lvalert `user guide <https://lscsoft.docs.ligo.org/lvalert/guide.html>`__
- :ref:`Tutorial<responding_to_lvalert>` on setting up LVAlert and configuring your listener.


LVAlert and GraceDB
===================
Generally speaking, GraceDB uses LVAlert to send "push" notifications about different actions that may be taken on the service.
Users can subscribe to different nodes (more below) to receive these notifications, filter their content, and optionally trigger follow-up processes, like data quality checks, parameter estimation, and more.
The content of an LVAlert message is designed to convey actionable information about a state change in GraceDB, including event creation, annotation, and other actions.

.. NOTE::
    An LVAlert message is sent out for *any* new event or annotation that arrives in the GraceDB database.
    This means that message volumes may be very high under certain circumstances, and listeners should be constructed to appropriately filter the messages.


LVAlert nodes managed by GraceDB
================================
By running ``lvalert_listen``, you will receive messages over all **nodes** to which you are subscribed.
There are two types of nodes to which GraceDB broadcasts alerts: event nodes and superevent nodes.


Event nodes
-----------
Event node names consist of at least two elements::

    <group_name>_<pipeline_name>

In other words, the (lower-cased) names of the Group and Pipeline separated by an underscore.
For example, the node ``burst_cwb`` would catch all messages relating to events in the Burst group from the cWB pipeline.
One can also specify the search name::

    <group_name>_<pipeline_name>_<search_name>

which has the effect of narrowing down the messages to only those related to a specific search.
For example, the node ``burst_cwb_allsky`` will contain messages relating to the AllSky search, but not the MDC search.

It is important to note that GraceDB will send an LVAlert to all nodes which match the parameters of the event in question.
For example, the creation of a Burst-cWB-AllSky event will result in messages being sent to the ``burst_cwb_allsky`` node, as well as the more generic ``burst_cwb`` node.
This feature allows the user to filter according to search by specifying different LVAlert processing scripts for different nodes.


Superevent nodes
----------------
There are only three superevent nodes; one for each category of superevent:

- ``superevent``
- ``test_superevent``
- ``mdc_superevent``

Most users will be interested in the ``superevent`` node in order to receive LVAlerts about real GW candidates.


Contents of LVAlerts sent by GraceDB
====================================
GraceDB sends LVAlert messages as a JSON-encoded dictionary.
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
