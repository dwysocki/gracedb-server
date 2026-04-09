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
from events.models import Event
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
