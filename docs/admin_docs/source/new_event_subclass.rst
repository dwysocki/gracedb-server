.. _new_event_subclass:

==================================
Creating a new event subclass
==================================

Why?
==========
Most events in GraceDB have attributes that go beyond those in the base
event class. If a new pipeline is developed, and the data analysts wish
to upload events to GraceDB, these events will often have attributes
that do not correspond to any of the existing event subclasses. In this
case, you will need to create a new event subclass. In addition, you'll
have to tailor the representation of the event, both in the web browser
and REST interfaces, to account for the presence of the new attributes.
This section of the documentation is meant to point out the places where
changes in the code will be required and to suggest a workflow. 
The workflow aspect, however, is idiosyncratic, and you should feel
free to adapt as you see fit.

The pipeline
============

Most often, a new event subclass is necessitated by the desire to support
events from a new pipeline. Thus we will need a new pipeline object and
appropriate permissions to populate it. Instructions for these steps are
given in :ref:`new_pipeline`. As in those instructions, we will assume
that our new pipeline is named ``newpipeline``.

The model and migration
=======================

You will need to understand the attributes of the events the pipeline uploads.
Importantly, you should ask the pipeline developers for an example of the 
type of file they plan to upload. Then you will be able to decide on which
attributes are to be added in the event subclass. 

In creating the new model, it will likely be helpful to compare with the
existing event subclasses: ``GrbEvent``, ``CoincInspiralEvent``, 
``MultiBurstEvent``, ``LalInferenceBurstEvent``, and ``SimInspiralEvent``.
Three of these (``CoincInspiralEvent``, ``MultiBurstEvent``, and 
``SimInspiralEvent``) were named according to the the names of the 
``ligolw`` tables from which the event information is drawn. The 
``LalInferenceBurstEvent`` class is named for the pipeline from which the
events come (Omicron-LIB). Finally, the ``GrbEvent`` class is named based
on the astrophysical transient being represented (as these events come
through multiple pipelines). For your new subclass, you may wish to name
it after the pipeline (e.g., ``NewPipelineEvent``), or you may decide to
go with something more physical if you suspect that more than one pipeline
will eventually be producing events with this same set of attributes.
For the sake of argument, we'll assume the former in what follows.

You'll want to begin by going to the GraceDB test instance and checking out
a new branch, such as ``my_new_pipeline_branch`` or something.
Creating the new event subclass is as simple as adding a new model in 
``gracedb/gracedb/models.py``::

    class NewPipelineEvent(Event):
        attribute1 = models.FloatField(null=True)
        attribute2 = models.IntegerField(null=True)
        attribute3 = models.CharacterField(max_length=50, blank=True, default="")
        attribute4 = ... 

This new model will correspond to a new database table: ``gracedb_newpipelineevent``.
To make the necessary changes to the database, we'll use a migration.
As the ``gracedb`` user::

    cd
    source djangoenv/bin/activate
    cd gracedb
    ./manage.py makemigrations --name added_newpipelineevent gracedb

Check that the new migration is present and has yet to be applied, and then apply it::

    ./manage.py migrate gracedb --list
    ./manage.py migrate gracedb

Finally commit the ``models.py`` file and the migration file on our new branch:

    git add gracedb/models.py
    git add gracedb/migrations/00XX_added_newpipelineevent.py
    git commit -m "New pipeline model and migration."

View logic for event creation
=============================

Now that we've got our new pipeline and event subclass, we can start putting in the
logic to create the events. The first place to look is the utility function
``_createEventFromForm`` in ``gracedb/view_logic.py``. There is an unwieldy ``if``
statement here that creates a new event object instance according to the 
pipeline. We'll need to add our new one::

    # Create Event
    if pipeline.name in ['gstlal', 'gstlal-spiir', 'MBTAOnline', 'pycbc',]:
        event = CoincInspiralEvent()
    elif pipeline.name in ['Fermi', 'Swift', 'SNEWS']:
        event = GrbEvent()
    elif pipeline.name in ['CWB', 'CWB2G']:
        event = MultiBurstEvent()
    elif pipeline.name in ['HardwareInjection',]:
        event = SimInspiralEvent()
    elif pipeline.name in ['LIB',]:
        event = LalInferenceBurstEvent()
    ### BEHOLD, a new case:
    elif pipeline.name in ['newpipeline',]:
        event = NewPipelineEvent()
    else:
        event = Event()

Now when we go to actually assign values to the pipeline specific fields, they 
will actually exist. (If we had used the base ``Event`` class, of course, they 
would not.) 

Next, edit the function ``handle_uploaded_data`` in ``gracedb/translator.py``.
This function has a large ``if``-statement based on the pipeline name. It is 
the pipeline, after all, that determines how the data file will be parsed. Hopefully
you were able to convince the pipeline developers to send you something that's 
simple to parse, like JSON. If so, you can add something like this to the large
if statement::

    elif pipeline == 'newpipeline':
        event_file = open(datafilename, 'r')
        event_file_contents = event_file.read()
        event_file.close()
        event_dict = json.loads(event_file_contents)

        # Extract relevant data from dictionary to put into event record.
        event.attribute1 = event_dict['attribute1']
        event.attribute2 = event_dict['attribute2']
        event.attribute3 = event_dict['attribute3']

        # Save the event
        event.save()

REST API changes
================

The representation of events in the REST API is controlled by the event serializer,
``eventToDict``. The various serializers are found in ``gracedb/view_utils.py``.
The event dictionary constructed there has an ``extra_attributes`` key, which is meant
to hold the attributes which are not present in the base evnet class. The value
for this key is populated by duck-typing the event. So we'll need an additional
try/except block::

    try:
        # NewPipelineEvent
        rv['extra_attributes']['NewPipeline'] = {
              "attribute1" : event.attribute1,
              "attribute2" : event.attribute2,
              "attribute3" : event.attribute3,
              }
    except:
        pass


And ... yeah, I think that's basically all you have to do for the REST API. 

Web interface changes
=====================

When a users looks at this event in the web interface, they should see the 
pipeline-specific attributes there as well. This will require a little bit of 
customization of the event view. In the main event view, ``gracedb.views.view``,
we'll need to add something to the control structure that chooses the template::

    if event.pipeline.name in settings.COINC_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_coinc.html')
    elif event.pipeline.name in settings.GRB_PIPELINES:
        templates.insert(0, 'gracedb/event_detail_GRB.html')
    elif event.pipeline.name.startswith('CWB'):
        templates.insert(0, 'gracedb/event_detail_CWB.html')
    elif event.pipeline.name in ['HardwareInjection',]:
        templates.insert(0, 'gracedb/event_detail_injection.html')
    elif event.pipeline.name in ['LIB',]:
        templates.insert(0, 'gracedb/event_detail_LIB.html')
    elif event.pipeline.name in ['newpipeline',]:
        templates.insert(0, 'gracedb/event_detail_newpipeline.html')

There you see our new template: ``event_detail_newpipeline.html`` right at the end.
What this is doing is inserting the pipeline specific event page template at the
beginning of the list of templates. This is a nice thing to do, because Django will
just use the first template on the list that it is able to find.

You'll find the other templates at ``gracedb/templates/gracedb``. Most of the time, 
the pipeline-specific templates just override the ``analysis_specific`` block, and inherit 
the rest of the sections from the base ``event_detail.html`` template. Usually, the
special section for pipeline specific attributes just consists of a table of key-value
pairs, but it could be just about anything--big block of text, images, whatever. 
It winds up right underneath the "Basic Info" section, toward the top.

This is where it really comes in handy to have an example data file or two from your
pipeline developer with some realistic values in it. That way you can design the 
template to look nice when populated with real data.
