.. _new_server_feature:

================================
Adding a new server-side feature
================================

.. NOTE::
    The steps here are only suggestions. You will undoubtedly discover 
    better ways to go about this. 

Suppose a user comes to you with a feature request or bug report that entails
changes to the GraceDB server codebase. Here's how I like to go about it.

#.  If it's a bug, make sure you can reproduce it. Perhaps write a little
    script with the client to exercise the bug automatically. Or figure out
    a way to test it quickly with the web interface.

#.  On the test machine, checkout a new branch off of master to develop the
    fix::

        cd /home/gracedb/gracedb_project
        git checkout master
        git checkout -b my_bugfix_branch

#.  Make the necessary changes to the codebase (fix the bug, or add the feature
    you want). 


#.  Iterate until the code is in a state that you like. If the process is 
    involved, you may want to make several commits along the way:: 

        git status
        git add /path/to/files/I/changed
        git commit -m "Yay! I fixed the bug."

#.  Run the unit tests against this server from another machine. Hopefully 
    they will all pass::

        cd gracedb-client
        export TEST_SERVICE='https://gracedb-test.ligo.org/api/'
        PYTHONPATH=. python ligo/gracedb/test/test.py

#.  If everything looks good, go back to gracedb-test, merge our branch into
    master, and push it::

        cd /home/gracedb/gracedb_project
        git status
        git checkout master
        git merge my_bugfix_branch
        git branch -d my_bugfix_branch
        git push

#.  Now go over to the production machine, and pull down the new version::

        cd /home/gracedb/gracedb_project
        git status
        git pull

And now your new feature or bugfix should be live on the production machine.
The scenario I've outlined above is more-or-less the simplest way things can 
go. Things are more complicated if you need to do a database migration...

To add:

* Information about doing migrations
* Information about django-debug-toolbar
* Tips for checking things in the logs
* Information about what each of the servers is used for and has (incommon, cirrus, etc.)

Using Django Debug Toolbar
==========================
Django Debug Toolbar (DJDT) is a useful tool for inspecting request objects, headers, SQL calls, etc. made by your web views.
One limitation is that it doesn't track Javascript or AJAX requests.
It's used by turning on the relevant middleware in the ``MIDDLEWARE`` setting and app in ``INSTALLED_APPS``.
The toolbar is shown to users whose IP address is included in the ``INTERNAL_IPS`` setting.
However, DJDT reveals certain headers which are to be kept secret, so to keep things extra-safe, we only allow the GraceDB server's IP address to be included in ``INTERNAL_IPS``.
As a result, you'll have to set up a SOCKS proxy to use DJDT.

Set up an SSH tunnel to the GraceDB server in question::

    ssh -D 8080 -f -C -q -N albert.einstein@gracedb-test.ligo.org

This process runs in the background, so once you're done, you'll have to kill it.

Mozilla Firefox
---------------
Go to Preferences, then under the "Network Proxy" heading, go to "Settings".
Use a manual proxy configuration, use SOCKS v5, use port 8080, and set ``127.0.0.1`` as the SOCKS host.

Google Chrome
-------------
Start Chrome from the command line with ``google-chrome --proxy-server="socks5://localhost:8080" --host-resolver-rules="MAP * ~NOTFOUND , EXCLUDE localhost"``.
