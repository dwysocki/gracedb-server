.. _introduction:

============
Introduction
============

*Last updated 13 Feb 2018*

GraceDB is a service for aggregating and disseminating information about candidate gravitational-wave events.
It is a key component of the effort to offer low-latency GW notifications to astronomer partners.
We provide a web interface and a RESTful API, along with a Python client for easily interacting with the API.

GraceDB currently runs on Debian Stretch, although upcoming developments may allow the service to be run on any operating system.

Components of the service
=========================
We can divide the GraceDB service into five main components:

- Django app
- Backend webserver (Gunicorn)
- Frontend webserver (Apache)
- Primary authentication (Shibboleth)
- Database backend (MariaDB)

Django
------
GraceDB is written in Python and is constructed around the `Django <https://www.djangoproject.com/>`__ web framework.
We are currently using Python 2 and Django 1.11.
Note that this is the last version of Django to support Python 2, so a migration to Python 3 will be necessary in the future.

Gunicorn
--------
`Gunicorn <http://gunicorn.org/>`__ is a lightweight Python webserver which interfaces directly with the Django service via the WSGI protocol.
The settings are managed with a config file and the service is started via systemd.

Apache
------
`Apache <https://httpd.apache.org/>`__ is one of the longest-running open source webservers.
We still use Apache in concert with Gunicorn because Shibboleth seems to work best with it.
It is configured as a reverse proxy which gets authentication information from Shibboleth, sets that information in the headers, and then passes it on to Gunicorn.

Shibboleth
----------
`Shibboleth <https://www.shibboleth.net/>`__ is a software package for managing federated identities and providing a single sign-on portal.
It uses metadata providers to collect user attributes from an attribute authority and put them into the user's session.
These attributes are then available to the relevant service providers which are accessed by the user.

Metadata providers used by GraceDB:

- LIGO attribute authority
- InCommon - provides access via institutional accounts registered on gw-astronomy.org
- Cirrus Gateway - provides access via Google accounts registered on gw-astronomy.org

MariaDB
-------
Currently, we use MariaDB 10.1 with the MyISAM table engine.
Note that the table engine is set within the Django settings, not directly in the database.
May want to look into other table engines in the future.

Servers
=======
Here's a short overview of the currently available GraceDB servers:

- Production:

  - gracedb.ligo.org
- Test: (almost) identical to production, to be used for final testing of development work.

  - gracedb-test.ligo.org
- Development: for raw code development; feel free to break these servers as needed. Note that these servers are not registered with any non-LIGO metadata providers, so testing of external authentication needs to happen on gracedb-test.

  - gracedb-dev1.ligo.org
  - gracedb-dev2.ligo.org
- Other:

  - simdb.ligo.org: for gstlal testing.  May be retired in the near future.

See :ref:`new_gracedb_instance` for information on setting up new servers.

Useful repositories
===================
The `scripts <https://git.ligo.org/gracedb/scripts>`__ repository contains a set of scripts for running cron jobs and performing useful tasks on a GraceDB server.
Examples include:

- Pulling LIGO users from the LIGO LDAP
- Adding users to executives and advocates groups
- Parsing Apache logs and database logs
- Starting LVAlert Overseer
- Managing LVAlert nodes

The `admin tools <https://git.ligo.org/gracedb/admin-tools>`__ repository is a collection of tools to be used by GraceDB administrators.
It also includes notes on past work and debugging efforts, as well as planning for future development.

