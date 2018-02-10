.. _sql_tips:

==============================
Database interactions with SQL
==============================

*Last updated 11 Aug 2017*

This section gives some tips on using the MySQL interface and some descriptions of currently available tables in the GraceDB and LVAlert databases.

The first step is to log in to the MySQL interface::

    sudo -i
    mysql -u root -p

Then enter the password when prompted.

Collection of tricks
====================

.. NOTE::
    It's not safe to update tables or delete rows manually through the MySQL interface, unless you **REALLY** know what you're doing (due to cross-table dependencies). The safest bet is to do it through the Django manager shell.

Viewing data
------------

* See all databases: ``SHOW DATABASES;``
* Select a database to use: ``USE gracedb;``
* See tables in that database: ``SHOW TABLES;``
* Get column names of a table: ``SHOW COLUMNS FROM events_event;``
* Get number of rows in a table: ``SELECT COUNT(*) FROM events_event;``
* See all data in a table: ``SELECT * FROM events_event;``
* Get only specific columns from a table: ``SELECT id,created FROM events_event;``
* Get a specific row: ``SELECT * FROM events_event WHERE id=2;``. Can use ``!=`` as well.

* Get a set of rows with a regular expression: ``SELECT * FROM auth_user WHERE user like '%albert%';``

  * ``%`` is a wildcard.
  * Can use ``NOT LIKE`` as well.

* Show a few rows: ``SELECT * FROM auth_user LIMIT Ni,N;`` where ``Ni`` is the starting row and ``N`` is the number of rows to display.
* Get unique entries in a column: ``SELECT DISTINCT(group_id) FROM events_event;``

Modifying data
--------------

* Delete a row or set of rows: ``DELETE FROM events_event where id<4;``
* Edit rows matching a regex: ``UPDATE auth_user SET username='new_username' WHERE username LIKE 'albert%';``


More complicated stuff
----------------------

* Set a variable: ``SET @var='created';``
* Show variable value: ``SELECT @var;``
* Get table information: ``SHOW TABLE STATUS WHERE Name='events_eventlog';``
* Changing storage engine for a table: ``ALTER TABLE events_eventlog ENGINE=InnoDB;``
* Check foreign key relationships::

    USE information_schema;
    SELECT table_name,column_name,referenced_table_name,referenced_column_name FROM key_column_usage;

* Complex ``SELECT`` query with a join::

    SELECT event.id, user.username
    FROM events_event AS event
    LEFT JOIN auth_user AS user ON event.submitter_id=user.id
    WHERE id<4;

* Complex ``UPDATE`` query with a join::

    UPDATE events_event AS event
    LEFT JOIN events_group AS group ON event.group_id=group.id
    SET event.far=0
    WHERE (group.name='Stochastic' AND event.far > 0);

Database copying and checking
-----------------------------

Make a copy of the database::

    mysqldump -u gracedb -p gracedb > backup.sql

Dump only specific tables::

    mysqldump -u root -p gracedb events_event events_eventlog auth_user > backup.sql

Use this command to import a dump file (overwrites any databases or tables which already exist)::

    mysql -u gracedb -p gracedb < backup.sql

Check the database for errors::

    mysqlcheck -c gracedb -u gracedb -p

.. NOTE::

   This won't resolve foreign key issues; for example, if an event is removed but the corresponding event logs are not.

GraceDB tables
--------------

The following tables should be the same across all GraceDB instances:

* auth_group
* auth_group_permissions
* auth_permission
* auth_user
* auth_user_groups
* auth_user_user_permissions
* django_content_type
* events_group
* events_label
* events_pipeline
* events_search
* guardian_groupobjectpermission
* guardian_userobjectpermission
* ligoauth_alternateemail
* ligoauth_ligoldapuser
* ligoauth_localuser
* ligoauth_x509cert
* ligoauth_x509cert_users

I'm not sure what the following tables do or if they are still in use:

* coinc_definer
* coinc_event
* coinc_event_map
* coinc_inspiral
* django_session
* django_site
* experiment
* experiment_map
* experiment_summary
* events_approval
* ligolwids
* multi_burst (somehow related to coinc_event)
* process
* process_params
* search_summary
* search_summvars
* sngl_inspiral
* time_slide

Notes on LVAlert databases
==========================

* To get the MySQL database password: ask Patrick Brady or the previous GraceDB developer.
* You'll want to do ``USE openfire;`` to select the database after logging into the MySQL interface.

Summary of tables
-----------------
All tables not listed here were found to be empty by Tanner in April 2017.

* Not empty, but probably not useful

  * ofID: not sure
  * ofPrivacyList: not sure, only contains stuff from Brian Moe
  * ofRoster: users, JIDs, nicknames, but only 4 users...
  * ofRosterGroups: shows roster groups (what are those?)
  * ofUserProp: something to do with the admin user
  * ofVCard: not sure
    ofVersion: shows ``openfire`` version

* Possibly useful

  * ofOffline: shows messages not received or waiting to be received? Seems out of date.
  * ofPresence: shows offline users (?)
  * ofPubsubDefaultConf: shows default configuration for users? Only contains info for certain users.
  * ofPubsubItem: shows all messages? Seems out of date

* Useful

  * ofProperty: properties of ``openfire`` server
  * ofPubsubAffiliation: shows affiliations to nodes, most useful columns are nodeID, jid (username, affiliation. Note: affiliation='none' indicates a subscriber to the node.
  * ofPubsubNode: shows all nodes
  * ofPubsubSubscription: shows node subscriptions
  * ofSecurityAuditLog: log of admin actions through the console
  * ofUser: list of users
