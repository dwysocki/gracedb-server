.. _managing_user_permissions: 

================================
Managing user permissions
================================

.. NOTE::
    The examples here show how to work with permissions in the Django console.
    I believe it is also possible to do the same thing through the admin
    browser interface.  I personally don't like it, though, so I never use it.

.. NOTE::
    This is a sample edit in order to prove editing functionality. 

Background on the permissions infrastructure
============================================

Native Django permissions
-------------------------

I find the Django docs a bit too concise on the subject of Permissions.
So what I'd like to do in this section is to explain how the permissions
infrastructure works in GraceDB in a relatively self-contained way.

Let's start with the native Django ``Permission`` model itself. 
Instances of this model correspond to permissions to do specific 
things, such as the permission to add an event. The formal ``name`` of
this permission object would be "Can add Event." 
They always consist of the modal verb "can" (i.e., "is permitted to"), 
an infinitive (i.e., the permitted action), and an object, which is 
always a Django model. 
For each model, Django automatically creates three permission objects:
on each for the infinitives ``add``, ``change``, and ``delete``. 

A full sentence about permissions (including the *subject*), such as 
"Albert can add events" 
comes when about you associate a ``Permission`` with a ``User``.
This is a many-to-many 
relationship (any given user can have many permissions, and any given
permission can be held by many users). In order to answer the 
question "Does Albert have permission to add events?", one queries the
database to see if 
this relationship between ``User`` and ``Permission`` exists.

The ``Permission`` model itself has a fairly small set of attributes:
the human-friendly ``name`` (mentioned above), the ``content_type``, 
and a ``codename``.  The ``codename`` consists
of the infinitive and object, lower-cased and separated by an underscore,
such as ``add_event``. This code name makes for a very convenient way of looking up
permissions in the database. The ``content_type`` specifies
exactly which model the permission refers to (e.g., the ``Event`` model
from the ``gracedb`` app).  
(The content type entry contains both the model name *and* the app to which 
the model belongs because both are necessary to fully specify the model. It
is not uncommon to have the same model name in multiple apps.)

Putting it all together, here's how a permission check could be done
in real life (from inside the Django shell)::
    
    >>> from django.contrib.auth.models import User, Permission

    >>> p = Permission.objects.get(codename='add_event')
    >>> u = User.objects.get(username='albert.einstein@LIGO.ORG')

    >>> if p in u.user_permissions.all():
    ...:    print "Albert can add events!"

The Django ``User`` class has a convenience function ``has_perm`` to 
make this easier::

    >>> from django.contrib.auth.models import User

    >>> u = User.objects.get(username='albert.einstein@LIGO.ORG')

    >>> if u.has_perm('gracedb.add_event'):
    ...:    print "Albert can add events!"

Again, notice that the ``has_perm`` function needs the codename to be scoped by
the app to which the model belongs. Both are required to fully specify the model.

Permissions can also be granted to a ``Group`` of users. In practice, this
is the most common way of doing permissions in GraceDB. Thus, individual
users can have a given permission by virtue of one of their
group memberships. Here is an example from real life::

    >>> from django.contrib.auth.models import User, Group, Permission

    # Retreive a specific permission, user, and group from the database
    >>> p = Permission.objects.get(codename='add_groupobjectpermission')
    >>> u = User.objects.get(username='peter.shawhan@LIGO.ORG')
    >>> g = Group.objects.get(name='executives')

    # Peter is a member of the executives group.
    >>> u in g.user_set.all()
    True

    # The permission is not in Peter's individual user permission set.
    >>> p in u.user_permissions.all()
    False

    # But the permission *is* in the permission set for the executives group.
    >>> p in g.permissions.all()
    True

    # Thus, Peter has permission by virtue of his group membership.
    >>> u.has_perm('guardian.add_groupobjectpermission')
    True

The significance of the permission used in the example above, 
``add_groupobjectpermission``,
will be explained in the next section.

Custom permissions for GraceDB
------------------------------

To wrap up our discussions of the native Django permissions infrastructure,
we note that Django allows custom permission types
in addition to the default ``add``, ``change``, and ``delete`` permissions.
We have added three custom permissions (i.e. *infinitives*) for GraceDB.
First, it is important to control which users and groups can *view* 
event data. Thus, we have added a custom ``view`` permission for the event models::

    >>> from django.contrib.auth.models import Permission

    >>> perms = Permission.objects.filter(codename__startswith='view')

    >>> for p in perms:
    ...:    print p.codename
    ...:     
    view_coincinspiralevent
    view_event
    view_grbevent
    view_multiburstevent
    view_siminspiralevent

A second custom permission arises because we need to control which users may
upload *non-Test* events for a given pipeline. Typically, a single robotic user
and a group of known pipeline developers are given permission to create 
non-test events for a given pipeline. This is to prevent accidental contamination
of the event stream with test events. For lack of a better term, the infinitive
chosen for this purpose is "populate", and the model referred to is ``Pipeline``.
Thus the permission's codename is ``populate_pipeline``. Notice that ``add`` 
would not have worked here, since the user isn't adding a new pipeline, but rather
populating an existing one. (I suppose ``change`` could have been used, but that
would seem a little weird to me too. Adding an event for a pipeline doesn't 
change the pipeline itself.)

The final custom permission applies only to GRB events. A trusted set of users
is allowed to edit GRB event information *after* the event has been created in 
order to set values for quantities like the redshift and T90, which are not 
known at the time of event creation. T90 was the first such attribute added, so
the infinitive chosen for this permission is ``t90``. In other words, a user
is said to *T90* a ``GrbEvent`` when he or she adds or updates these special attributes. 
(I realize this is ugly, but I couldn't think of anything better at the time.
It has to be short.) Thus, the codename is ``t90_grbevent``. Again, one might wonder
whether ``change_grbevent`` would have made more sense to use for this purpose.
However, that permission is already being used to check for the ability to 
add log messages or observation records to the event. 

The row-level extension
-----------------------

The permissions described above apply at the Django model level, or
equivalently, to entire database tables.  Thus, a user with the permission
``change_event`` in his or her permission set is able to change *any* entry in
the ``gracedb_event`` table. However, GraceDB requires finer grained access
controls: we need to be able to grant individual users or groups permissions
on *individual objects*, or equivalently, individual rows of the database.
Thus these are sometimes called *row-level* (or object-level) permissions, as opposed to the 
usual *table-level* (or model-level) permissions.
We use a third party package, 
`django-guardian <https://github.com/django-guardian/django-guardian>`__, 
to add support for row-level permissions. 
In practice, row-level permissions are the most commonly used type for 
GraceDB. (There are a few exceptions, for example the 
``t90_grbevent`` permission discussed in the previous section, which is table-level.)

Row-level permissions work as a simple extension of system outlined above.
In order to specify a row-level permission for a user, we will need to 
know three pieces of information: 1) the user in question, 2) the permission
being granted, and 3) the particular object for which the user will have
said permission.
Thus, the ``UserObjectPermission`` model has the following attributes: ``user``,
``permission``, ``content_type``, and ``object_pk``. Together, the ``content_type``
and the ``object_pk`` specify the individual object (or database row)
that this permission refers to. 

.. NOTE:: 
    In the case of table-level permissions, the association between ``User``
    and ``Permission`` was handled with a many-to-many relationship. In this
    case, the ``guardian`` package provides an entirely new model instead, (the
    ``UserObjectPermission``), with foreign keys to the user and permission.
    This is necessary because of the additional required attributes.

.. NOTE:: 
    One might ask: "Why should we use two separate fields (``content_type`` and
    ``object_pk``) to specify the object? Why not just have a foreign key to
    the object instead?" But using a foreign key field would mean that we need
    a different ``User{*}Permission`` model for *each and every* model that we
    want to control access to. This is because the specific model is hardwired
    into the declaration of a foreign key field. So, instead, the designers of
    ``guardian`` decided to store the primary key (``object_pk``) and the model
    (``content_type``). This way, the ``UserObjectPermission`` model is
    completely generic. 

As with table-level permissions, row-level permissions can also be applied to
groups. Thus, there is also a ``GroupObjectPermission`` object. It is the same
as the ``UserObjectPermission``, except that there is a foreign key to a
``Group`` rather than a ``User``. The majority of the row-level permission
objects are actually for groups rather than users. In particular, we use group
object ``view`` permissions to expose events to various groups. 

Now I can explain the example in the previous section with
``add_groupobjectpermission`` permission object. A user with this permission
may create new ``GroupObjectPermission`` objects. Thus, he or she will be
authorized to grant ``view`` permission on a particular event to a particular
group of users, such as the LV-EM observers group
(``gw-astronomy:LV-EM:Observers``).  Similarly, the
``delete_groupobjectpermission`` permission controls whether a user can
*revoke* the view permissions on an event. Because releasing event information
to non-LVC users is a sensitive matter, only the ``executives`` group is
authorized to do this. Thus, we are using table-level permissions to authorize
the addition and deletion of row-level permissions. Turtles all the way down
(well, not *really*). 

On permissions and searching for events
---------------------------------------

One of the main features of GraceDB is the ability to query for events matching
certain criteria. However, we clearly only want events for which the user has
``view`` permission to show up in the search results. Suppose a user has
searched for events from the ``gstlal`` pipeline, and we want to filter the
events according to the user's ``view`` permissions.  One way to do this is by
querying the database for each event in the queryset to see if the user has
either an individual or group permission to view the event. There is a 
`shortcut  <http://django-guardian.readthedocs.org/en/stable/api/guardian.shortcuts.html#get-objects-for-user>`__
provided to do this from the guardian package::

    from django.contrib.auth.models import User
    from gracedb.models import Event, Pipeline
    from guardian.shortcuts import get_objects_for_user

    user = User.objects.get(username='albert.einstein@LIGO.ORG')
    events = Event.objects.filter(pipeline=Pipeline.objects.get(name='gstlal'))

    filtered_events = get_objects_for_user(user, 'gracedb.view_event', events)

However, behind the scenes, this requires creating a complex join query over
several tables, and the process is rather slow. Thus, I added a field to the
base event class itself called ``perms``, which is intended to store a
JSON-serialized list of the group permissions, where each
``GroupObjectPermission`` on the event is represented by a string like ``<group
name>_can_<shortname>`` (where the shortname corresponds to the permission's
infinitive). Thus, to filter a queryset of events, one can do the following::

    from django.db.models import Q
    from django.contrib.auth.models import User, Group

    user = User.objects.get(username='albert.einstein@LIGO.ORG')
    shortname = 'view' # Typically, we are filtering for view permissions.

    auth_filter = Q()
    for group in user.groups.all():
        perm_string = '%s_can_%s' % (group.name, shortname)
        auth_filter = auth_filter | Q(perms__contains=perm_string)
    return events.filter(auth_filter)
     
This constructs a string for each group the user belongs to, and checks to 
see whether that string occurs anywhere within the event's ``perm`` string.
These queries are combined with ``OR`` so that as long as one group has
``view`` permission on an event, that event will be present in the final
filtered queryset used to construct the search results page.
The utility ``filter_events_for_user`` in ``permission_utils.py`` uses
this technique.  It improves the speed of a search by about a factor of 10
with respect to the ``get_objects_for_user`` method shown above, based
on some anecdotal testing.

There is also a method on the ``Event`` object to refresh this permissions
string::

    from gracedb.models import Event
    e = Event.getByGraceid('G184098')
    e.refresh_perms()

This operation is idempotent, so it should always be safe to do this.  Sensible
defaults are applied when the event is created, but it is necessary to call
this ``refresh_perms`` method if the permissions are updated (i.e., if the
event is exposed or hidden from the LV-EM group).

Practical examples
==================

Granting permissions to expose events 
-------------------------------------

So, practically speaking, how would you give someone permission to expose to 
the LV-EM observers group? Or permission to hide an event that has already been
exposed? It's simple: Just add the person to the ``executives`` group::

    >>> from django.contrib.auth.models import User, Group
    >>> u = User.objects.get(username='albert.einstein@LIGO.ORG')
    >>> g = Group.objects.get(name='executives')
    >>> g.user_set.add(u) 

Granting permission to edit GRB events
--------------------------------------

As mentioned in the discussion above, sometimes the GRB group requests that 
a user be enabled to add values like T90 and redshift to GRB events. This 
can be done by adding the permission by hand::
    
    >>> from django.contrib.auth.models import User, Permission

    >>> p = Permission.objects.get(codename='t90_grbevent')
    >>> u = User.objects.get(username='albert.einstein@LIGO.ORG')

    >>> u.user_permissions.add(p):
    ...:    print "Albert can add events!"

Granting permission to populate a pipeline
------------------------------------------

Permission to populate a pipeline is typically given to individual users,
rather than to groups. Thus, a new ``UserObjectPermission`` needs to be 
created. An example of this is shown in :ref:`new_pipeline`, in the section
on server-side changes.
