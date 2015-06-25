.. _auth:

================================
Authentication and Authorization
================================

Authentication methods
========================================

GraceDB supports three different types of authentication methods depending
on the entry point:

- **Web Interface**: ``gracedb.ligo.org/`` supports Shibboleth with
  federated identities.
- **REST API**: The API has three entry points:
    - **X509**: ``gracedb.ligo.org/api/``
    - **Shibboleth**: ``gracedb.ligo.org/apiweb/``
    - **Basic**: ``gracedb.ligo.org/apibasic/``

The X509 URL listed above is the default for the Python client. But users
with robot Kerberos keytabs will want to point to the Shibboleth URL.
(The same URL can also be accessed with a web browser to browse the API.)
Similarly, LV-EM users accessing the API will want to point to the URL
for basic auth.

GraceDB permissions
=========================================

After a user has successfully authenticated, GraceDB examines the user's
group memberships to determine whether the user is authorized to access
or modify a particular resource. These permissions apply at the level of
individual events. The relevant permissions are: ``view`` (which allows 
viewing) and ``change`` (which allows annotation). In most cases, LVC
users have both permissions on all events. By contrast, LV-EM members 
(and, in the future, 
other external users) have permissions only on events that have 
been vetted for
distribution through the EM followup alert network. This restriction
is to avoid possible confusion with injections, glitches, pipeline
testing etc.  Membership in a special administrators group is 
required to alter the
permissions on an event. 

Creating new events in a *non-test* group (e.g., CBC or Burst) requires 
a special ``populate`` permission on the relevant pipeline object. These 
permissions are set at the user (rather than group) level and are 
maintained by hand. Send email to the GraceDB maintainer 
or the ``uwm-help`` queue if you need a new Pipeline or pipeline permission.

Robot certificates
=====================

Access to the REST API through the X509 entry point requires a valid robot 
certificate.  (Note: This is only necessary for LVC users. LV-EM users can see
:ref:`basic_auth_for_lvem` .) Instructions for obtaining a certificate are 
available 
`here <https://wiki.ligo.org/AuthProject/LIGOCARobotCertificate>`__. When you 
send the certificate signing request (CSR) to the
``rt-auth`` queue, make sure to indicate that you intend to use the 
robot certificate to access GraceDB. 

Robot keytabs
======================

Robot keytabs are now available by going to `robots.ligo.org <https://robots.ligo.org>`__ and
clicking on "Apply for a shibboleth automaton keytab." However, the version of the 
GraceDB Python client that works with the Kerberos ticket cache has not yet 
been released. You can get this version of the client by cloning the client source
and checking out the ``shibbolized_client`` branch. After running ``kinit`` 
with your robot keytab to obtain a valid ticket cache, you can use the 
Shibbolized client as follows::

    from ligo.gracedb.rest import GraceDb, HTTPError

    SERVICE = "https://gracedb.ligo.org/apiweb/"
    SHIB_SESSION_ENDPOINT = "https://gracedb.ligo.org/Shibboleth.sso/Session"

    client = GraceDb(SERVICE, SHIB_SESSION_ENDPOINT)
    client.initialize()

    try:
        r = client.ping()
    except HTTPError, e:
        print e.message

    print "Response code: %d" % r.status
    print "Response content: %s" % r.json() 

