.. _responding_to_lvalert:

==============================
Responding to LVAlert Messages
==============================

.. sectionauthor:: Reed Essick

This tutorial will show you how to
  * register to receive LVAlerts 
  * subscribe and unsubscribe from pubsub nodes
  * instantiate and manage an ``lvalert_listen`` instance 
  * interact with GraceDB through the Python REST interface in a script that is launched via ``lvalert_listen``

This tutorial assumes that the ``ligo-lvalert`` software package is already installed on
your machine (this is true on all cluster machines).

While we attempt to be pedagogically complete as much as possible, we would
like to stress that the existing documentation and help-strings for the
command-line and Python packages are *very* useful and should be the final
reference if you have any questions.

Registering to receive LVAlert messages
=======================================

LSC-Virgo members can activate accounts by simply completing the form 
`here <https://www.lsc-group.phys.uwm.edu/cgi-bin/jabber-acct.cgi>`__.

If you need to create an account that is not attached to your user.name, you
can email uwm-help@cgca.uwm.edu and request an account.  Once you have created an
account, you will be able to subscribe the account to different pubsub nodes
and receive lvalert messages.

Subscribing to pubsub nodes
===========================

LVAlert messages are broadcast through pubsub nodes and different messages go
through different nodes. For instance, all gstlal events created in GraceDB are
announced through the pubsub node called::

    cbc_gstlal

which includes both highmass and lowmass events. If you instead want to only
receive lowmass events, these are announced through::

    cbc_gstlal_lowmass

Importantly, if you subscribe to both ``cbc_gstlal`` and ``cbc_gstlal_lowmass``, you
will receive two alerts for every gstlal lowmass event. The general format of::

    group_pipeline[_search]

is followed by all pubsub nodes used to announce events and annotations to
those events in GraceDB.

Fill out the form and follow all instructions to create an account attached to
your "user.name". For the rest of this tutorial, I will refer to the username
as "user.name", but you should replace this with your own account's information.
You'll be prompted for your password after each command.

*Note: To bypass this, create a .netrc file in your home directory and enter your
authentication information*::

    machine lvalert.cgca.uwm.edu login user.name password passw0rd

*With this setup, you won't need to include the* ``-a`` *flag for your username, 
or enter your password. Your .netrc file should only be accessible by you, so
be sure to do* ``chmod 600 $HOME/.netrc``.

To actually subscribe to a pubsub node, we use ``lvalert_admin``
which allows you to manage your subscriptions. This includes subscribing to new
nodes, unsubscribing from nodes and viewing your current subscriptions. We will
now subscribe your account to ``cbc_gstlal_lowmass``. Run::

    lvalert_admin -a user.name --subscribe --node cbc_gstlal_lowmass

You can confirm that your account is successfully subscribed to this node by
running::

    lvalert_admin -a user.name --subscriptions

which will list your account's subscriptions. You should see
``cbc_gstlal_lowmass`` in the resulting list.  To unsubscribe from a node, use::

    lvalert_admin -a user.name --unsubscribe --node cbc_gstlal_lowmass

but for now we'll leave our subscription in place. If you'd like to subscribe
to other nodes, simply repeat the subscription command and replace
``cbc_gstlal_lowmass`` with the name of the node to which you'd like to
subscribe. A complete list of nodes is available by running::

    lvalert_admin -a user.name --get-nodes

For this tutorial, let's subscribe to another node to show how things scale.  Run::

    lvalert_admin -a user.name --subscribe --node cbc_gstlal_highmass

Creating an LVAlert node
========================

Users can create their own LVAlert pubsub nodes as well. Unsurprisingly, this
is also straightforward. Simply run::

    lvalert_admin -a user.name --create --node user.name-TestNode

to create a node called ``user.name-TestNode``. Of course, you'll want to change
"user.name" to your account's name. Go ahead and create this node. If you need
to delete it at any time, you can with::

    lvalert_admin -a user.name --delete --node user.name-TestNode

but leave it be for the moment. You now have a node owned by your account to
which you can publish alerts. We'll come back to this when we test our set-up.
You will also need to subscribe to this node with::

    lvalert_admin -a user.name --subscribe --node user.name-TestNode

Run::

    lvalert_admin -a user.name --subscriptions

and make sure you see::

    cbc_gstlal_lowmass 
    cbc_gstlal_highmass 
    user.name-TestNode

in the output.

Starting and managing an ``lvalert_listen`` instance
====================================================

Now you have an lvalert account and it is subscribed to a few pubsub nodes.
It's time to set up an ``lvalert_listen`` instance which allows your code to
receive and react to announcements broadcast through the pubsub nodes. The
first thing you'll need is a config file. Using your favorite text editor,
create a file called ``myLVAlertListen.ini`` with the following as its contents::

    [cbc_gstlal_lowmass]
    executable = /bin/true

    [cbc_gstlal_highmass]
    executable = /bin/false

    [user.name-TestNode]
    executable = /bin/true

Now run::

    lvalert_listen -a user.name -c myLVAlertListen.ini > myLVAlertListen.out &

Congratulations! You've set up an ``lvalert_listen`` instance which reacts to
announcements published to the ``cbc_gstlal_lowmass``, ``cbc_gstlal_highmass`` and
``user.name-TestNode`` nodes.

Here's what's happening: ``lvalert_listen`` hears announcements made to any node to
which your account is subscribed. When an alert is
received, it looks in the config file (loaded into memory) for the associated
section. Importantly, if there is no section in the config file corresponding
to the pubsub node's name (an exact match is required), ``lvalert_listen`` ignores
the announcements from that node even if you are subscribed to it. If it finds
a section, it looks for the "executable" option and attempts to run the
associated value (in this case ``/bin/true``) via Python's subprocess module. The
delegation to ``subprocess.Popen`` does *not* split the value so this must be a
single filename for the executable. If your executable takes in options, we
recommend wrapping it in a simple shell script and specifying the shell script
within ``myLVAlertListen.ini``. We'll get to that in a bit.

In this way, you can have multiple ``lvalert_listen`` instances for a single
account listening to multiple different nodes and doing multiple different
things. Furthermore, if you provide multiple sections in ``myLVAlertListen.ini``
you can react to announcements from different pubsub nodes in different ways, all
within the same ``lvalert_listen`` instance.

Right now your listener (running in the background) isn't doing much. When
``cbc_gstlal_lowmass`` alerts are received, it forks an instance of ``/bin/true`` and
when ``cbc_gstlal_highmass`` alerts are received, it forks an instance of
``/bin/false``. We can improve upon that pretty easily.

Let's start by creating some basic wrapper scripts to print that we've received
alerts. Again, using your favorite text editor, create the file ``lvalert-run_cbc_gstlal_lowmass.sh``
and fill it with::

    #!/bin/bash
    echo "received an alert about a cbc_gstlal_lowmass event!" >> lvalert_cbc_gstlal_lowmass.out

Similarly, create ``lvalert-run_cbc_gstlal_highmass.sh`` and fill it with::

    #!/bin/bash
    echo "received an alert about a cbc_gstlal_highmass event!" >> lvalert_cbc_gstlal_highmass.out

Finally, create a file for your test node, ``lvalert-run_user.name-TestNode.sh``,
which contains::

    #!/bin/bash
    read a
    echo "received a test alert: ${a}" >> lvalert_user.name-TestNode.out

Once you've done that, ensure that all three shell scripts are executables (required
by the delegation through ``subprocess.Popen``) with::

    chmod +x lvalert-run_cbc_gstlal_lowmass.sh
    chmod +x lvalert-run_cbc_gstlal_highmass.sh
    chmod +x lvalert-run_user.name-TestNode.sh

and edit myLVAlertListen.ini so it reads::

    [cbc_gstlal_lowmass]
    executable = ./lvalert-run_cbc_gstlal_lowmass.sh

    [cbc_gstlal_highmass]
    executable = ./lvalert-run_cbc_gstlal_highmass.sh

    [user.name-TestNode]
    executable = ./lvalert-run_user.name-TestNode.sh

It is generally a good rule of thumb to provide the full paths to executables
and output files in both ``myLVAlertListen.ini`` as well as these simple shell
scripts. However, for the purpose of this tutorial we'll stick with relative
paths.

Now, because you have modified the ``lvalert_listen.ini`` file, you'll need to
restart your ``lvalert_listen`` instance. Find the PID in the process table, kill
the existing process, and restart the listener using the command from above.

You can also specify a resource name in your call to ``lvalert_listen``
using the ``-r`` flag::

    lvalert_listen -a user.name -c myLVAlertListen.ini -r listener1 &

If you don't specify this parameter, a random UUID is generated for the resource name.
The important point to consider is that only one listener can exist for any 
(user.name, passw0rd, resource.name) triple *anywhere in the network*.
If you launch a second process with matching values of this triple,
one of the processes is killed automatically (although which process
dies may not be deterministic). Thus, I can kill processes running at CIT by
creating processes at UWM with the same resource name. This can be extremely
dangerous and annoying, so please be careful. If you want to directly specify
resource names for all of your listener processes, you can do something like::
 
    lvalert_listen -a user.name -c myLVAlertListen.ini -r oneInstance &
    lvalert_listen -a user.name -c myLVAlertListen.ini -r twoInstance &

This will launch two instances of ``lvalert_listen`` (both using the same
config file) with different resource names (note that this can also be
achieved by not specifying the resource name at all).
They will both react to alerts and fork
processes. If each points to a different config file, I can then get multiple
types of follow-up processes forked for the same announcement through a single
pubsub node.

When alerts are received, you will see a line printed to the associated files.
Note, the scripts for the ``cbc_gstlal`` nodes do not report anything about the
actual alerts received, whereas the script for your test node reads in stdin
(to a variable called "a") and then echo's that into the output file. This is
how ``lvalert_listen`` passes the contents of the alert into the forked subprocess,
via stdin. We'll come back to that later when we interact with GraceDB.

For now, let's test your set-up by publishing a few announcements to your test
pubsub node. Create a file called ``test.txt`` and fill it with some text like::

    just a test announcment

Then run::

    lvalert_send -a user.name -n user.name-TestNode --file test.txt

This publishes the contents of test.txt as a string to the node
``user.name-TestNode``. If your listener is running in the
background, then you should see a new line in ``lvalert_user.name-TestNode.out``
which reads::

    received a test alert: just a test announcement

If you repeat the ``lvalert_send`` command, you should see multiple lines appear,
one for each time you sent an alert.

Note, each time we change the ``lvalert_listen`` config file (``myLVAlertListen.ini``)
we have to restart the listener for the changes to take effect.
However, if the config file points to wrapper script we can modify the contents
of the wrapper script and have the changes take effect immediately for all
future events *without* restarting the ``lvalert_listen`` process. This can be
quite handy, although you should be careful to keep track of what was actually
run when (version controlling the config file and ``lvalert-run_*sh`` scripts is a
good idea).

It is worth stressing that you do *not* have to actually use a wrapper script.
If you have an executable that can be called via subprocess in the same way as
the wrapper script, then you can simply specify that within myLVAlertListen.ini
instead of dealing with wrappers at all. This can reduce the number of files
that have to be managed but because of how ``lvalert_listen`` forks the executable
through subprocess the executable cannot take in any command line options or
arguments.

Now, ``lvalert_listen`` is a fairly robust process and is unlikely to throw errors
or fall over by itself. However, occasionally server-side or local trouble can
cause your listener to die and you will need to restart it.
Several solutions exist, although the preferred option is 
`Monit <https://mmonit.com/monit/>`__ which can automatically restart processes and
notify you that it did so.

Reacting to GraceDB
===================

Now that you've got an ``lvalert_listen`` instance running which reacts to a few
different pubsub nodes, let's really dig into the full potential of this
system.

So far, we either haven't used the contents of the alert or have simply printed
them into a file. That's nice, but we can do much better. GraceDB (the main
publisher of alerts) sends JSON (JavaScript Object Notation) strings through
lvalert and there are several convenient tools to parse these in Python.
Similarly, there is an extremely useful RESTful interface to GraceDB
implemented in Python, although command-line executables also exist.

Let's start by mining the JSON string sent by GraceDB for some information.
Create a Python executable ``iReact.py`` and fill it with the following::

    #!/usr/bin/python 
    import json 
    import sys

    alert = json.loads(sys.stdin.read())
    print 'uid : ' + alert['uid']

Don't forget to give this executable permissions with::

    chmod +x iReact.py

Now, modify your wrapper script for the test node
(``lvalert-run_user.name-TestNode.sh``) so it reads::

    #!/bin/bash
    ./iReact.py >> lvalert_user.name-TestNode.out

When we send messages to the test node, it will now delegate to ``iReact.py``. We
don't have to restart the ``lvalert_listen`` instance because that still points to
``lvalert-run_user.name-TestNode.sh``, which is nice.

Let's go ahead and send a test message in JSON format. Edit ``test.txt`` so it
reads::

    {"uid": "G12345"}

and run::

    lvalert_send -a user.name --node user.name-TestNode --file test.txt

You should see a new line in ``lvalert_user.name-TestNode.out`` which reads::

    uid : G12345

Ta-da! You've now sent, received, parsed, and reacted to a JSON string
through lvalert. This is the key way all follow-up processes listen for events
in GraceDB and react accordingly. Note, the ``sys.stdin.read()`` command will
block until there is something in stdin and this can cause your code to hang if
you don't specify anything. This should not be the case when it is called from
within ``lvalert_listen``, but it can sometimes be annoying when debugging your
follow-up scripts.

Let's do something a bit more concrete with more specific examples of how we
can interface with GraceDB based off lvalert messages.
Open ``iReact.py`` and modify it so it reads::

    #!/usr/bin/python 
    import json 
    import sys

    from ligo.gracedb.rest import GraceDb

    alert = json.loads(sys.stdin.read())
    print 'uid : ' + alert['uid']

    gdb = GraceDb() ### instantiate a GraceDB object which connects to the default server

    if alert['alert_type'] == 'new': ### the event was just created and this is the first announcment
        gdb.writeLog( alert['uid'], message="user.name heard an alert about this new event!" )

    elif alert['alert_type'] == 'update': ### something happened in GraceDB for this event and GraceDB is letting everyone know
        gdb.writeLog( alert['uid'], message="user.name heard an alert about an update for this event!" )

Now, if we modify ``test.txt`` to::

    {"uid": "G12345", "alert_type": "new", "far": 1e-8}

and send it, ``iReact.py`` will try to write a log entry in GraceDB for event
G12345. It's easy to see that you can filter alerts out (e.g.: only react to
'new' events) and modify your follow-up processes behavior accordingly. To
check that this worked, you'll need to look at the associated GraceDB page,
expand the "full log" section and look for your log message.

**IMPORTANTLY,** I've just made up 'G12345' as an example. If you really want
to test your script, you should choose a test event from GraceDB. A query for
these events is available `here <https://gracedb.ligo.org/events/search/?query=group%3A%20Test>`__.
*NOTE: please do* **NOT** *test your script with important events in GraceDB
like G184098 (the cWB entry for GW150914) or others with low FAR.*
Instead, please use a test event as described above. There are also test instances of
GraceDB available if you'd prefer to not work with the production server right
away. Contact uwm-help@cgca.uwm.edu with a descriptive subject line for more
information.

At this point, you're pretty much ready to go. However, I'll leave you with one
more example for what ``iReact.py`` might look like::

    #!/usr/bin/python 
    import json 
    import sys

    from ligo.gracedb.rest import GraceDb

    FarThr = float(sys.argv[1])

    alert = json.loads(sys.stdin.read()) 
    print 'uid : '+alert['uid']

    gdb = GraceDb() ### instantiate a GraceDB object which connects to the default server

    if alert['alert_type'] == 'new': ### the event was just created and this is the first announcment
        if alert['far'] < FarThr:
            file_obj = open("iReact.txt", "w")
            print >> file_obj, "wow! this was a rare event!  It had FAR = %.3e < %.3e, which was my threshold"%(alert['far'], FarThr)
            file_obj.close()
            gdb.writeLog( alert['uid'], message="user.name heard an alert about this new event!", filename="iReact.txt", tagname=["data_quality"] )

Try to figure out exactly what this version does. If you can
understand everything within this script you certainly know enough to get your
follow-up process running! Hint: to get this to run correctly, you'll want to
modify ``lvalert-run_user.name-TestNode.sh`` so it looks like::

    #!/bin/bash
    ./iReact.py 1e-8 >> lvalert_user.name-TestNode.out

