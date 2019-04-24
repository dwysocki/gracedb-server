.. _public_gracedb:

=====================================
GraceDB and public triggers
=====================================

In the era of public triggers, certain resources on GraceDB should be available
to users without any authentication. This is because the GCN notices will be
public, and these contain links to GraceDB resources (such as the skymap).  
These particular links need to be open, since it's very impolite to include them
otherwise. In my mind, this is the strongest reason, but there could be others
as well.

There are several changes that will be needed in order to open up GraceDB
resources to the public. This outline may not be exhaustive.

Groups and permissions
======================

Un-authenticated users
----------------------

Truly un-authenticated users should only be able to perform ``GET`` requests.
Unfortunately, the Django ``AnonymousUser`` object doesn't help us much,
because this user has no group memberships, and we want to be able to control
access with groups. For example, the filtering of search results depeneds on a
perm string with group-based permissions.

Thus, we could create a dummy user::

    from django.contrib.auth.models import User, Group

    anon_user = User.objects.create(username='AnonUser')
    anon = Group.objects.create(name='anon')
    anon.user_set.add(anon_user)

And then instead of ``request.user`` being ``None`` for unauthenticated users,
it would be set to ``AnonUser``. That way, ``request.user`` would always be
either a known user or ``AnonUser``.

Authenticated public users
---------------------------

Interested members of the public who wish to use the web interface to comment
(i.e., a ``POST`` or ``PUT``) or to use the REST API (with basic auth) should
be required to *register* first on gw-astronomy.org. They will need to have a
google account or some institutional login from our identity federation.

This requires a bit of help for the auth team. Basically, we'll need a group
that doesn't require any approval from a liaison.  But otherwise would be
similar to the LV-EM group.

The attribute authority should assert a group membership, such as ``public``.
(The name needs to be different than the ``anon`` group above, because we don't
want to allow the anonymous user to make any unsafe requests.)

Actually, here's one issue you'll run into: Google releases an obfuscated
persistent ID. It's basically a long string of numbers instead of the person's
actual name. But a user who leaves a comment on an event may *want* to identify
him/herself.

So I would recommend adding a field in the registration form on
gw-astronomy.org that allows the user to pick a display name.  Then configure
the gw-astronomy attribute authority to release this attribute. In the ligoauth
middleware, grab the attribute (if present) and use it to set the ``last_name``
of the user. That way, it will show up in the event log display.

Apache Config
=============

This will be considerably simpler than before. Basically, the idea is that we
will require the shibboleth module to be active on all URL paths in the web
interface. But we won't actually require a ``valid-user`` except for particular
locations, such as the admin docs and the reports page.  That way, instead of
having Apache handle the ACLs, more of it will be pushed off onto the app. But
that is actually a good thing::

    Alias /documentation/ "/home/gracedb/gracedb_project/docs/user_docs/build/"
    <Directory "/home/gracedb/gracedb_project/docs/user_docs/build/">
         AuthType shibboleth
         ShibRequestSetting requireSession false
         Require shibboleth
    </Directory>

    Alias /admin_docs/ "/home/gracedb/gracedb_project/docs/admin_docs/build/"
    <Directory "/home/gracedb/gracedb_project/docs/admin_docs/build/">
         AuthType shibboleth
         ShibRequestSetting requireSession 1
         Require user branson.stephens@ligo.org alexander.pace@ligo.org patrick.brady@ligo.org
    </Directory>

    <Location "/">
         AuthType shibboleth
         ShibRequestSetting requireSession false
         Require shibboleth
    </Location>

View logic for manipulating permissions
=======================================

The necessary logic for manipulating permissions already exists.  Suppose you
want to expose a particular event to the public.  You'll give ``view`` perms to
the ``public`` and ``anon`` groups, and ``change`` perms to ``public`` only.
Unfortunately, the client doesn't have a convenience function for altering
permissions. So you have to create the URL and ``POST`` to it by hand. For
example, here is how to grant ``view`` permissions to ``public``:: 

    from ligo.gracedb.rest import GraceDb
    import urllib

    g = GraceDb

    graceid = 'G123456'
    group_name = 'public'
    perm_shortname = 'view'

    url = g.service_url + urllib.parse.quote('events/%s/%s/%s' % (graceid, group_name, perm_codename))
    r = g.put(url)

Templates 
==========

This is where things can get tricky. First, I'll explain where things are now.

At present, there are only two main groups of users that can access GraceDB:
LVC users, and LV-EM MOU partners. The information shown to the MOU partners
differs in 4 ways from that shown to LVC members:

#. the false alarm rate is floored to avoid revealing that we have a gold-plated detection
#. the pipeline-specific attributes are missing
#. the list of event log messages is reduced to EM-relevant info 
#. the neighbors list is filtered according to ``view`` permissions

To achieve the first three, ``is_external(request.user)`` is used. In 
other words, these restrictions on the event view will be made for any 
user who is *not* a member of the LVC. In particular, for (1), we check 
whether the user is external before calculating a display FAR to pass into
the template context. For (2), we pass in a ``user_is_external`` variable
into the template context. 

For item (3), the ``get`` method on the ``EventLogList`` resource returns an
appropriately filtered list of log messages. In particular, any log entries
will be removed from the list unless they have been deliberately tagged with
the external access tag.  This tag is specified in the settings module::

    EXTERNAL_ACCESS_TAGNAME = 'lvem'

The name of this tag is a bit unfortunate (since it is too specific--in the
future, not all external users will be members of LV-EM). But it could be
changed in the future.

The final item on the list above--the filtering of neighbors--is done in the
same way as the filtering of search results, so this needs no modification.

So what happens when we enter the public era? Well, if the general public
should be given access to the *same* information as the LV-EM group, then it will
be easy. In fact, nothing would need to be done.

However, I don't see that scenario as being likely, because the LV-EM group
members share information with the LVC and each other inside a private bubble.
They may not want to share information about observation coordinates with
members of the general public. Thus, we'll probably want to have an additional
tagname::

    PUBLIC_ACCESS_TAGNAME = 'public'

And then individual log entries can be released to the public by tagging
them with this tag. An extra filter would need to be added in ``api.py``::
         
    @event_and_auth_required
    def get(self, request, event):
        logset = event.eventlog_set.order_by("created","N")

        # Filter log messages for external users.
        if is_external(request.user):
            logset = logset.filter(tags__name=settings.EXTERNAL_ACCESS_TAGNAME)

        if is_public(request.user):
            logset = logset.filter(tags__name=settings.PUBLIC_ACCESS_TAGNAME)

And you'll need an ``is_public`` utility function as well. Everything else can
be done in the same way as for external users.

Another potential issue that could arise: It's possible that the LV-EM MOU
group and the general public would have different FAR floors. In other words,
we might want to limit the LV-EM fars to one per 100 years, but limit the
public FARs to 1 per 10 years. If this is the case, you'll want to look for
instances of ``VOEVENT_FAR_FLOOR`` in the code and modify accordingly.
