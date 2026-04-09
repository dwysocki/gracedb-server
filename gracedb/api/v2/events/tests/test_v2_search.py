"""
Integration tests for the v2 event search API.

Two search paths are tested:
  1. GET /api/v2/events/?query=<json>   — URL-parameter-based search
  2. POST /api/v2/events/search/        — body-based search (JSON or YAML)
"""
import json

from django.urls import reverse

from api.tests.utils import GraceDbApiTestBase
from core.tests.utils import GraceDbTestBase
from events.models import Event, Label, Labelling
from events.tests.mixins import EventCreateMixin
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    viewname = f'api:{API_VERSION}:' + viewname
    return reverse(viewname, *args, **kwargs)


def _list_url():
    return v_reverse('events:event-list')


def _search_url():
    return v_reverse('events:event-search')


def _get_query_param(client, user, query_dict):
    client.force_login(user)
    response = client.get(
        _list_url(),
        {'query': json.dumps(query_dict)},
    )
    client.logout()
    return response


def _post_json(client, user, body):
    client.force_login(user)
    response = client.post(
        _search_url(),
        data=json.dumps(body),
        content_type='application/json',
    )
    client.logout()
    return response


def _post_yaml(client, user, yaml_body):
    client.force_login(user)
    response = client.post(
        _search_url(),
        data=yaml_body,
        content_type='application/yaml',
    )
    client.logout()
    return response


class TestV2EventSearchBasic(EventCreateMixin, GraceDbApiTestBase):
    """Basic query correctness tests for the v2 event-list and search endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.list_url = _list_url()
        cls.search_url = _search_url()

        cls.cbc_event_1 = cls.create_event('CBC', 'gstlal', user=cls.internal_user)
        cls.cbc_event_2 = cls.create_event('CBC', 'MBTA', user=cls.internal_user)
        cls.burst_event = cls.create_event('Burst', 'CWB', user=cls.internal_user)

    def _ids(self, response):
        return {e['graceid'] for e in response.data['events']}

    # ------------------------------------------------------------------
    # No-query / empty-query
    # ------------------------------------------------------------------

    def test_no_query_returns_events(self):
        """GET without a query returns accessible events."""
        response = self.request_as_user(self.list_url, 'GET', self.internal_user)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertIn(self.burst_event.graceid, ids)

    def test_empty_and_via_get_returns_all(self):
        """GET ?query=empty-and returns the unfiltered accessible set."""
        response = _get_query_param(self.client, self.internal_user, {'field': 'gpstime', 'op': '>', 'value': -1})
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertIn(self.burst_event.graceid, ids)

    def test_empty_and_via_post_returns_all(self):
        """POST search with empty AND returns the unfiltered accessible set."""
        body = {'object_type': 'event', 'query': {'field': 'gpstime', 'op': '>', 'value': -1}}
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertIn(self.burst_event.graceid, ids)

    # ------------------------------------------------------------------
    # GET with ?query= URL parameter
    # ------------------------------------------------------------------

    def test_get_query_param_group_cbc(self):
        """?query=<json> filters by group=CBC."""
        node = {'field': 'group', 'op': '=', 'value': 'CBC'}
        response = _get_query_param(self.client, self.internal_user, node)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertIn(self.cbc_event_2.graceid, ids)
        self.assertNotIn(self.burst_event.graceid, ids)

    def test_get_query_param_pipeline_gstlal(self):
        """?query=<json> filters by pipeline=gstlal."""
        node = {'field': 'pipeline', 'op': '=', 'value': 'gstlal'}
        response = _get_query_param(self.client, self.internal_user, node)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertNotIn(self.cbc_event_2.graceid, ids)
        self.assertNotIn(self.burst_event.graceid, ids)

    # ------------------------------------------------------------------
    # POST /search/ with JSON body
    # ------------------------------------------------------------------

    def test_post_search_group_cbc(self):
        """POST search by group=CBC returns only CBC events."""
        body = {
            'object_type': 'event',
            'query': {'field': 'group', 'op': '=', 'value': 'CBC'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertIn(self.cbc_event_2.graceid, ids)
        self.assertNotIn(self.burst_event.graceid, ids)

    def test_post_search_group_burst(self):
        """POST search by group=Burst returns only Burst events."""
        body = {
            'object_type': 'event',
            'query': {'field': 'group', 'op': '=', 'value': 'Burst'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.burst_event.graceid, ids)
        self.assertNotIn(self.cbc_event_1.graceid, ids)

    # ------------------------------------------------------------------
    # YAML body
    # ------------------------------------------------------------------

    def test_yaml_body_accepted(self):
        """A YAML query body is accepted."""
        yaml_body = (
            'object_type: event\n'
            'query:\n'
            '  field: group\n'
            '  op: "="\n'
            '  value: CBC\n'
        )
        response = _post_yaml(self.client, self.internal_user, yaml_body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertNotIn(self.burst_event.graceid, ids)

    # ------------------------------------------------------------------
    # Combinators
    # ------------------------------------------------------------------

    def test_and_combinator(self):
        """AND(group=CBC, pipeline=gstlal) returns only cbc_event_1."""
        body = {
            'object_type': 'event',
            'query': {
                'and': [
                    {'field': 'group', 'op': '=', 'value': 'CBC'},
                    {'field': 'pipeline', 'op': '=', 'value': 'gstlal'},
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertNotIn(self.cbc_event_2.graceid, ids)
        self.assertNotIn(self.burst_event.graceid, ids)

    def test_or_combinator(self):
        """OR(group=CBC, group=Burst) returns all three events."""
        body = {
            'object_type': 'event',
            'query': {
                'or': [
                    {'field': 'group', 'op': '=', 'value': 'CBC'},
                    {'field': 'group', 'op': '=', 'value': 'Burst'},
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.cbc_event_1.graceid, ids)
        self.assertIn(self.cbc_event_2.graceid, ids)
        self.assertIn(self.burst_event.graceid, ids)

    def test_not_combinator(self):
        """NOT group=CBC returns only Burst events."""
        body = {
            'object_type': 'event',
            'query': {
                'not': {'field': 'group', 'op': '=', 'value': 'CBC'},
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.burst_event.graceid, ids)
        self.assertNotIn(self.cbc_event_1.graceid, ids)
        self.assertNotIn(self.cbc_event_2.graceid, ids)

    # ------------------------------------------------------------------
    # Unauthenticated
    # ------------------------------------------------------------------

    def test_unauthenticated_search_rejected(self):
        """Anonymous POST to /search/ is rejected."""
        body = {'object_type': 'event', 'query': {'field': 'gpstime', 'op': '>', 'value': -1}}
        response = self.client.post(
            self.search_url,
            data=json.dumps(body),
            content_type='application/json',
        )
        self.assertIn(response.status_code, (401, 403))


class TestV2EventSearchErrors(EventCreateMixin, GraceDbApiTestBase):
    """Error handling tests for the v2 event search endpoints."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()
        cls.list_url = _list_url()
        cls.event = cls.create_event('CBC', 'gstlal', user=cls.internal_user)

    def _assert_invalid_query(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('error'), 'invalid_query')
        self.assertEqual(response.data.get('version'), '2')

    def test_invalid_json_body_returns_400(self):
        """Malformed JSON body → 400 with structured error."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data='not json at all }{',
            content_type='application/json',
        )
        self.client.logout()
        self._assert_invalid_query(response)

    def test_invalid_yaml_returns_400(self):
        """Malformed YAML body → 400."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data=': bad yaml ][}',
            content_type='application/yaml',
        )
        self.client.logout()
        self._assert_invalid_query(response)

    def test_unknown_field_via_post_returns_400(self):
        """Unknown field name in POST body → 400."""
        body = {
            'object_type': 'event',
            'query': {'field': 'bogus_field_xyz', 'op': '=', 'value': '1'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)

    def test_unknown_field_via_get_param_returns_400(self):
        """Unknown field name in GET ?query= → 400."""
        node = {'field': 'bogus_field_xyz', 'op': '=', 'value': '1'}
        response = _get_query_param(self.client, self.internal_user, node)
        self._assert_invalid_query(response)

    def test_wrong_object_type_returns_400(self):
        """object_type='superevent' sent to events endpoint → 400."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'far', 'op': '<', 'value': 1e-10},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)
        self.assertIn('event', response.data['message'])

    def test_bad_operator_for_field_returns_400(self):
        """Operator not valid for the field type → 400."""
        body = {
            'object_type': 'event',
            'query': {'field': 'group', 'op': '<', 'value': 'CBC'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)

    def test_body_not_dict_returns_400(self):
        """JSON array body → 400."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data=json.dumps(['not', 'a', 'dict']),
            content_type='application/json',
        )
        self.client.logout()
        self._assert_invalid_query(response)

    def test_invalid_json_in_get_param_returns_400(self):
        """Malformed JSON in ?query= GET parameter → 400."""
        self.client.force_login(self.internal_user)
        response = self.client.get(self.list_url, {'query': 'not-valid-json'})
        self.client.logout()
        self._assert_invalid_query(response)


class TestV2EventSearchDefaultFilter(EventCreateMixin, GraceDbApiTestBase):
    """
    Verify that the default filter hides Test-group and MDC-search events
    from queries that do not explicitly reference group/search/id, and that
    an explicit group=Test query does return those events.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()
        cls.list_url = _list_url()

        cls.cbc_event = cls.create_event('CBC', 'gstlal', user=cls.internal_user)
        cls.test_event = cls.create_event('Test', 'gstlal', user=cls.internal_user)
        cls.mdc_event = cls.create_event('CBC', 'gstlal',
                                         search_name='MDC',
                                         user=cls.internal_user)

    def _ids(self, response):
        return {e['graceid'] for e in response.data['events']}

    def test_default_filter_hides_test_group_events(self):
        """Without an explicit group filter, Test-group events must not appear."""
        body = {
            'object_type': 'event',
            'query': {'field': 'gpstime', 'op': '>', 'value': -1},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.test_event.graceid, ids)
        self.assertIn(self.cbc_event.graceid, ids)

    def test_default_filter_hides_mdc_search_events(self):
        """Without an explicit search filter, MDC-search events must not appear."""
        body = {
            'object_type': 'event',
            'query': {'field': 'gpstime', 'op': '>', 'value': -1},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.mdc_event.graceid, ids)

    def test_explicit_group_test_bypasses_default_filter(self):
        """An explicit group=Test condition must return Test-group events."""
        body = {
            'object_type': 'event',
            'query': {'field': 'group', 'op': '=', 'value': 'Test'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.test_event.graceid, ids)
        self.assertNotIn(self.cbc_event.graceid, ids)

    def test_explicit_search_mdc_bypasses_default_filter(self):
        """An explicit search=MDC condition must return MDC events."""
        body = {
            'object_type': 'event',
            'query': {'field': 'search', 'op': '=', 'value': 'MDC'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.mdc_event.graceid, ids)

    def test_explicit_id_bypasses_default_filter(self):
        """Querying by id must bypass the default filter."""
        body = {
            'object_type': 'event',
            'query': {'field': 'id', 'op': '=', 'value': self.test_event.graceid},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.test_event.graceid, ids)


class TestV2EventSearchOperators(EventCreateMixin, GraceDbApiTestBase):
    """
    Integration tests for operators not covered elsewhere:
    between, is_null, in, and the error response path format.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()
        cls.list_url = _list_url()

        cls.event_low_far = cls.create_event('CBC', 'gstlal', user=cls.internal_user)
        cls.event_low_far.far = 1e-12
        cls.event_low_far.gpstime = 1000.0
        cls.event_low_far.save()

        cls.event_high_far = cls.create_event('CBC', 'pycbc', user=cls.internal_user)
        cls.event_high_far.far = 1e-3
        cls.event_high_far.gpstime = 2000.0
        cls.event_high_far.save()

        cls.event_no_far = cls.create_event('CBC', 'mbta', user=cls.internal_user)
        cls.event_no_far.gpstime = 3000.0
        cls.event_no_far.save()

    def _ids(self, response):
        return {e['graceid'] for e in response.data['events']}

    def test_between_gpstime(self):
        """between operator on gpstime filters correctly."""
        body = {
            'object_type': 'event',
            'query': {'field': 'gpstime', 'op': 'between', 'value': [500.0, 1500.0]},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_low_far.graceid, ids)
        self.assertNotIn(self.event_high_far.graceid, ids)

    def test_is_null_far_true(self):
        """is_null=true on far returns only events with no FAR."""
        body = {
            'object_type': 'event',
            'query': {'field': 'far', 'op': 'is_null', 'value': True},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_no_far.graceid, ids)
        self.assertNotIn(self.event_low_far.graceid, ids)

    def test_is_null_far_false(self):
        """is_null=false on far returns only events that have a FAR."""
        body = {
            'object_type': 'event',
            'query': {'field': 'far', 'op': 'is_null', 'value': False},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_low_far.graceid, ids)
        self.assertIn(self.event_high_far.graceid, ids)
        self.assertNotIn(self.event_no_far.graceid, ids)

    def test_in_pipeline(self):
        """in operator on pipeline filters to the listed pipelines."""
        body = {
            'object_type': 'event',
            'query': {'field': 'pipeline', 'op': 'in',
                      'value': ['gstlal', 'pycbc']},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_low_far.graceid, ids)   # gstlal
        self.assertIn(self.event_high_far.graceid, ids)  # pycbc
        self.assertNotIn(self.event_no_far.graceid, ids) # mbta

    def test_error_path_is_string(self):
        """Error response 'path' field must be a formatted string, not a list."""
        body = {
            'object_type': 'event',
            'query': {
                'and': [
                    {'field': 'bad_field', 'op': '=', 'value': 'x'},
                ]
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 400)
        path_value = response.data.get('path')
        # path must be a string like "and[0]", not a list
        if path_value is not None:
            self.assertIsInstance(path_value, str,
                msg=f"'path' in error response should be a string, got {type(path_value)}")


class TestV2EventSearchLabels(EventCreateMixin, GraceDbApiTestBase):
    """
    Integration tests for label has/not_has operators.

    These exercise the Exists-subquery code path in the translator, which is
    completely separate from the simple Q-object path used for scalar fields.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

        cls.lbl_a = Label.objects.create(name='INT_LBL_A', description='test A')
        cls.lbl_b = Label.objects.create(name='INT_LBL_B', description='test B')

        # event_a: only label A; event_b: only label B;
        # event_ab: both; event_none: neither
        cls.event_a    = cls.create_event('CBC', 'gstlal', user=cls.internal_user)
        cls.event_b    = cls.create_event('CBC', 'gstlal', user=cls.internal_user)
        cls.event_ab   = cls.create_event('CBC', 'gstlal', user=cls.internal_user)
        cls.event_none = cls.create_event('CBC', 'gstlal', user=cls.internal_user)

        u = cls.internal_user
        Labelling.objects.create(event=cls.event_a,  label=cls.lbl_a, creator=u)
        Labelling.objects.create(event=cls.event_b,  label=cls.lbl_b, creator=u)
        Labelling.objects.create(event=cls.event_ab, label=cls.lbl_a, creator=u)
        Labelling.objects.create(event=cls.event_ab, label=cls.lbl_b, creator=u)

    def _ids(self, response):
        return {e['graceid'] for e in response.data['events']}

    def test_label_has(self):
        """has INT_LBL_A returns events that carry that label."""
        body = {
            'object_type': 'event',
            'query': {'field': 'label', 'op': 'has', 'value': 'INT_LBL_A'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_a.graceid, ids)
        self.assertIn(self.event_ab.graceid, ids)
        self.assertNotIn(self.event_b.graceid, ids)
        self.assertNotIn(self.event_none.graceid, ids)

    def test_label_not_has(self):
        """not_has INT_LBL_A returns events that do NOT carry that label."""
        body = {
            'object_type': 'event',
            'query': {'field': 'label', 'op': 'not_has', 'value': 'INT_LBL_A'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.event_a.graceid, ids)
        self.assertNotIn(self.event_ab.graceid, ids)
        self.assertIn(self.event_b.graceid, ids)
        self.assertIn(self.event_none.graceid, ids)

    def test_and_of_two_labels(self):
        """AND(has A, has B) returns only events that carry both labels."""
        body = {
            'object_type': 'event',
            'query': {
                'and': [
                    {'field': 'label', 'op': 'has', 'value': 'INT_LBL_A'},
                    {'field': 'label', 'op': 'has', 'value': 'INT_LBL_B'},
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_ab.graceid, ids)
        self.assertNotIn(self.event_a.graceid, ids)
        self.assertNotIn(self.event_b.graceid, ids)
        self.assertNotIn(self.event_none.graceid, ids)

    def test_or_of_two_labels(self):
        """OR(has A, has B) returns events that carry either label."""
        body = {
            'object_type': 'event',
            'query': {
                'or': [
                    {'field': 'label', 'op': 'has', 'value': 'INT_LBL_A'},
                    {'field': 'label', 'op': 'has', 'value': 'INT_LBL_B'},
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_a.graceid, ids)
        self.assertIn(self.event_b.graceid, ids)
        self.assertIn(self.event_ab.graceid, ids)
        self.assertNotIn(self.event_none.graceid, ids)

    def test_not_wrapping_has(self):
        """NOT(has A) is semantically equivalent to not_has A."""
        body = {
            'object_type': 'event',
            'query': {'not': {'field': 'label', 'op': 'has', 'value': 'INT_LBL_A'}},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.event_a.graceid, ids)
        self.assertNotIn(self.event_ab.graceid, ids)
        self.assertIn(self.event_b.graceid, ids)
        self.assertIn(self.event_none.graceid, ids)


class TestV2EventSearchStringOps(EventCreateMixin, GraceDbApiTestBase):
    """
    Integration tests for string operators: startswith, !=, contains,
    and the instruments iexact case-insensitive match (Bug 2 regression).
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

        cls.event_gs = cls.create_event('CBC', 'gstlal', user=cls.internal_user)
        cls.event_py = cls.create_event('CBC', 'pycbc',  user=cls.internal_user)

        # Set instruments on the gstlal event for the iexact test.
        cls.event_gs.instruments = 'H1,L1'
        cls.event_gs.save()

    def _ids(self, response):
        return {e['graceid'] for e in response.data['events']}

    def test_neq_pipeline(self):
        """pipeline != gstlal excludes the gstlal event."""
        body = {
            'object_type': 'event',
            'query': {'field': 'pipeline', 'op': '!=', 'value': 'gstlal'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.event_gs.graceid, ids)
        self.assertIn(self.event_py.graceid, ids)

    def test_startswith_graceid(self):
        """id startswith 'G' matches both CBC events (graceids begin with 'G')."""
        # All non-special events get 'G'-prefixed graceids.
        body = {
            'object_type': 'event',
            'query': {'field': 'id', 'op': 'startswith',
                      'value': self.event_gs.graceid[:1]},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_gs.graceid, ids)
        self.assertIn(self.event_py.graceid, ids)

    def test_in_graceid(self):
        """id in [G1] returns exactly the listed event."""
        body = {
            'object_type': 'event',
            'query': {'field': 'id', 'op': 'in',
                      'value': [self.event_gs.graceid]},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_gs.graceid, ids)
        self.assertNotIn(self.event_py.graceid, ids)

    def test_instruments_eq_case_insensitive(self):
        """
        instruments = 'h1,l1' (lowercase) must match 'H1,L1' stored in the DB
        (Bug 2 regression: instruments = must use iexact, not exact).
        """
        body = {
            'object_type': 'event',
            'query': {'field': 'instruments', 'op': '=', 'value': 'h1,l1'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_gs.graceid, ids)
        self.assertNotIn(self.event_py.graceid, ids)

    def test_contains_pipeline(self):
        """pipeline contains 'stlal' matches the gstlal event."""
        body = {
            'object_type': 'event',
            'query': {'field': 'pipeline', 'op': 'contains', 'value': 'stlal'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.event_gs.graceid, ids)
        self.assertNotIn(self.event_py.graceid, ids)


class TestV2EventSearchEmptyBody(EventCreateMixin, GraceDbApiTestBase):
    """POST /search/ with no body (or empty body) returns the full accessible set."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()
        cls.event = cls.create_event('CBC', 'gstlal', user=cls.internal_user)

    def test_post_empty_body_returns_accessible_set(self):
        """POST to /search/ with no body returns all accessible events."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data='',
            content_type='application/json',
        )
        self.client.logout()
        self.assertEqual(response.status_code, 200)
        ids = {e['graceid'] for e in response.data['events']}
        self.assertIn(self.event.graceid, ids)

    def test_post_no_content_type_returns_accessible_set(self):
        """POST to /search/ with no content-type and no body also returns all events."""
        self.client.force_login(self.internal_user)
        response = self.client.post(self.search_url)
        self.client.logout()
        self.assertEqual(response.status_code, 200)
        ids = {e['graceid'] for e in response.data['events']}
        self.assertIn(self.event.graceid, ids)


class TestV2EventSearchBug1Regression(EventCreateMixin, GraceDbApiTestBase):
    """
    Regression tests for Bug 1: is_null with a null or non-boolean value must
    be rejected with a 400, not silently pass validation.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

    def _assert_invalid_query(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('error'), 'invalid_query')

    def test_is_null_with_string_value_rejected(self):
        """is_null with a string value must return 400 (requires boolean)."""
        body = {
            'object_type': 'event',
            'query': {'field': 'far', 'op': 'is_null', 'value': 'yes'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)

    def test_is_null_with_numeric_value_rejected(self):
        """is_null with a numeric value must return 400."""
        body = {
            'object_type': 'event',
            'query': {'field': 'far', 'op': 'is_null', 'value': 1},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)

    def test_is_null_true_accepted(self):
        """is_null with value=true must be accepted (200)."""
        body = {
            'object_type': 'event',
            'query': {'field': 'far', 'op': 'is_null', 'value': True},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)

    def test_is_null_false_accepted(self):
        """is_null with value=false must be accepted (200)."""
        body = {
            'object_type': 'event',
            'query': {'field': 'far', 'op': 'is_null', 'value': False},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
