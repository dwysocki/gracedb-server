try:
    from unittest import mock
except ImportError:  # python < 3
    import mock
import datetime
import pytest
import pytz

from django.conf import settings
from django.db.models import Q

from superevents.models import Superevent
from search.constants import RUN_MAP
from search.query.events import parseQuery
from search.query.superevents import parseSupereventQuery


def prefix_keys(prefix, dict):
    return {f"{prefix}{k}": v for k, v in dict.items()}


# Get server timezone
SERVER_TZ = pytz.timezone(settings.TIME_ZONE)


# Label names to use in Label list mock
MOCK_LABEL_LIST = ['LABEL1', 'LABEL2', 'LABEL3']
# Datetime to use in timezone.now() mock
MOCK_NOW_DT = SERVER_TZ.localize(datetime.datetime(2019, 3, 31, 10, 50, 0))

# Tests -----------------------------------------------------------------------
DEFAULT_Q = ~Q(category=Superevent.SUPEREVENT_CATEGORY_TEST) & \
    ~Q(category=Superevent.SUPEREVENT_CATEGORY_MDC)
SUPEREVENT_QUERY_TEST_DATA = [
    ("", DEFAULT_Q),
    ("id: S190509bc",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("S190509bc"))),
    ("id: Tgw190331eBz",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("TGW190331EBZ"))),
    ("id: ms190331BCdE",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("MS190331bcde"))),
    ("superevent_id: S190509bc",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("S190509bc"))),
    ("S190509bc",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("S190509bc"))),
    ("TS190509bc",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("TS190509bc"))),
    ("MS190509bc",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("MS190509bc"))),
    ("GW121203K",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("GW121203K"))),
    ("MGW180923ZZZ",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("MGW180923ZZZ"))),
    # Test case with missing letter suffix
    ("GW150914",
        Q(**Superevent.get_filter_kwargs_for_date_id_lookup("GW150914A"))),
    ("Test", Q(category=Superevent.SUPEREVENT_CATEGORY_TEST)),
    ("category: Test", Q(category=Superevent.SUPEREVENT_CATEGORY_TEST)),
    ("MDC", Q(category=Superevent.SUPEREVENT_CATEGORY_MDC)),
    ("category: MDC", Q(category=Superevent.SUPEREVENT_CATEGORY_MDC)),
    ("category: Production",
        Q(category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION)),
    ("t_0: 1234.5678", Q(t_0=1234.5678) & DEFAULT_Q),
    ("t_0: 1234.56 .. 3456.78", Q(t_0__range=[1234.56, 3456.78]) &
        DEFAULT_Q),
    ("gpstime: 1234.5678", Q(t_0=1234.5678) & DEFAULT_Q),
    ("gpstime: 1234.56 .. 3456.78", Q(t_0__range=[1234.56, 3456.78]) &
        DEFAULT_Q),
    ("t_start: 1234.5678", Q(t_start=1234.5678) & DEFAULT_Q),
    ("t_start: 1234.56 .. 3456.78", Q(t_start__range=[1234.56, 3456.78]) &
        DEFAULT_Q),
    ("t_end: 1234.5678", Q(t_end=1234.5678) & DEFAULT_Q),
    ("t_end: 1234.56 .. 3456.78", Q(t_end__range=[1234.56, 3456.78]) &
        DEFAULT_Q),
    ("submitter: \"test\"", (Q(submitter__username__icontains="test") | 
        Q(submitter__last_name__icontains="test")) & DEFAULT_Q),
    ("\"test\"", (Q(submitter__username__icontains="test") | 
        Q(submitter__last_name__icontains="test")) & DEFAULT_Q),
    ('preferred_event: G1234', Q(preferred_event__id=1234) & DEFAULT_Q),
    ('preferred_event: G1234 .. G2345',
        Q(preferred_event__id__range=[1234, 2345]) & DEFAULT_Q),
    ('event: G1234', Q(events__id=1234) & DEFAULT_Q),
    ('event: G1234 .. G2345', Q(events__id__range=[1234, 2345]) & DEFAULT_Q),
    ('events: G1234', Q(events__id=1234) & DEFAULT_Q),
    ('events: G1234 .. G2345', Q(events__id__range=[1234, 2345]) & DEFAULT_Q),
    ('is_gw: True', Q(is_gw=True) & DEFAULT_Q),
    ('is_gw: False', Q(is_gw=False) & DEFAULT_Q),
    ('is_public: True', Q(is_exposed=True) & DEFAULT_Q),
    ('is_public: False', Q(is_exposed=False) & DEFAULT_Q),
    ('is_exposed: True', Q(is_exposed=True) & DEFAULT_Q),
    ('is_exposed: False', Q(is_exposed=False) & DEFAULT_Q),
    ('status: public', Q(is_exposed=True) & DEFAULT_Q),
    ('status: internal', Q(is_exposed=False) & DEFAULT_Q),
    ('public', Q(is_exposed=True) & DEFAULT_Q),
    ('internal', Q(is_exposed=False) & DEFAULT_Q),
    ('category: production',
        Q(category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION)),
    ('Test',
        Q(category=Superevent.SUPEREVENT_CATEGORY_TEST)),
    ('category: MDC',
        Q(category=Superevent.SUPEREVENT_CATEGORY_MDC)),
    ('created: 2019-05-04', Q(created=SERVER_TZ.localize(datetime.datetime(
        2019, 5, 4, 0, 0, 0))) & DEFAULT_Q),
    ('created: 2019-05-04 01:23:45 .. 2019-05-05 12:34:56',
        Q(created__range=[
        SERVER_TZ.localize(datetime.datetime(2019, 5, 4, 1, 23, 45)),
        SERVER_TZ.localize(datetime.datetime(2019, 5, 5, 12, 34, 56))]) &
        DEFAULT_Q),
    ('yesterday .. now', Q(created__range=[
        MOCK_NOW_DT.replace(day=MOCK_NOW_DT.day-1, hour=0, minute=0,
            second=0, microsecond=0), MOCK_NOW_DT]) & DEFAULT_Q),
    ('a couple of days ago', Q(created=MOCK_NOW_DT.replace(
        day=MOCK_NOW_DT.day-2)) & DEFAULT_Q),
    ('1 week ago .. now', Q(created__range=[
        MOCK_NOW_DT - datetime.timedelta(days=7), MOCK_NOW_DT]) & DEFAULT_Q),
    ('3 days ago .. 2 days ago', Q(created__range=[
        MOCK_NOW_DT - datetime.timedelta(days=3),
        MOCK_NOW_DT - datetime.timedelta(days=2)]) & DEFAULT_Q),
    ('noon', Q(created=MOCK_NOW_DT.replace(hour=12, minute=0, second=0,
        microsecond=0)) & DEFAULT_Q),
    ('far <= 1e-10', Q(preferred_event__far__lte=1e-10) & DEFAULT_Q),
    ('far < 1e-10', Q(preferred_event__far__lt=1e-10) & DEFAULT_Q),
    ('far > 1e-10', Q(preferred_event__far__gt=1e-10) & DEFAULT_Q),
    ('far >= 1e-10', Q(preferred_event__far__gte=1e-10) & DEFAULT_Q),
    ('far: 0.001', Q(preferred_event__far=0.001) & DEFAULT_Q),
    ('far in 1e-5, 1e-4', Q(preferred_event__far__range=[1e-5, 1e-4]) &
        DEFAULT_Q),
    ('far: 1e-5 .. 1e-4', Q(preferred_event__far__range=[1e-5, 1e-4]) &
        DEFAULT_Q),
    ('far: 1e-5 - 1e-4', Q(preferred_event__far__range=[1e-5, 1e-4]) &
        DEFAULT_Q),
    # A few complex queries
    ('far in 1e-10, 1e-8 created: yesterday public',
        Q(preferred_event__far__range=[1e-10, 1e-8]) &
        Q(created=SERVER_TZ.localize(datetime.datetime(2019, 3, 30))) &
        Q(is_exposed=True) & DEFAULT_Q),
    ('gpstime: 123 .. 456 Test events: G123 .. G129',
        Q(t_0__range=[123, 456]) &
        Q(category=Superevent.SUPEREVENT_CATEGORY_TEST) &
        Q(events__id__range=[123, 129])),
]
# Add tests based on run IDs
RUNID_QUERY_DATA = [(k, Q(t_0__range=v) & (DEFAULT_Q))
    for k,v in RUN_MAP.items()]
SUPEREVENT_QUERY_TEST_DATA.extend(RUNID_QUERY_DATA)

@pytest.mark.parametrize("query,expected_Q_result", SUPEREVENT_QUERY_TEST_DATA)
def test_superevent_queries(query, expected_Q_result):
    # Mock out label queries
    with mock.patch('search.query.labels.Label.objects.values_list') as mock_labels_list, \
        mock.patch('events.nltime.timezone.now') as mock_now:
        # Set up mocks
        mock_labels_list.return_value = MOCK_LABEL_LIST
        mock_now.return_value = MOCK_NOW_DT

        # Run query
        Q_result = parseSupereventQuery(query)

    assert Q_result == expected_Q_result


# Group, pipeline, search names to use in mocks
MOCK_GROUP_LIST = ['Test', 'External', 'GROUP1', 'GROUP2']
MOCK_PIPELINE_LIST = ['HardwareInjection', 'PIPELINE1', 'PIPELINE2']
MOCK_SEARCH_LIST = ['MDC', 'SEARCH1', 'SEARCH2']

DEFAULT_EVENT_Q__GROUP_NAME = ~Q(group__name='Test')
DEFAULT_EVENT_Q__SEARCH_NAME = ~Q(search__name='MDC')
DEFAULT_EVENT_Q = DEFAULT_EVENT_Q__GROUP_NAME & DEFAULT_EVENT_Q__SEARCH_NAME
# NOTE: the event query stuff is just too nasty.  Attempts at testing
# are not going well.  It needs a full rework.
EVENT_QUERY_TEST_DATA = [
    # Default query
    ("", DEFAULT_EVENT_Q),
    # By instrument
    ("instruments: \"L1\"", Q(instruments="L1") & DEFAULT_EVENT_Q),
    ("instruments: \"H1,L1,V1\"", Q(instruments="H1,L1,V1") & DEFAULT_EVENT_Q),
    # By FAR
    ("far <= 1e-7", Q(far__lte=1e-7) & DEFAULT_EVENT_Q),
    ("far < 1e-7", Q(far__lt=1e-7) & DEFAULT_EVENT_Q),
    ("far > 1e-7", Q(far__gt=1e-7) & DEFAULT_EVENT_Q),
    ("far >= 1e-7", Q(far__gte=1e-7) & DEFAULT_EVENT_Q),
    ("far: 0.001", Q(far=0.001) & DEFAULT_EVENT_Q),
    # By event attributes
    ("singleinspiral.mchirp >= 0.5 & singleinspiral.eff_distance in 0.0,55",
        Q(singleinspiral__mchirp__gte=0.5) &
        Q(singleinspiral__eff_distance__range=[0.0, 55]) &
        DEFAULT_EVENT_Q),
    ("(si.channel = \"DMT-STRAIN\" | si.channel = \"DMT-PAIN\") & si.snr < 5",
        (Q(singleinspiral__channel="DMT-STRAIN") |
         Q(singleinspiral__channel="DMT-PAIN")) &
        Q(singleinspiral__snr__lt=5) & DEFAULT_EVENT_Q),
    ("mb.snr in 1,3 & mb.central_freq > 1000",
        Q(multiburstevent__snr__range=[1, 3]) &
        Q(multiburstevent__central_freq__gt=1000) &
        DEFAULT_EVENT_Q),
    # By GPS time
    ("gpstime: 899999000 .. 999999999",
        Q(gpstime__range=["899999000", "999999999"]) & DEFAULT_EVENT_Q),
    ("899999000 .. 999999999",
        Q(gpstime__range=["899999000", "999999999"]) & DEFAULT_EVENT_Q),
    # By creation time
    ('created: 2019-05-04', Q(created=SERVER_TZ.localize(datetime.datetime(
        2019, 5, 4, 0, 0, 0))) & DEFAULT_EVENT_Q),
    ('created: 2019-05-04 01:23:45 .. 2019-05-05 12:34:56',
        Q(created__range=[
        SERVER_TZ.localize(datetime.datetime(2019, 5, 4, 1, 23, 45)),
        SERVER_TZ.localize(datetime.datetime(2019, 5, 5, 12, 34, 56))]) &
        DEFAULT_EVENT_Q),
    ('yesterday .. now', Q(created__range=[
        MOCK_NOW_DT.replace(day=MOCK_NOW_DT.day-1, hour=0, minute=0,
            second=0, microsecond=0), MOCK_NOW_DT]) & DEFAULT_EVENT_Q),
    ('a couple of days ago', Q(created=MOCK_NOW_DT.replace(
        day=MOCK_NOW_DT.day-2)) & DEFAULT_EVENT_Q),
    ('created: 1 week ago .. now', Q(created__range=[
        MOCK_NOW_DT - datetime.timedelta(days=7), MOCK_NOW_DT]) &
        DEFAULT_EVENT_Q),
    ('created: 3 days ago .. 2 days ago', Q(created__range=[
        MOCK_NOW_DT - datetime.timedelta(days=3),
        MOCK_NOW_DT - datetime.timedelta(days=2)]) & DEFAULT_EVENT_Q),
    ('noon', Q(created=MOCK_NOW_DT.replace(hour=12, minute=0, second=0,
        microsecond=0)) & DEFAULT_EVENT_Q),
    # By graceid
    ("G1234", Q(id="1234") & DEFAULT_EVENT_Q),
    ("gid: G1234", Q(id="1234") & DEFAULT_EVENT_Q),
    ("G1234 .. G1240", Q(id__range=["1234", "1240"]) & DEFAULT_EVENT_Q),
    ("gid: G1234 .. G1240", Q(id__range=["1234", "1240"]) & DEFAULT_EVENT_Q),
    ("G1234 G1235 G1236", (Q(id="1234") | Q(id="1235") | Q(id="1236")) &
        DEFAULT_EVENT_Q),
    ("gid: G1234 G1235 G1236", (Q(id="1234") | Q(id="1235") | Q(id="1236")) &
        DEFAULT_EVENT_Q),
    # By hardware injection id
    ## NOTE: without 'hid:' this gets confused with the 'H1' instrument
    ("hid: H1234", Q(id="1234") & Q(pipeline__name="HardwareInjection") &
        DEFAULT_EVENT_Q),
    ("H3456", Q(id="3456") & Q(pipeline__name="HardwareInjection") &
        DEFAULT_EVENT_Q),
    # By test event id
    ("tid: T1234", Q(id="1234") & Q(group__name="Test") &
        DEFAULT_EVENT_Q__SEARCH_NAME),
    ("T1234", Q(id="1234") & Q(group__name="Test") &
        DEFAULT_EVENT_Q__SEARCH_NAME),
    # By external trigger event id
    ("eid: E1234", Q(id="1234") & Q(group__name="External") & DEFAULT_EVENT_Q),
    ("E1234", Q(id="1234") & Q(group__name="External") & DEFAULT_EVENT_Q),
    # By MDC event id
    ("mid: M1234", Q(id="1234") & Q(search__name="MDC") &
        DEFAULT_EVENT_Q__GROUP_NAME),
    ("M1234", Q(id="1234") & Q(search__name="MDC") &
        DEFAULT_EVENT_Q__GROUP_NAME),
    # By group, pipeline, and search
    ("GROUP1 SEARCH1", Q(group__name__in=["GROUP1"]) &
        DEFAULT_EVENT_Q__GROUP_NAME & Q(search__name__in=["SEARCH1"]) &
        DEFAULT_EVENT_Q__SEARCH_NAME),
    ("group: GROUP1 search: SEARCH1", Q(group__name__in=["GROUP1"]) &
        DEFAULT_EVENT_Q__GROUP_NAME & Q(search__name__in=["SEARCH1"]) &
        DEFAULT_EVENT_Q__SEARCH_NAME),
    ("PIPELINE1", Q(pipeline__name__in=["PIPELINE1"]) & DEFAULT_EVENT_Q),
    ("PIPELINE1 group: GROUP1 SEARCH1 pipeline: PIPELINE2",
        ( Q(pipeline__name__in=["PIPELINE1"])
        | Q(pipeline__name__in=["PIPELINE2"]) ) &
        Q(group__name__in=["GROUP1"]) & DEFAULT_EVENT_Q__GROUP_NAME &
        Q(search__name__in=["SEARCH1"]) & DEFAULT_EVENT_Q__SEARCH_NAME),
    ("Test MDC", Q(group__name__in=["Test"]) & Q(search__name__in=["MDC"])),
    # By label
    ## These don't work because of the separate label parser
#    ("label: LABEL1", Q(label="LABEL1") & DEFAULT_EVENT_Q),
#    ("LABEL1", Q(label="LABEL1") & DEFAULT_EVENT_Q),
    # By submitter
    ("\"waveburst\"",
        ( Q(submitter__username__icontains="waveburst")
        | Q(submitter__last_name__icontains="waveburst") ) &
        DEFAULT_EVENT_Q),
    ("submitter: \"albert.einstein@ligo.org\"",
        ( Q(submitter__username__icontains="albert.einstein@ligo.org")
        | Q(submitter__last_name__icontains="albert.einstein@ligo.org") ) &
        DEFAULT_EVENT_Q),
    # By superevent status
    ("in_superevent: True", Q(superevent__isnull=False) & DEFAULT_EVENT_Q),
    ("in_superevent: False", Q(superevent__isnull=True) & DEFAULT_EVENT_Q),
    ("superevent: S180525c",
        Q(**prefix_keys("superevent__",
                        Superevent.get_filter_kwargs_for_date_id_lookup("S180525c"))) &
        DEFAULT_EVENT_Q),
    ("is_preferred_event: True", Q(superevent_preferred_for__isnull=False) &
        DEFAULT_EVENT_Q),
    ("is_preferred_event: False", Q(superevent_preferred_for__isnull=True) &
        DEFAULT_EVENT_Q),
]
@pytest.mark.parametrize("query,expected_Q_result", EVENT_QUERY_TEST_DATA)
def test_event_queries(query, expected_Q_result):
    # Mock out label queries
    with mock.patch('search.query.labels.Label.objects.values_list') as mock_labels_list, \
        mock.patch('search.query.events.Group.objects.values_list') as mock_group_list, \
        mock.patch('search.query.events.Pipeline.objects.values_list') as mock_pipeline_list, \
        mock.patch('search.query.events.Search.objects.values_list') as mock_search_list, \
        mock.patch('events.nltime.timezone.now') as mock_now:
        # Set up mocks
        mock_labels_list.return_value = MOCK_LABEL_LIST
        mock_group_list.return_value = MOCK_GROUP_LIST
        mock_pipeline_list.return_value = MOCK_PIPELINE_LIST
        mock_search_list.return_value = MOCK_SEARCH_LIST
        mock_now.return_value = MOCK_NOW_DT

        # Run query
        Q_result = parseQuery(query)

    assert Q_result == expected_Q_result
