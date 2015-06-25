==========================
Using the web interface
==========================

The GraceDB web interface is intended primarily for "read" operations (i.e., searching for
and viewing events), whereas the REST interface (discussed in
:ref:`rest_interface`) is used for both "read" and "write" operations. Thus,
new events are ordinarily created via the REST interface, but viewed with the
web interface. This section focuses on the latter.

Searching for events
==========================

The search form can be found by clicking on "SEARCH" in the top navigation menu.
Many different types of searches are available, and they can be combined with
each other in various ways:

- by event attributes:
    - ``instruments = "H1,L1,V1" & far < 1e-7``
    - ``coincinspiral.mass < 5 & single_inspiral.eff_distance in 100,300``
- by GPS time or range 
    - ``gpstime: 999999999``
    - ``899999000..999999999``
- by event creation time
    - ``created: 2009-10-08 .. 2009-12-04 16:00:00``
    - ``yesterday .. now``
- by specific graceid or range
    - ``G125700``
    - ``G120000 .. G13000``
- by group, pipeline, and search (names are case insensitive)
    - ``cbc gstlal lowmass``
    - ``group: burst``
    - ``test hardwareinjection``
- by label
    - ``label: INJ``
    - ``EM_READY PE_READY``
- by submitter (note the required straight quotes)
    - ``"waveburst"``
    - ``submitter: "gracedb.processor"``
    - ``submitter: "joss.whedon@ligo.org"``

Notice how pipeline-specific attributes, such as the chirp mass, need to be
qualified with the type of event (e.g., ``coincinspiral.mchirp`` in queries
rather than just ``mchirp``). Keywords in the searches (e.g., ``gpstime``,
``created``, etc.) are usually optional but are sometimes useful for
disambiguation.

Understanding the event page
===============================

Clicking on an event in the search results table leads to an individual event page.
These pages are broken up into several sections (in order from top to bottom):

- **Basic info**: Attributes that are common to all event types, including the graceid (UID),
  group, pipeline, and search. A link to the associated data files is also found here.
- **Pipeline-specific attributes**: Tables of attributes associated with a specific search
  pipeline (e.g., the chirp mass for a CBC event, or the central frequency for a burst event)
- **Neighbors**: Surrounding events within a specified time window. (Note that the time window is adjustable
  by clicking on it.) These events are neighbors in the temporal sense only (i.e., not spatial).
- **Event log messages**: This is the largest section, consisting of annotations broken up into
  thematic sections that may be collapsed and expanded.
  
At the bottom of the Event Log Messaages section, there is a pane entitled
"Full Event Log" which (when expanded) shows all of the annotations in reverse
chronological order. These individual entries are sometimes *tagged* as
belonging to a particular category, and these tags are used to group entries
into the thematic sections above. Each entry in the full event log has a log
message number, creation time, and user name to establish provenance.  The
existing tags are also shown in the same column as the message itself, as is
the form (which looks like a `+`) to add a new tag. Users are free to create
new tags for their own purposes (e.g., searching through annotations at some
later date), but only a pre-determined list of tags is used to create title
pane sections.

For more on the GraceDB event page, see 
`this <https://www.youtube.com/watch?v=oIJE4dTISs4>`_  helpful video
by Roy Williams, which is geared toward LV-EM users.   There also is a 
`companion video <https://www.youtube.com/watch?v=ydXUD9KIN98>`__ on the SkymapViewer.

Signing up for email alerts (LVC only)
=======================================================

LVC users may set up email notifications for events that come from specific
pipelines and have specific labels. (This feature is available to LVC users
only because the events are not vetted before the alert is sent out. For
non-LVC users, GCN will provide the equivalent functionality.  See the LV-EM 
`techinfo page <https://gw-astronomy.org/wiki/LV_EM/TechInfo>`__.) 

In order to sign up for an email alert, you must first create a contact by
clicking on "OPTIONS" in the navigation menu, and then "Create New Contact."
Add an email address and description (such as "uni email account", or "my cell", 
etc.).  Note that many mobile carriers allow users to receive emails via 
text (e.g., 1234567890@vtext.com).
Next, return to the options page and click "Create New Notification",
which allows you to select a label and pipeline to track, as well as a 
contact.  
