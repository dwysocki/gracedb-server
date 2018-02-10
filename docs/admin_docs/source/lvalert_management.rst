.. _lvalert_management:

==================
LVAlert management
==================
*Last updated 28 June 2017*

Server configuration
====================
You can access some of the Openfire server settings through the `web interface <lvalert.cgca.uwm.edu:9090>`__.
Use your LVAlert credentials on that server to log in.
If you don't have an account, you'll need another GraceDB/LVAlert developer to create an account for you and make you an admin.
There is also an admin account, ask Patrick Brady if you don't know the password.
Note that this password can also be used to login to the database via the MySQL interface.

There are a few things you can do from within this web interface, but the main useful function is to create/edit/delete user or pipeline accounts.

Managing nodes
==============
In an effort to tightly control production LVAlert nodes, we've developed a `script <https://git.ligo.org/gracedb/scripts/blob/master/add_lvalert_nodes.py>`__ which is used to create them and add publishers.
There are more instructions in the script, but the main principles are:

* The LVAlert account used by the production GraceDB server (username ``gracedb``) should be the owner of **ALL** GW event nodes, even those on the test LVAlert server.
* LVAlert accounts for test/development GraceDB servers should be added as publishers to these nodes on the test LVAlert server **only**.
* The production and test LVAlert servers should contain the same GW event nodes.
