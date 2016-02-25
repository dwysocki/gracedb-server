.. _managing_user_permissions: 

================================
Managing user permissions
================================

Note
==========

You can do this stuff through the admin interface too, I think.
I just don't like it, so I never use it.

General info on the permissions infrastructure
==============================================

To see which users already have permissions, go to the Django shell and...

Permissions to expose events 
============================

In effect, these permission objects allow specific users to maniupulate
*other* permission objects.

Permissions to edit GRB events
==============================

Sometimes the GRB group requests to add another user to the list of users
allowed to provide supplementary information to GRB events by hand. 
