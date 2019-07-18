try:
    from functools import reduce
except ImportError:  # python < 3
    pass

from django.conf import settings
from django.db.models import Q

from events.models import Label
from events.shortcuts import is_event
from superevents.shortcuts import is_superevent
from .models import Contact, Notification
from .utils import evaluate_label_queries


class CreationRecipientGetter(object):
    queryset = Notification.objects.all()

    def __init__(self, es, **kwargs):
        # NOTE: es = event_or_superevent
        self.is_event_alert = is_event(es)
        self.event = es if self.is_event_alert else es.preferred_event
        self.process_kwargs(**kwargs)

        # Explicitly get the values for a few things and store them on a
        # class instance.  This is because there is a possibility of race
        # conditions if the event or superevent is updated while we are trying
        # to figure out which notifications should trigger, which can take
        # several seconds or more in production.
        self.far = self.event.far
        self.is_ns_candidate = self.event.is_ns_candidate()
        # Force queryset evaluation with list()
        self.label_names = list(es.labels.values_list('name', flat=True))

    def process_kwargs(self, **kwargs):
        pass

    def get_category_filter(self):
        if self.is_event_alert:
            return Q(category=Notification.NOTIFICATION_CATEGORY_EVENT)
        return Q(category=Notification.NOTIFICATION_CATEGORY_SUPEREVENT)

    def get_far_filter(self):
        query = Q(far_threshold__isnull=True)
        if self.far:
            query |= Q(far_threshold__gt=self.far)
        return query

    def get_nscand_filter(self):
        if self.is_ns_candidate:
            return Q()
        return Q(ns_candidate=False)

    def get_group_filter(self):
        if self.is_event_alert:
            return Q(groups__isnull=True) | Q(groups=self.event.group)
        return Q()
        
    def get_pipeline_filter(self):
        if self.is_event_alert:
            return Q(pipelines__isnull=True) | Q(pipelines=self.event.pipeline)
        return Q()

    def get_search_filter(self):
        if self.is_event_alert:
            return Q(searches__isnull=True) | Q(searches=self.event.search)
        return Q()

    def get_filter_query(self):
        filter_list =  [getattr(self, method)() for method in dir(self) 
            if method.startswith('get_') and method.endswith('_filter')]
        if filter_list:
            return reduce(Q.__and__, filter_list)
        return Q()

    def get_trigger_query(self):
        return Q()

    def filter_for_labels(self, notifications):
        # Check notifications which do NOT have a label query. Check whether
        # their labels are a subset of what is attached to the event or
        # superevent.  Notifications with no labels are automatically a
        # subset.
        # In this case, all the labels attached to the notification should
        # be in the set attached to the event/superevent.
        notification_pks = []
        label_set = set(self.label_names)
        for n in notifications.filter(label_query__isnull=True):
            n_label_set = set(n.labels.values_list('name', flat=True))
            if n_label_set.issubset(label_set):
                notification_pks.append(n.pk)

        # Check those with label queries
        notification_qs = notifications.filter(label_query__isnull=False)
        pks = evaluate_label_queries(self.label_names, notification_qs)
        notification_pks.extend(pks)
        return Notification.objects.filter(pk__in=notification_pks)

    def get_contacts_for_notifications(self, notifications):
        # Get contacts; make sure contacts are verified and user is in the
        # LVC group (safeguards)
        contacts = Contact.objects.filter(notification__in=notifications,
            verified=True, user__groups__name=settings.LVC_GROUP) \
            .select_related('user')

        # Separate into email and phone contacts
        email_recipients = contacts.filter(email__isnull=False)
        phone_recipients = contacts.filter(phone__isnull=False)

        return email_recipients, phone_recipients

    def get_notifications(self):
        # Get trigger query and apply to get baseline set of notifications
        trigger_query = self.get_trigger_query()
        base_notifications = self.queryset.filter(trigger_query)

        # Get and apply filter query to trim it down
        filter_query = self.get_filter_query()
        notifications = base_notifications.filter(filter_query)

        # Do label filtering - remove any notifications whose
        # label requirements are not met by the event or superevent
        final_notifications = self.filter_for_labels(notifications)

        return final_notifications

    def get_recipients(self):
        # Get notifications matching criteria
        notifications = self.get_notifications()

        # Get email and phone recipients and return
        email_contacts, phone_contacts = \
            self.get_contacts_for_notifications(notifications)

        # Filter to get only "distinct" contacts; i.e., don't send multiple
        # texts to a user who has two notifications set up to point to the
        # same contact
        email_contacts = email_contacts.distinct()
        phone_contacts = phone_contacts.distinct()

        return email_contacts, phone_contacts


class UpdateRecipientGetter(CreationRecipientGetter):

    def process_kwargs(self, **kwargs):
        # We try to get old_far this way since old_far can be None, but we
        # want the code to fail if it is not provided.
        try:
            self.old_far = kwargs['old_far']
        except KeyError:
            raise ValueError('old_far must be provided')
        self.old_nscand = kwargs.get('old_nscand', None)
        if self.old_nscand is None:
            raise ValueError('old_nscand must be provided')

    def get_trigger_query(self):
        # Initial query should match no objects
        query = Q(pk__in=[])

        # Then we add other options that could possibly match
        if self.far is not None:
            if self.old_far is None:
                query |= Q(far_threshold__gt=self.far)
            else:
                query |= (Q(far_threshold__lte=self.old_far) &
                    Q(far_threshold__gt=self.far))
        if self.old_nscand is False and self.is_ns_candidate:
            query |= Q(ns_candidate=True)
        return query


class LabelAddedRecipientGetter(CreationRecipientGetter):

    def process_kwargs(self, **kwargs):
        self.label = kwargs.get('label', None)
        if self.label is None:
            raise ValueError('label must be provided')

    def get_notifications(self):

        # Any notification that might be triggered by a label_added action
        # should have that label in the 'labels' field.  This includes
        # notifications with a label_query. Part of the Notification creation
        # process picks out all labels in the label_query (even negated ones)
        # and adds the to the 'labels' field.
        base_notifications = self.label.notification_set.all()

        # Get and apply filter query to trim it down
        filter_query = self.get_filter_query()
        notifications = base_notifications.filter(filter_query)

        # Do label filtering
        final_notifications = self.filter_for_labels(notifications)

        # Get email and phone recipients and return
        return final_notifications


class LabelRemovedRecipientGetter(LabelAddedRecipientGetter):

    def filter_for_labels(self, notifications):
        # Only notifications with a label query should be triggered
        # by a label_removed alert, since notifications with a
        # label set can only have non-negated labels.
        notification_qs = notifications.filter(label_query__isnull=False)
        pks = evaluate_label_queries(self.label_names, notification_qs)
        return Notification.objects.filter(pk__in=pks)


# Dict which maps alert types to recipient getter classes
ALERT_TYPE_RECIPIENT_GETTERS = {
    'new': CreationRecipientGetter,
    'update': UpdateRecipientGetter,
    'label_added': LabelAddedRecipientGetter,
    'label_removed': LabelRemovedRecipientGetter,
}
