import copy
import pytest
import re

from django.contrib.auth import get_user_model

from alerts.models import Contact, Notification
from events.models import Label, Group, Pipeline, Search, Event
from superevents.models import Superevent
from .constants import (
    DEFAULT_FAR_T, DEFAULT_LABELS, DEFAULT_LABEL_QUERY, LABEL_QUERY2,
    RANDOM_LABEL, LABEL_QUERY_PARSER, DEFAULT_GROUP, DEFAULT_PIPELINE,
    DEFAULT_SEARCH
)

UserModel = get_user_model()


###############################################################################
# UTILITY FUNCTIONS ###########################################################
###############################################################################
def create_notification(
    user,
    notification_category,
    contact_description='test',
    phone=None,
    email=None,
    phone_method=Contact.CONTACT_PHONE_BOTH,
    notification_description='test',
    far_threshold=None,
    ns_candidate=None,
    label_names=None,
    label_query=None,
    groups=None,
    pipelines=None,
    searches=None,
):
    # Create contact
    contact_dict = {}
    if phone is not None and email is not None:
        raise ValueError("Specify only one of label_names or label_query")
    elif phone:
        contact_dict['phone'] = phone
        contact_dict['phone_method'] = phone_method
    elif email:
        contact_dict['email'] = email
    c = Contact.objects.create(
        user=user,
        description=contact_description,
        verified=True,
        **contact_dict
    )

    # Create notification
    notification_dict = {}
    if far_threshold:
        notification_dict['far_threshold'] = far_threshold
    if ns_candidate:
        notification_dict['ns_candidate'] = ns_candidate
    if label_query:
        notification_dict['label_query'] = label_query
        
    n = Notification.objects.create(
        user=user,
        description=notification_description,
        category=notification_category,
        **notification_dict
    )
    # Add m2m relations
    n.contacts.add(c)
    if label_names and label_query:
        raise ValueError('')
    elif label_query:
        label_names = LABEL_QUERY_PARSER.findall(label_query)
    if label_names:
        for l in label_names:
            label, _ = Label.objects.get_or_create(name=l)
            n.labels.add(label)
    if notification_category == Notification.NOTIFICATION_CATEGORY_EVENT:
        if groups:
            for g in groups:
                group, _ = Group.objects.get_or_create(name=g)
                n.groups.add(group)
        if pipelines:
            for p in pipelines:
                pipeline, _ = Pipeline.objects.get_or_create(name=p)
                n.pipelines.add(pipeline)
        if searches:
            for s in searches:
                search, _ = Search.objects.get_or_create(name=s)
                n.searches.add(search)
    return n


###############################################################################
# FIXTURES ####################################################################
###############################################################################
@pytest.mark.django_db
@pytest.fixture
def event():
    group, _ = Group.objects.get_or_create(name='event_group')
    pipeline, _ = Pipeline.objects.get_or_create(name='event_pipeline')
    search, _ = Search.objects.get_or_create(name='event_search')
    user = UserModel.objects.create(username='event.creator')
    event = Event.objects.create(group=group, pipeline=pipeline, search=search,
                                 far=1, submitter=user)
    return event


@pytest.mark.django_db
@pytest.fixture
def superevent(event):
    user = UserModel.objects.create(username='superevent.creator')
    superevent = Superevent.objects.create(submitter=user, t_start=0, t_0=1,
                                           t_end=2, preferred_event=event)
    return superevent


SUPEREVENT_NOTIFICATION_DATA = [
    dict(desc='all'),
    dict(desc='far_t_only', far_threshold=DEFAULT_FAR_T),
    dict(desc='nscand_only', ns_candidate=True),
    dict(desc='labels_only', label_names=DEFAULT_LABELS),
    dict(desc='labelq_only', label_query=DEFAULT_LABEL_QUERY['query']),
    dict(desc='far_t_and_nscand', far_threshold=DEFAULT_FAR_T,
         ns_candidate=True),
    dict(desc='far_t_and_labels', far_threshold=DEFAULT_FAR_T,
         label_names=DEFAULT_LABELS),
    dict(desc='far_t_and_labelq', far_threshold=DEFAULT_FAR_T,
         label_query=DEFAULT_LABEL_QUERY['query']),
    dict(desc='nscand_and_labels', ns_candidate=True,
         label_names=DEFAULT_LABELS),
    dict(desc='nscand_and_labelq', ns_candidate=True,
         label_query=DEFAULT_LABEL_QUERY['query']),
    dict(desc='far_t_and_nscand_and_labels', far_threshold=DEFAULT_FAR_T,
         ns_candidate=True, label_names=DEFAULT_LABELS),
    dict(desc='far_t_and_nscand_and_labelq', far_threshold=DEFAULT_FAR_T,
         ns_candidate=True, label_query=DEFAULT_LABEL_QUERY['query']),
    dict(desc='labelq2_only', label_query=LABEL_QUERY2),
    dict(desc='far_t_and_labelq2', far_threshold=DEFAULT_FAR_T,
         label_query=LABEL_QUERY2),
    dict(desc='nscand_and_labelq2', ns_candidate=True,
         label_query=LABEL_QUERY2),
    dict(desc='far_t_and_nscand_and_labelq2', far_threshold=DEFAULT_FAR_T,
         ns_candidate=True, label_query=LABEL_QUERY2),
]
@pytest.mark.django_db
@pytest.fixture
def superevent_notifications(request):
    # Get user fixture
    user = request.getfixturevalue('internal_user')

    # Create notifications
    notification_pks = []
    notification_data = copy.deepcopy(SUPEREVENT_NOTIFICATION_DATA) 
    for notification_dict in notification_data:
        desc = notification_dict.pop('desc')
        n = create_notification(
            user,
            Notification.NOTIFICATION_CATEGORY_SUPEREVENT,
            phone='12345678901',
            notification_description=desc,
            **notification_dict
        )
        notification_pks.append(n.pk)

    return Notification.objects.filter(pk__in=notification_pks)


EVENT_NOTIFICATION_DATA = copy.deepcopy(SUPEREVENT_NOTIFICATION_DATA)
EVENT_NOTIFICATION_DATA += [
    dict(desc='gps_only', groups=[DEFAULT_GROUP], pipelines=[DEFAULT_PIPELINE],
         searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_gps', far_threshold=DEFAULT_FAR_T,
         groups=[DEFAULT_GROUP], pipelines=[DEFAULT_PIPELINE],
         searches=[DEFAULT_SEARCH]),
    dict(desc='nscand_and_gps', ns_candidate=True,
         groups=[DEFAULT_GROUP], pipelines=[DEFAULT_PIPELINE],
         searches=[DEFAULT_SEARCH]),
    dict(desc='labels_and_gps', label_names=DEFAULT_LABELS,
         groups=[DEFAULT_GROUP], pipelines=[DEFAULT_PIPELINE],
         searches=[DEFAULT_SEARCH]),
    dict(desc='labelq_and_gps', label_query=DEFAULT_LABEL_QUERY['query'],
         groups=[DEFAULT_GROUP], pipelines=[DEFAULT_PIPELINE],
         searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_nscand_and_gps', far_threshold=DEFAULT_FAR_T,
         ns_candidate=True, groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_labels_and_gps', far_threshold=DEFAULT_FAR_T,
         label_names=DEFAULT_LABELS, groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_labelq_and_gps', far_threshold=DEFAULT_FAR_T,
         label_query=DEFAULT_LABEL_QUERY['query'], groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='nscand_and_labels_and_gps', ns_candidate=True,
         label_names=DEFAULT_LABELS, groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='nscand_and_labelq_and_gps', ns_candidate=True,
         label_query=DEFAULT_LABEL_QUERY['query'], groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_nscand_and_labels_and_gps',
         far_threshold=DEFAULT_FAR_T, ns_candidate=True,
         label_names=DEFAULT_LABELS, groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_nscand_and_labelq_and_gps',
         far_threshold=DEFAULT_FAR_T, ns_candidate=True,
         label_query=DEFAULT_LABEL_QUERY['query'], groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='labelq2_and_gps', label_query=LABEL_QUERY2,
         groups=[DEFAULT_GROUP], pipelines=[DEFAULT_PIPELINE],
         searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_labelq2_and_gps', far_threshold=DEFAULT_FAR_T,
         label_query=LABEL_QUERY2, groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='nscand_and_labelq2_and_gps', ns_candidate=True,
         label_query=LABEL_QUERY2, groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
    dict(desc='far_t_and_nscand_and_labelq2_and_gps',
         far_threshold=DEFAULT_FAR_T, ns_candidate=True,
         label_query=LABEL_QUERY2, groups=[DEFAULT_GROUP],
         pipelines=[DEFAULT_PIPELINE], searches=[DEFAULT_SEARCH]),
]
@pytest.mark.django_db
@pytest.fixture
def event_notifications(request):
    # Get user fixture
    user = request.getfixturevalue('internal_user')

    # Create notifications
    notification_pks = []
    notification_data = copy.deepcopy(EVENT_NOTIFICATION_DATA) 
    for notification_dict in notification_data:
        desc = notification_dict.pop('desc')
        n = create_notification(
            user,
            Notification.NOTIFICATION_CATEGORY_EVENT,
            phone='12345678901',
            notification_description=desc,
            **notification_dict
        )
        notification_pks.append(n.pk)

    return Notification.objects.filter(pk__in=notification_pks)
