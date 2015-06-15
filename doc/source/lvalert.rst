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

.. tell them how to get the names of all of the nodes

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

.. examples of the different types
.. demonstration of how to parse

.. what kind of alert does a replacement trigger?

Further reading on LVAlert
=====================================================

.. links to LVAlert documentation

Further information on using LVAlert can be found on the
`LVAlert Project Page <https://www.lsc-group.phys.uwm.edu/daswg/projects/lvalert.html>`_
and the `LVAlert Howto <https://www.lsc-group.phys.uwm.edu/daswg/docs/howto/lvalert-howto.html>`_.
