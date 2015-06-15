==========================
Data models
==========================

What characterizes an event?
=====================================

The different types of events in GraceDB are distinguished by the following parameters:

- ``Group``
    the working group responsible for finding the candidate
- ``Pipeline``
    the data analysis software tool used make the detection 
- ``Search``
    the search activity which led to the detection (often linked to a specific
    astrophysical target, such as low-mass binaries)

Specifying the values of these three parameters has the effect of isolating
an "event stream," e.g., *low-mass inspiral events detected by the gstlal 
pipeline in the CBC group*. These categories were chosen in order avoid 
situations in which events from different sources would overlap in searches
and alerts. 

The existing values for ``Group``, ``Pipeline``, and ``Search`` are as follows:
            
.. Acknowledge slippage in the categories

Base event model
====================================

.. In addition to the three parameters described above, there are additional
.. common attributes for all events. These are

Under construction.


Event subclasses
====================================

Under construction.

.. _annotation_models:

Annotations
=======================

.. explain what is an annotation

.. explain about tags and blessed tags... need subsection?

Under construction.
