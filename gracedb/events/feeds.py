import logging

from django.conf import settings
from django.contrib.syndication.views import FeedDoesNotExist
from django.contrib.syndication.views import Feed
from django.shortcuts import render
from django.template import RequestContext
from django.urls import reverse

from .models import Event, Group, Pipeline
from .permission_utils import internal_user_required
from .views import view


# Set up logger
logger = logging.getLogger(__name__)

FEED_MAX_RESULTS = getattr(settings, 'FEED_MAX_RESULTS', 20)


class EventFeed(Feed):
    title_template = "feeds/latest_title.html"
    description_template = "feeds/latest_description.html"

    # Restrict access to feeds
    @internal_user_required
    def __call__(self, request, *args, **kwargs):
        return super(EventFeed, self).__call__(request, *args, **kwargs)

    def get_object(self, request, url):
        bits = url.split('/')[1:]
        # bits will look like
        # [] , ['cbc'], ['cbc','gstlal']

        objs = Event.objects.order_by("-id")
        if 'test' not in bits:
            # Filter out test group
            testGroup = Group.objects.filter(name__iexact='Test')
            if testGroup.count():
                objs = objs.exclude(group=testGroup[0])
        if len(bits) not in [0,1,2]:
            raise FeedDoesNotExist
        if not bits:
            title = "GraceDB Events"
        else:
            group = Group.objects.filter(name__iexact=bits[0])
            if not group.count():
                raise FeedDoesNotExist
            group = group[0]
            objs = Event.objects.filter(group=group)
            if len(bits) == 1:
                title = "GraceDB %s Events" % group.name
            else:
                pipeline = Pipeline.objects.filter(name__iexact=bits[1])
                if not pipeline.count():
                    raise FeedDoesNotExist
                pipeline = pipeline[0]
                objs = Event.objects.filter(pipeline=pipeline)
                title = "GraceDB %s / %s Events" % (group.name, pipeline.name)
        return title, objs[:FEED_MAX_RESULTS]

    def title(self, obj):
        title, _ = obj
        return title

    def link(self, obj):
        # This is the link around the title for the entire feed.
        return reverse("home")

    def item_link(self, obj):
        return reverse(view, args=[obj.graceid])

    def item_author_name(self, obj):
        return u"{0} {1}".format(obj.submitter.first_name, obj.submitter.last_name)

    def item_pubdate(self, obj):
        return obj.created

    def description(self, obj):
        # XXX Descriptive text for the feed itself.
        # I don't know what to put here
        return ""

    def items(self, obj):
        _, x = obj
        return x

@internal_user_required
def feedview(request):
    return render(request, 'feeds/index.html')
