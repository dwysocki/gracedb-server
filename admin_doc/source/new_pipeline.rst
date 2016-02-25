================================
Adding a new pipeline or search
================================

Sometimes, users will request that a new ``Pipeline`` be added. Creating
the pipeline object itself is the easy part. The hard part is figuring out
what kind of data file the group will be uploading, and how to ingest the values.
The directions below will focus on the easiest possible case--in which the 
new pipeline's data files have the same format and information as those 
of an existing pipeline. (For example, the ``gstlal-spiir`` group uploads
the same type of data file as the ``gstlal`` group, and this made adding the
``gstlal-spiir`` pipeline relatively easy.)
Adding a new ``Search`` is simpler, but the steps relating to LVAlert are similar.


.. NOTE::
    The following suggests performing the necessary database operations
    in the django console (i.e., a Python interpreter running with the correct
    environment). These operations could also be done in the web-based django
    admin interface. However, I never use it myself, so that's not the method
    I'll show in this documentation. One could also issue raw SQL commands
    if preferred.

.. NOTE::
    The database operations here could also be done with 'data migrations'. 
    This leaves more of a paper trail, and as such might be considered 
    'the right thing to do.' However, it seems like overkill for relatively
    small tasks like this.

GraceDB server side steps
=========================

First, create the new pipeline object. Since the only field in the Pipeline model
is the name, it's pretty simple. Suppose we are creating a new pipeline called 
``newpipeline``. We fire up the Django console:: 

    cd /home/gracedb
    ./manage.py shell

Now we create the pipeline object itself::

    from gracedb.models import Pipeline
    newpipeline = Pipeline.objects.create(name='newpipeline')

Now that the pipeline exists, one or more users will need to be given
permission to *populate* the pipeline (i.e., to create new events for that
pipeline). For more info on permissions, see :ref:`managing_user_permissions`.
By default, all internal users will have permission to create ``Test``
events for our new pipeline, but only specific users will be allowed to create
non-``Test`` events. Let's suppose we want to give access to a human user
(Albert Einstein) and a robotic user (``newpipeline_robot``)::

    from django.contrib.auth.models import User, Permission
    from guardian.models import UserObjectPermission
    from django.contrib.contenttypes.models import ContentType

    # Retrieve the objects we will need
    p = Permission.objects.get(codename='populate_pipeline')
    ctype = ContentType.objects.get(app_label='gracedb', model='pipeline')
    einstein = User.objects.get(username='albert.einstein@LIGO.ORG')
    robot = User.objects.get(username='newpipeline_robot')

    # Create the new permission
    UserObjectPermission.objects.create(user=einstein, permission=p, 
        content_type=ctype, object_pk=newpipeline.id)
    UserObjectPermission.objects.create(user=robot, permission=p, 
        content_type=ctype, object_pk=newpipeline.id)

The next step is to figure out how events from the 
new pipeline will be represented in the database. If the base ``Event`` class
is is sufficient, or if one of the existing subclasses can be used, then 
no new database tables will be needed. However, if the events coming from the
pipeline has new attributes, then a new event subclass will be needed to 
adequately represent it. If the latter, see :ref:`new_event_subclass`. 

For now, let's assume that the attributes of the new pipeline match up
exactly with those of an existing pipeline, and that the data file can be
parsed in the same way. Then all we need to do is to edit the utility function
``_createEventFromForm`` in ``gracedb/view_logic.py`` so that our 
new pipeline's name appears in the correct list, resulting in the correct
event class being created. For example, if the events
of the new pipeline match up with those from Fermi, then we can add it to
the same list as Fermi, Swift, and SNEWS. 

Next, edit the function ``handle_uploaded_data`` in ``gracedb/translator.py``
so that, when an event is created for our new pipeline, the data file is
parsed in the correct way. This function is basically just a huge ``if``
statement on the pipeline name. So if we want the data file to be parsed
in the same way as the files for Fermi and Swift, we would just add the name
of our new pipeline next to Fermi and Swift in the control structure.

Steps for LVAlert
=================

When a new pipeline is created, the corresponding LVAlert nodes need to be 
created. Let's suppose our new pipeline is associated with the ``Burst``
group. That means we will need at least two new LVAlert nodes::

    test_newpipeline
    burst_newpipeline

If the relevant group (in this case, the burst group) wants to specify one
or more ``Search`` values for their event, then these nodes need to be 
created as well::

    test_newpipeline_search1
    burst_newpipeline_search1
    test_newpipeline_search2
    burst_newpipeline_search2

where the names of the searches are ``search1`` and ``search2``. I typically
use a script such as the one below to create the nodes and add the ``gracedb``
user as a publisher::

    #!/usr/bin/env python

    import subprocess
    import time

    nodes = [
        'test_newpipeline',
        'burst_newpipeline',
        'test_newpipeline_search1',
        'burst_newpipeline_search1',
        'test_newpipeline_search2',
        'burst_newpipeline_search2',
    ]

    username = 'user.name'
    password = 'passw0rd'

    servers = [
        'lvalert.cgca.uwm.edu',
        'lvalert-test.cgca.uwm.edu',
    ]

    for server in servers:
        for node in nodes:
            print "creating node %s for server %s ..." % (node, server)
            cmd = 'lvalert_admin -a {0} -b {1} -c {2} -d -q {3}'.format(username, 
                password, server, node)
            p = subprocess.Popen(cmd, shell=True)
            out, err = p.communicate()

            if err:
                print "Error for node %s: %s" % (node, error)

            # add gracedb as publisher
            # Also serves as a check to whether the node exists if not creating
            time.sleep(2)

            print "adding gracedb as publisher to node %s for server %s ..." % (node, server)

            cmd = 'lvalert_admin -a {0} -b {1} -c {2} -j gracedb -q {3}'.format(username,
                password, server, node)
            p = subprocess.Popen(cmd, shell=True)
            out, err = p.communicate()

            if err:
                print "Error for node %s: %s" % (node, error)
