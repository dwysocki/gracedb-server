.. _miscellaneous:

================================
Miscellaneous 
================================

*Last updated 17 October 2017*

Replacing the database on the test instance
===========================================

Sometimes it's nice to update the database on the test instance so that
it matches the one on the production instance--which is being constantly
updated with new events and annotations. 

.. NOTE::
    There is no automated database replication between the test and 
    production instances. This would get in the way of development,
    especially when one is working on database schema migrations to
    try out on the test box.

There are no longer SSH keys tied to the gracedb user account, so here is what I consider to be teh simplest strategy for copying the database to a new server::

    # On production
    sudo -i
    cp /opt/gracedb/sql_backups/gracedb.sql.gz /home/albert.einstein
    chown albert.einstein:uwmlsc /home/albert.einstein/gracedb.sql.gz
    logout
    scp $HOME/gracedb.sql.gz albert.einstein@gracedb-test.ligo.org:~

    # Log into gracedb-test
    gunzip gracedb.sql.gz
    mysql -u gracedb -p gracedb < gracedb.sql

The latter step requires entering the MySQL password for the ``gracedb``
testing user. This can be found in ``config/settings/secret.py``.    

.. _copying_event_data:

Getting data for particular events onto the test instance
=========================================================

The above procedure, for better or worse, doesn't move all of the data
onto the test server: there are still backing files to move (i.e., the files
associated with annotations).  Normally, you'll only want to move files over
for a specific event or set of events. This is because the test server is 
likely to have a much smaller disk than the production machine, so you can't
just rsync all of the data over. I cobbled together an extremely hacky
way of moving only the data for selected events.

First, on the machine with the data, somehow create a list of the GraceID's 
of the events that you want to move data for. I would do this in the Django
console (i.e., ``./manage.py shell``). Suppose I want to move the data
for all gstlal events during O1::

    from events.models import Event
    from events.forms import SimpleSearchForm
    f = SimpleSearchForm({'query': 'gstlal O1'})
    outfile = open('/home/gracedb/query_graceids.txt', 'w')
    if f.is_valid():
        objects = form.cleaned_data['query']
        for object in objects:
            f.write('%s\n' % object.graceid)
    f.close()

Now, go to the data directory root ``/opt/gracedb/data`` and temporarily 
copy the tarring script there. Then run the script::
    
    cd /opt/gracedb/data
    cp /home/gracedb/bin/tar_up_data_dirs.py .
    ./tar_up_data_dirs.py

Now, you should have a new tar file ``/home/gracedb/tmp.tar``. Simply take
this to the new machine, ``cd`` into the GraceDB data directory, and 
un-tar the file. 

Adding a parameter to the VOEvent (and other "mini" development tasks)
======================================================================

We send information about events to GCN in the 
`VOEvent <http://www.ivoa.net/documents/VOEvent/>`__ format. It's basically
just a big XML file.  Sometimes,
the consumers of this information will ask you to add an additional parameter,
or make some other small modification. This is an example of what might be
called a "mini" development task: It doesn't involve any major code changes,
but you still have to go through the same sequence of steps that you would
for a true developement task. I recommend the workflow described in :ref:`new_server_feature`.

In this particular case, the only necessary code change is to edit the 
file ``gracedb/events/buildVOEvent.py`` and add something like::

    w.add_Param(Param(name="MyParam",
        dataType="float",
        value=getMyParamForEvent(event),
        Description=["My lovely new parameter"]))

working by analogy with the other parameters present. I only wanted to give
this example here, because it seems likely that such a task will be considered
"operational" even though it is really mini-development. The line is pretty 
blurry.

Adding an interferometer
========================
Note that these directions may change in the near future since we plan to add an instruments table to the database.

A good starting point is to search the GraceDB server code for "L1" to see where interferometers directly come into play.

Specifics (assume X1 is the IFO code):

1. Add X1OPS, X1OK, X1NO labels, update ``gracedb/templates/gracedb/event_detail_script.js`` with description, and update ``gracedb/templates/search/query_help_frag.html``
2. Add to instruments in ``gracedb/events/buildVOEvent.py``
3. Update ifoList in ``gracedb/events/query.py``
4. Add entry to ``CONTROL_ROOM_IPS`` in ``gracedb/config/settings/base.py``
5. Add signoff option for X1 in ``gracedb/templates/gracedb/event_detail.html``
6. Update INSTRUMENTS and time zones in ``gracedb/events/models.py``.
7. Update any event objects which need it (currently only LIB events)
8. Update lots of things in ``gracedb/events/serialize.py``
9. Add a permission like 'do_X1_signoff' to the superevent (and probably event) signoff model
10. Handle that case in the corresponding permissions in the API

See an example (Virgo) `here <https://git.ligo.org/lscsoft/gracedb/commit/65a4c08e25d7a472e1f995072d166b4c8dc611df>`__, but note that a lot of the Virgo-related stuff was already in the code.

Leap seconds
============
GraceDB does its own conversion between UTC and GPS time, but unfortunately, we have to track leap seconds.
This is done in ``gracedb/core/time_utils.py``.
You'll have to update this whenever a new leap second is announced (preferably in advance of its implementation).

There is probably a better way to do this.

On backups
==========

Backups for GraceDB are controlled by the file::
    ``/root/backup-scripts/gracedb.ligo.uwm.edu-filesystems`` 
    
on ``backup01.nemo.uwm.edu``.  This file simply contains::

    /etc
    /opt/gracedb

which means that everything under these directories on ``gracedb.ligo.uwm.edu``
will be backed up on ``backup00``.  You can see the files under the location
``/backup/gracedb.ligo.uwm.edu/``. This is occasionally useful for recovering
a config file that got blown away by puppet. Notice, though, that nothing 
under ``/home/gracedb`` is backed up. That's because the core server code and
accompanying scripts are under version control, and thus are backed up elsewhere.

I believe that everything backed up on ``backup01`` is also backed up off-site at CIT.
