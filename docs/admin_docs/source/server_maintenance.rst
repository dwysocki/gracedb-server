.. _server_maintenance:

=============================
GraceDB server maintenance
=============================

*Last updated 24 July 2017*

This section documents procedures for performing server maintenance and upgrading the production server code.

Routine maintenance
===================
You should upgrade the system packages on at least a bi-weekly basis.
Do the following on a test server first, then if everything seems OK, repeat for the production server:

.. code-block:: bash

    # Get package updates
    apt-get update
    # CHECK which packages will be upgraded, removed, etc.
    apt-get upgrade -s
    # Install upgrades, if they look OK
    apt-get upgrade
    apt-get dist-upgrade

Then, reboot the server, run the server code unit tests (if available), and run the client code unit tests, pointing to the server you just upgraded.

When doing updates on the production server, make sure to take a snapshot of the VM first, in case something goes wrong.

Server code upgrades
====================
First, develop and test your new features on one of the test servers.

SCCB approval
-------------
Once you are ready to move the new features into production, you'll need to get approval from the SCCB.
Create a new issue on the `SCCB project page <https://bugs.ligo.org/redmine/projects/sccb>`__.
The title should be something like "GraceDB server code update (1.0.10), 4 July 2017".
Note that you should submit these requests by Thursday at the latest if you want to implement the changes during maintenance the next Tuesday.

In the issue, you should describe the features/changes/bugfixes you've implemented, along with why they are necessary and what you've done to test them.
It's really helpful if you can get someone else with GraceDB experience to look over them in advance and approve them, too; this goes a long way with the SCCB reviewers.
The description should also include a link to a diff of the code changes from the server code git repository - this can be master vs. the old tag or a new tag vs. the old tag, depending on if you tag the code in advance.
I often wait to tag the new code until it's fully in place on the production server, in case any small changes become necessary.

Leave the status as 'New' and set the the category to 'Requested'.
After approval, an SCCB member will change the category to 'Approved' and the status to 'In Progress'.

After you've successfully updated the server code (see next subsection), post a short note, including a permanent diff between the old tag and the new tag (if you didn't already), and change the status to 'Closed' and the category to 'Production'.

Updating the production server
------------------------------
First, take a snapshot of the VM in case you somehow catastrophically break something.
Pull the changes into the local master branch:

.. code-block:: bash

    git checkout master
    git pull

Run any database migrations (as gracedb user):

.. code-block:: bash

    source ~/djangoenv

    # Show all migrations
    # Those not marked with an 'X' have not been performed
    python ~/gracedb/manage.py showmigrations

    # Example migration
    python ~/gracedb/manage.py migrate gracedb 0021

If you haven't tagged this version of the code already, do that and push the tag:

.. code-block:: bash

    git tag -a gracedb-1.0.11 -m "tag notes"
    git push --tags

Check out the tag (the production server should **always** be on a tag):

.. code-block:: bash

    git checkout gracedb-1.0.11

Build this documentation:

.. code-block:: bash

    sphinx-build -b html ~/gracedb/admin_doc/source/ ~/gracedb/admin_doc/build/

At this point, you can run the client code unit tests (pointing to the production server), since they only create Test events.
It always makes me a bit nervous to do this on the production server, so you can do some manual tests instead, like creating Test events, annotating with log messages, etc.
Basically, do whatever it takes for you to feel confident that the changes are in place and the server is working properly.

Memory management
=================
To get an idea for how much memory is currently being used, you can run the same plugin as nagios does for the memory check:

.. code-block:: bash

    /usr/lib/nagios/plugins/check_memory -f -C -w 10 -c 5

To combat an issue with wsgi_daemon threads persisting and consuming memory, we've set up a monit instance on the production server which monitors the memory usage and kills all wsgi_daemon processes running longer than 12 hours if the memory usage goes over 70%.
If this doesn't work for some reason, you can:

* Run the script manually:

  - Log in as root
  - Run ``/root/kill_wsgi.sh``

* Kill the processes manually (not very nice, may result in dropped connections for users):

  - Run ``sudo kill -s KILL $(pgrep -u wsgi_daemon)``

The aforementioned issue may be resolved in the near future.

Clearing file space
===================
Sometimes the GraceDB server's file system gets full for one reason or another.
A few common culprits are the ``apt`` logs and the Shibboleth cache.

To clean up ``apt`` logs (``/var/cache/apt``):

.. code-block:: bash

    apt-get clean

Shibboleth seems to accumulate many MB of JSON cache files in ``/var/cache/shibboleth`` on a daily basis.
We have currently set up a cron job under the root user to clear files older than a day from this cache.
This may be fixed in future versions of Shibboleth.
To remove these files manually, you can do:: 

    find /var/cache/shibboleth -type f -name '*.json' -mtime +1 -delete

To find directories which are using significant amounts of space, you can do something like:

.. code-block:: bash

    sudo -i
    cd /
    du -h --max-depth=1

and iterate from there to identify large subdirectories.

Tips for emergencies
====================

1. Announce emergency maintenance, especially if downtime is expected.  You'll probably want to send this announcement to DASWG, ldg-announce, and possibly DAC and the search groups.
2. Take a VM snapshot, if possible.

Stuck/overloaded server
-----------------------
If the server is "stuck", you might need to:

* Restart Apache: ``systemctl restart apache2``
* Restart Shibboleth: ``systemctl restart shibd``
* Free up some memory: see `Memory management`_.
* Clear up some space on the file system: see `Clearing file space`_.
* Reboot the entire server.

Server code bugfixes
--------------------
If at all possible, you'll want to do your testing/debugging on a test server.
To do this, you might need to copy the production database over to a test server.
See :ref:`sql_tips` for how to do this.

A few things that you may want to do after copying the database, but before beginning your debugging:

* Turn off phone alerts! Obviously the Contact and Trigger instances are part of the database you just copied and will trigger and annoy people if you submit events for testing.  The easiest solution is probably to just delete all of the Contact and/or Trigger objects (in the copied database) through the Django shell.
* You may want to turn off XMPP alerts just to be safe.

