.. _shibbolized_client:

================================
The Shibbolized Client
================================

Goal
====

Eventually, it would be nice to move towards not using any X509-based
authentication.  If were able to use Shibboleth only, that would considerably
simplify the auth infrastructure of GraceDB. It's also nicer in the sense that
all of the necessary information comes through the Shibboleth session. That way
we could get rid of our dependence on the LIGO LDAP as well.

Installation and usage
======================

At present, there is an experimental Shibbolized client that lies on a separate
branch.  I recommend installing it in a virtual environment::

    virtualenv --system-site-packages test
    source test/bin/activate

    ecp-cookie-init LIGO.ORG https://versions.ligo.org/git albert.einstein
    git clone https://versions.ligo.org/git/gracedb-client.git
    cd gracedb-client
    git checkout shibbolized_client

    python setup.py install

In order to use the client you will need a Kerberos ticket cache::

    kinit albert.einstein@LIGO.ORG

When you run the initialize method of the client, it uses this ticket cache to
authenticate against the LIGO IdP, and stores the resulting Shibboleth session
in a cookie jar::

    from ligo.gracedb.rest import GraceDb
    g = GraceDb()
    g.initialize()

Now the client is ready to use.

Robots
======

It's possible to obtain LIGO robot keytabs by going to 
`robots.ligo.org <https://robots.ligo.org/>`__ and clicking on "Apply for a 
shibboleth automaton keytab." Once you have this keytab, you can obtain a 
ticket cache by::

    kinit myRobot/robot/my.ligo.host.edu -k -t myrobot.robot.my.ligo.host.edu 

where ``myrobot.robot.my.ligo.host.edu`` is the name of the keytab file. 
These ticket caches are only valid for 24 hours, so it is handy to put the
``kinit`` command into a cron job. When requesting the keytab, make sure to
specify that the robot should belong to the group ``Communities:LSCVirgoLIGOGroupMembers``.
If the robot is to create GraceDB events, then the robot user will need to be 
authorized to do that as described in :ref:`new_pipeline`.

