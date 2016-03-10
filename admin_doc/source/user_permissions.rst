.. _managing_user_permissions: 

================================
Managing user permissions
================================

.. NOTE::
    You can do this stuff through the admin interface too, I think.
    I just don't like it, so I never use it.

General info on the permissions infrastructure
==============================================

I find the Django docs a bit too concise on the subject of Permissions.
So what I'd like to do in this section is to explain how the permissions
infrastructure works in GraceDB in a relatively self-contained way.

I'll start with the native Django ``Permission`` model itself. 
Instances of this model correspond to permissions to do specific 
things, such as "can add ``Event``", "can add ``Labelling``, etc.
So they consist of a verb and an object. The object will always 
be a model, so that the permissions always refer to various things that
can be done to a particular model.

Thus, the ``Permission`` object has a formal name
This model model itself has a fairly small set of attributes:
``name``, ``content_type``, and ``codename``.  The codename consists
of a verb and an object, where the object is the name of the model in 
question. 


Django natively supports model-level (or *table-level*) permissions for users
and groups.  In other words, individual users or groups of users can have
permission to ``add``, ``change``, or ``delete`` objects of a given model
(i.e., rows on a given table).  We use a third party package, 
`django-guardian <https://github.com/django-guardian/django-guardian>`__, 
to add support for object level (or *row-level* permissions). This allows 
individual users or groups to be granted permission on *individual objects*,
or equivalently, individual rows of a database table.

The ``User`` and ``Group`` models are many-to-many with ``Permission`` 
(through the ``user_permissions`` and ``permissions`` attributes, 
respectively). (In practice, these many-to-many relationships are 
stored in separate tables: ``auth_user_user_permissions`` and
``auth_group_permissions``.) 

The ``Group`` model 
has only ``name`` and permissions. In practice, we rarely use table-level
authorization checks in GraceDB--either for users or group. One exception
to this is the ability to edit certain properties of the GRB events, 
such as T90. This table-level permission (with codename ``t90_grbevent``) 
is granted to individual users on a case-by-case basis.

.. NOTE::
    You may have noticed that ``t90`` is being used as a verb here.
    This is, in fact, how I thought of it. A user is said to *t90* an 
    event when he or she adds or updates values for T90, and the other 
    special GRB attributes.

In addition to the ``add``, ``change``, and ``delete`` permissions native
to Django, we added a custom ``view`` permission for each of the Event and 
event subclass models. This is the permission that controls whether the user
is able to view an event page or access information about an event through
the REST API. 

The row-level permissions work as a simple extension of the above model.
In order to specify a row-level permission for a user, we will need to 
know three pieces of information: 1) the user in question, 2) the permission
being granted, and 3) the particular object for which the user will have
said permission.
Thus, the ``UserObjectPermission`` model has the following attributes: ``user``,
``permission``, ``content_type``, and ``object_pk``. Together, the ``content_type``
and the ``object_pk`` specify the individual object (or database row)
that this permission refers to. 

The following is a digression... One might ask: "Why use two separate fields
to specify the object? Why not just a foreign
key to the object instead?" But using a foreign key field would mean
that we need a different ``UserObjectPermission`` model for *each and every*
model that we want to control.  For
example, suppose I create a model with a foreign key to a ``User`` 
object::

    from django.db import models 
    from django.contrib.auth.models import User

    class MyModel(models.Model):
        user = models.ForeignKey(User)

Then the database table will have a column ``user_id``, which just contains
the primary key of the user object. When you're working with a ``MyModel`` object
and you access the ``user`` attribute, Django uses the primary key (stored in
``user_id`` and the definition of the model to retrieve the ``User`` object.
So the fact that the ``id`` belongs to a ``User`` object is baked into the 
definition of ``MyModel``. However, we want the ``UserObjectPermission`` to 
be general purpose--in other words, we want to be able to grant a particular
permission to a particular user, for any kind of object. Thus, the ``ForeignKey``
field is not an option here, as it requires the specific kind of object to
be hardwired into the model. Instead, we store the primary key (``object_pk``)
and the model (``content_type``).


To see which users already have permissions, go to the Django shell and...

Permissions to expose events 
============================

In effect, these permission objects allow specific users to maniupulate
*other* permission objects.

Permissions to edit GRB events
==============================

Sometimes the GRB group requests to add another user to the list of users
allowed to provide supplementary information to GRB events by hand. 
