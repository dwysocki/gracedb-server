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

        cd /home/gracedb/gracedb
        git checkout master
        git checkout -b my_bugfix_branch

#.  Make the necessary changes to the codebase (fix the bug, or add the feature
    you want). 

#.  In order to see whether the changes you've made had the desired effect, 
    you may need to restart the WSGI daemon. This can be done by touching the
    WSGI script file, since the daemon monitors this file for any changes::

        cd /home/gracedb/wsgi
        touch django.wsgi

#.  Iterate until the code is in a state that you like. If the process is 
    involved, you may want to make several commits along the way:: 

        git status
        git add /path/to/files/I/changed
        git commit -m "Yay! I fixed the bug."

#.  Run the unit tests against this server from another machine. Hopefully 
    they will all pass::

        cd gracedb-client/ligo/gracedb/test
        export TEST_SERVICE='https://gracedb-test.ligo.org/api/'
        python test.py

#.  If everything looks good, go back to gracedb-test, merge our branch into
    master, and push it::

        cd /home/gracedb/gracedb
        git status
        git checkout master
        git merge my_bugfix_branch
        git branch -d my_bugfix_branch
        git push

#.  Now go over to the production machine, and pull down the new version::

        cd /home/gracedb/gracedb
        git status
        git pull

#.  As with the test machine, you'll need to touch the WSGI script as well::

        touch gracedb/wsgi/django.wsgi

And now your new feature or bugfix should be live on the production machine.
The scenario I've outlined above is more-or-less the simplest way things can 
go. Things are more complicated if you need to do a database migration...
