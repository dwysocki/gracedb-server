================================
Miscellaneous 
================================

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

Here is how I recommend doing it. First gsissh into the test instance as
the ``gracedb`` user. Then::

    cd 
    scp gracedb@gracedb.cgca.uwm.edu:/opt/gracedb/sql_backups/gracedb.sql.gz .
    gunzip gracedb.sql.gz
    mysql -u gracedb -p gracedb < gracedb.sql

The latter step requires entering the MySQL password for the ``gracedb``
testing user. This can be found in ``/home/gracedb/settings/settings_secrets.py``.    


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

    from gracedb.models import Event
    from gracedb.forms import SimpleSearchForm
    f = SimpleSearchForm({'query': 'gstlal O1'})
    outfile = open('/home/gracedb/query_graceids.txt', 'w')
    if f.is_valid():
        objects = form.cleaned_data['query']
        for object in objects:
            f.write('%s\n' % object.graceid())
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
file ``gracedb/gracedb/buildVOEvent.py`` and add something like::

    w.add_Param(Param(name="MyParam",
        dataType="float",
        value=getMyParamForEvent(event),
        Description=["My lovely new parameter"]))

working by analogy with the other parameters present. I only wanted to give
this example here, because it seems likely that such a task will be considered
"operational" even though it is really mini-development. The line is pretty 
blurry.

On backups
==========

Backups for GraceDB are controlled by the file::
    ``/root/backup-scripts/gracedb.cgca.uwm.edu-filesystems`` 
    
on ``backup01``.  This file simply contains::

    /etc
    /opt/gracedb

which means that everything under these directories on ``gracedb.cgca.uwm.edu``
will be backed up on ``backup01``.  You can see the files under the location
``/backup/gracedb.cgca.uwm.edu/``. This is occasionally useful for recovering
a config file that got blown away by puppet. Notice, though, that nothing 
under ``/home/gracedb`` is backed up. That's because the core server code and
accompanying scripts are under version control, and thus are backed up elsewhere.

I believe everything backed up on ``backup01`` is also backed up off-site at CIT.
