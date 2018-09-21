==========================
Using the web interface
==========================

The GraceDB web interface is intended primarily for "read" operations (i.e., searching for and viewing events), whereas the REST interface (discussed in :ref:`rest_interface`) is used for both "read" and "write" operations.
Thus, new events are ordinarily created via the REST interface, but viewed with the
web interface.
This section focuses on the latter.

Searching for events and superevents
====================================

The search form can be found by clicking on "SEARCH" in the top navigation menu.
Use the dropdown menu to select whether you want to search for events or superevents and enter your search criteria in the text box.

There are a variety of different attributes which can be used to search for events or superevents.
Click on the "Query help" link below the "Search" button for a list of attributes and examples.

Latest events and superevents
=============================

The "LATEST" page shows the most recent events or superevents (by submission time).
You can also do searches from this page.

Understanding the event detail page
===================================

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
  
At the bottom of the Event Log Messages section, there is a pane entitled "Full Event Log" which (when expanded) shows all of the annotations in reverse chronological order.
These individual entries are sometimes *tagged* as belonging to a particular category, and these tags are used to group entries into the thematic sections above.
Each entry in the full event log has a log message number, creation time, and user name to establish provenance.
The existing tags are also shown in the same column as the message itself, as is the form (which looks like a `+`) to add a new tag.
Users are free to create new tags for their own purposes (e.g., searching through annotations at some
later date), but only a pre-determined list of tags is used to create title pane sections.

For more on the GraceDB event page, see `this <https://www.youtube.com/watch?v=oIJE4dTISs4>`_ helpful video by Roy Williams, which is geared toward LV-EM users.
There also is a `companion video <https://www.youtube.com/watch?v=ydXUD9KIN98>`__ on the SkymapViewer.

Understanding the superevent detail page
========================================

The detail page for a superevent can be accessed similarly to an event page.
The content is analogous to that shown on the event page, although it contains information about the superevent in general, as well as a table summarizing the information about the superevent's preferred event.

Signing up for email or phone alerts (LVC only)
=======================================================

LVC users may set up email or phone notifications for events that come from specific pipelines and have specific labels.
This feature is available to LVC users only because the events are not vetted before the alert is sent out.
For non-LVC users, GCN will provide the equivalent functionality.
See the LV-EM `techinfo page <https://gw-astronomy.org/wiki/LV_EM/TechInfo>`__.) 

In order to sign up for an alert, you must first create a contact by clicking on "OPTIONS" in the navigation menu, and then "Create New Contact."
Follow the instructions on that page to add your contact information.
Next, return to the options page and click "Create New Notification".
This page allows you to set the criteria for alerts to be sent to the contact that you created in the previous step.

These are currently only available for events, but may be extended to superevents in the future.
