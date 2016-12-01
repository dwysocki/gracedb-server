==========================
Data models
==========================

What characterizes an event?
=====================================

The different types of events in GraceDB are distinguished by the following parameters:

- ``Group``: the working group responsible for finding the candidate
    - values: ``CBC``, ``Burst``, ``External``, ``Test`` 
- ``Pipeline``: the data analysis software tool used make the detection 
    - values: ``MBTAOnline``, ``CWB``, ``gstlal``, ``gstlal-spiir``, ``HardwareInjection``, ``Fermi``, ``Swift``, ``SNEWS``, ``LIB``
- ``Search``: the search activity which led to the detection 
    - values: ``AllSky``, ``AllSkyLong``, ``LowMass``, ``HighMass``, ``GRB``, ``Supernova``, ``MDC``

An individual "event stream" is specified by setting the values of these three 
parameters.  For example, choosing ``Group=CBC, Pipeline=gstlal, and Search=LowMass`` 
selects the event stream consisting of low-mass inspiral events 
detected by the gstlal pipeline from the CBC group. This framework was chosen 
in order avoid situations where events from different sources would overlap in searches
and alerts. 

Base event model
====================================

In addition to the three parameters described above, there are additional
common attributes for all events. These are

- ``submitter``: the user who submitted the event
- ``created``: the time at which the event was created
- ``instruments``: the interferometers involved in the detection
- ``far``: the false alarm rate in Hz
- ``gpstime``: the time at which the event occurred (a.k.a. "Event time")

The base event class was created with GW events in mind, so not all of the fields
will be applicable for any given event. (For example, ``instruments`` and ``far``
do not apply to a Swift GRB event.)

Event subclasses
====================================

Most events also have pipeline-specific attributes, and these are reflected in event
subclasses. For example, the ``gstlal`` pipeline produces an estimate for the chirp
mass, which is represented in the ``CoincInspiral`` event subclass. The following table 
shows the different subclasses with selected attributes:

.. raw:: html

    <div id="subclasses_table"></div>

.. _annotation_models:

Annotations
=======================

*Annotations* are pieces of information about an event that that are added
after the event is created. They are often the results of followup processes,
but are sometimes also provided by the same data analysis pipeline that
initially generated the event. The most common type of annotation is an *event
log message* with the following fields:

- ``submitter``: the user who created the log message
- ``created``: the time at which the log message was created
- ``filename``: the name of the attached file (if applicable)
- ``file_version``: the specific version of the file for this message
- ``comment``: the log message text

If the uploaded file is an image, it is displayed along with the comment in the
GraceDB event page. Log messages can also be *tagged* in order to give other
users an idea of the thematic category to which the message belongs. Users can
invent arbitrary tags, but the following set have a special status, as they
affect the display of information in the event page (i.e., the are
*"blessed"*):

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

Other types of annotations are labels, VOEvent objects, and EM observation records.
