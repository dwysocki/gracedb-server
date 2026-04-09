"""
Integration tests for the v2 superevent search API.

Two search paths are tested:
  1. GET /api/v2/superevents/?query=<json>  — URL-parameter-based search
  2. POST /api/v2/superevents/search/       — body-based search (JSON or YAML)
"""
import json
import os

import pytest
from django.urls import reverse

from api.tests.utils import GraceDbApiTestBase
from core.tests.utils import GraceDbTestBase
from superevents.models import Superevent
from superevents.tests.mixins import SupereventCreateMixin, SupereventSetup
from superevents.utils import expose_superevent
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    """Versioned reverse for v2 API."""
    viewname = f'api:{API_VERSION}:' + viewname
    return reverse(viewname, *args, **kwargs)


def _list_url():
    return v_reverse('superevents:superevent-list')


def _search_url():
    return v_reverse('superevents:superevent-search')


def _get_query_param(client, user, query_dict):
    """GET /superevents/?query=<json> as an authenticated user."""
    client.force_login(user)
    response = client.get(
        _list_url(),
        {'query': json.dumps(query_dict)},
    )
    client.logout()
    return response


def _post_json(client, user, body):
    """POST /superevents/search/ with JSON body."""
    client.force_login(user)
    response = client.post(
        _search_url(),
        data=json.dumps(body),
        content_type='application/json',
    )
    client.logout()
    return response


def _post_yaml(client, user, yaml_body):
    """POST /superevents/search/ with YAML body."""
    client.force_login(user)
    response = client.post(
        _search_url(),
        data=yaml_body,
        content_type='application/yaml',
    )
    client.logout()
    return response


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------

class TestV2SupereventSearchBasic(SupereventSetup, GraceDbApiTestBase):
    """
    Basic query correctness tests.

    SupereventSetup creates three superevents:
      internal_superevent   — no external permissions
      lvem_superevent       — LV-EM permissions
      public_superevent     — public permissions
    All three are Production category with t_0=1.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.list_url = _list_url()
        cls.search_url = _search_url()

    # ------------------------------------------------------------------
    # No-query behaviour
    # ------------------------------------------------------------------

    def test_no_query_returns_all_accessible_superevents(self):
        """GET without a query returns all accessible superevents."""
        response = self.request_as_user(self.list_url, 'GET', self.internal_user)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 3)

    # ------------------------------------------------------------------
    # GET with ?query= URL parameter
    # ------------------------------------------------------------------

    def test_get_query_param_category_production(self):
        """?query=<json> on GET filters correctly by category."""
        node = {'field': 'category', 'op': '=', 'value': 'Production'}
        response = _get_query_param(self.client, self.internal_user, node)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 3)

    def test_get_query_param_t0_range(self):
        """t_0 > 0.5 returns all three fixtures (all have t_0=1)."""
        node = {'field': 't_0', 'op': '>', 'value': 0.5}
        response = _get_query_param(self.client, self.internal_user, node)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 3)

    def test_get_query_param_t0_excludes_all(self):
        """t_0 > 1000 returns empty when all t_0=1."""
        node = {'field': 't_0', 'op': '>', 'value': 1000.0}
        response = _get_query_param(self.client, self.internal_user, node)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 0)

    def test_get_query_param_empty_and_returns_all(self):
        """Empty AND combinator is an identity filter."""
        response = _get_query_param(self.client, self.internal_user, {'field': 't_0', 'op': '>', 'value': -1})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 3)

    # ------------------------------------------------------------------
    # POST /search/ with JSON body
    # ------------------------------------------------------------------

    def test_post_search_empty_and_returns_all(self):
        """POST search with empty AND returns all accessible superevents."""
        body = {'object_type': 'superevent', 'query': {'field': 't_0', 'op': '>', 'value': -1}}
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 3)

    def test_post_search_category_production(self):
        """POST search by category=Production returns all three fixtures."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'category', 'op': '=', 'value': 'Production'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 3)

    def test_post_search_category_test_returns_empty(self):
        """POST search for Test superevents returns empty when none exist."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'category', 'op': '=', 'value': 'Test'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 0)

    def test_post_search_t0_excludes_all(self):
        """POST search t_0 > 1000 returns nothing."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 't_0', 'op': '>', 'value': 1000.0},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 0)

    # ------------------------------------------------------------------
    # YAML body
    # ------------------------------------------------------------------

    def test_yaml_body_accepted(self):
        """A YAML query body is accepted and produces correct results."""
        yaml_body = (
            'object_type: superevent\n'
            'query:\n'
            '  field: category\n'
            '  op: "="\n'
            '  value: Production\n'
        )
        response = _post_yaml(self.client, self.internal_user, yaml_body)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['superevents']), 3)

    # ------------------------------------------------------------------
    # Permission filtering
    # ------------------------------------------------------------------

    def test_permission_filter_lvem_user(self):
        """LV-EM user only sees permitted superevents via POST search."""
        body = {'object_type': 'superevent', 'query': {'field': 't_0', 'op': '>', 'value': -1}}
        response = _post_json(self.client, self.lvem_user, body)
        self.assertEqual(response.status_code, 200)
        ids = {s['superevent_id'] for s in response.data['superevents']}
        self.assertIn(self.lvem_superevent.superevent_id, ids)
        self.assertIn(self.public_superevent.superevent_id, ids)
        self.assertNotIn(self.internal_superevent.superevent_id, ids)

    def test_permission_filter_via_get_query_param(self):
        """LV-EM user only sees permitted superevents via GET query param."""
        node = {'field': 't_0', 'op': '>', 'value': -1}
        response = _get_query_param(self.client, self.lvem_user, node)
        self.assertEqual(response.status_code, 200)
        ids = {s['superevent_id'] for s in response.data['superevents']}
        self.assertIn(self.lvem_superevent.superevent_id, ids)
        self.assertNotIn(self.internal_superevent.superevent_id, ids)

    def test_unauthenticated_search_rejected(self):
        """Anonymous POST to /search/ is rejected (401 or 403)."""
        body = {'object_type': 'superevent', 'query': {'field': 't_0', 'op': '>', 'value': -1}}
        response = self.client.post(
            self.search_url,
            data=json.dumps(body),
            content_type='application/json',
        )
        self.assertIn(response.status_code, (401, 403))


class TestV2SupereventSearchErrors(SupereventSetup, GraceDbApiTestBase):
    """Error handling: 400 responses for bad queries."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()
        cls.list_url = _list_url()

    def _assert_invalid_query(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('error'), 'invalid_query')
        self.assertEqual(response.data.get('version'), '2')

    def test_invalid_json_body_returns_400(self):
        """Malformed JSON body → 400 with structured error."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data='this is not json {{{',
            content_type='application/json',
        )
        self.client.logout()
        self._assert_invalid_query(response)

    def test_invalid_yaml_body_returns_400(self):
        """Malformed YAML body → 400."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data=': invalid: yaml: [unclosed',
            content_type='application/yaml',
        )
        self.client.logout()
        self._assert_invalid_query(response)

    def test_unknown_field_returns_400(self):
        """Unknown field name → 400 with path info."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'no_such_field', 'op': '=', 'value': 'x'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)
        self.assertIsNotNone(response.data.get('message'))

    def test_unknown_field_via_get_param_returns_400(self):
        """Unknown field in GET ?query= also returns 400."""
        node = {'field': 'no_such_field', 'op': '=', 'value': 'x'}
        response = _get_query_param(self.client, self.internal_user, node)
        self._assert_invalid_query(response)

    def test_wrong_object_type_returns_400(self):
        """object_type='event' sent to superevent endpoint → 400."""
        body = {
            'object_type': 'event',
            'query': {'field': 'group', 'op': '=', 'value': 'CBC'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)
        self.assertIn('superevent', response.data['message'])

    def test_bad_operator_returns_400(self):
        """Operator not valid for the field type → 400."""
        body = {
            'object_type': 'superevent',
            'query': {
                'field': 'category',
                'op': 'startswith',  # not valid for enum
                'value': 'Production',
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)

    def test_body_not_dict_returns_400(self):
        """JSON array body → 400."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data=json.dumps([1, 2, 3]),
            content_type='application/json',
        )
        self.client.logout()
        self._assert_invalid_query(response)

    def test_invalid_json_in_get_param_returns_400(self):
        """Malformed JSON in ?query= → 400."""
        self.client.force_login(self.internal_user)
        response = self.client.get(self.list_url, {'query': 'not-json'})
        self.client.logout()
        self._assert_invalid_query(response)


class TestV2SupereventSearchComplex(SupereventCreateMixin, GraceDbApiTestBase):
    """
    Combinator (AND, OR, NOT) tests with distinct Production and Test
    superevents.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

        cls.se_prod = cls.create_superevent(
            cls.internal_user,
            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
        )
        cls.se_prod.t_0 = 100.0
        cls.se_prod.save(update_fields=['t_0'])

        cls.se_test = cls.create_superevent(
            cls.internal_user,
            category=Superevent.SUPEREVENT_CATEGORY_TEST,
        )
        cls.se_test.t_0 = 200.0
        cls.se_test.save(update_fields=['t_0'])

    def _ids(self, response):
        return {s['superevent_id'] for s in response.data['superevents']}

    def test_and_combinator(self):
        """AND(category=Production, t_0>50) returns only the production SE."""
        body = {
            'object_type': 'superevent',
            'query': {
                'and': [
                    {'field': 'category', 'op': '=', 'value': 'Production'},
                    {'field': 't_0', 'op': '>', 'value': 50.0},
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_prod.superevent_id, ids)
        self.assertNotIn(self.se_test.superevent_id, ids)

    def test_or_combinator(self):
        """OR(category=Production, category=Test) returns both SEs."""
        body = {
            'object_type': 'superevent',
            'query': {
                'or': [
                    {'field': 'category', 'op': '=', 'value': 'Production'},
                    {'field': 'category', 'op': '=', 'value': 'Test'},
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_prod.superevent_id, ids)
        self.assertIn(self.se_test.superevent_id, ids)

    def test_not_combinator(self):
        """NOT category=Test returns only the production SE."""
        body = {
            'object_type': 'superevent',
            'query': {
                'not': {'field': 'category', 'op': '=', 'value': 'Test'},
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_prod.superevent_id, ids)
        self.assertNotIn(self.se_test.superevent_id, ids)

    def test_nested_and_or(self):
        """AND(category=Production, OR(t_0>50, t_0<0)) — only prod qualifies."""
        body = {
            'object_type': 'superevent',
            'query': {
                'and': [
                    {'field': 'category', 'op': '=', 'value': 'Production'},
                    {
                        'or': [
                            {'field': 't_0', 'op': '>', 'value': 50.0},
                            {'field': 't_0', 'op': '<', 'value': 0.0},
                        ]
                    },
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_prod.superevent_id, ids)
        self.assertNotIn(self.se_test.superevent_id, ids)
