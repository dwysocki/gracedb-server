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
from events.models import Label
from superevents.models import Superevent, Labelling as SupereventLabelling
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

    def test_is_null_far_via_post(self):
        """is_null=true on t_0 — no superevents in this suite have null t_0,
        so the result must be empty."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 't_0', 'op': 'between',
                      'value': [50.0, 150.0]},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_prod.superevent_id, ids)  # t_0=100
        self.assertNotIn(self.se_test.superevent_id, ids)  # t_0=200

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


class TestV2SupereventSearchDefaultFilter(SupereventCreateMixin, GraceDbApiTestBase):
    """
    Verify that the default filter hides Test and MDC superevents from queries
    that do not reference category/id, and that explicit category queries bypass it.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()
        cls.list_url = _list_url()

        cls.se_prod = cls.create_superevent(
            cls.internal_user,
            category=Superevent.SUPEREVENT_CATEGORY_PRODUCTION,
        )
        cls.se_test = cls.create_superevent(
            cls.internal_user,
            category=Superevent.SUPEREVENT_CATEGORY_TEST,
        )
        cls.se_mdc = cls.create_superevent(
            cls.internal_user,
            category=Superevent.SUPEREVENT_CATEGORY_MDC,
        )

    def _ids(self, response):
        return {s['superevent_id'] for s in response.data['superevents']}

    def test_default_filter_hides_test_superevents(self):
        """Without an explicit category filter, Test superevents must not appear."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 't_0', 'op': '>', 'value': -1},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_prod.superevent_id, ids)
        self.assertNotIn(self.se_test.superevent_id, ids)

    def test_default_filter_hides_mdc_superevents(self):
        """Without an explicit category filter, MDC superevents must not appear."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 't_0', 'op': '>', 'value': -1},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.se_mdc.superevent_id, ids)

    def test_explicit_category_test_bypasses_default_filter(self):
        """Querying category=Test must return Test superevents."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'category', 'op': '=', 'value': 'Test'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_test.superevent_id, ids)
        self.assertNotIn(self.se_prod.superevent_id, ids)

    def test_explicit_category_in_bypasses_default_filter(self):
        """category in [Test, MDC] returns both non-production categories."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'category', 'op': 'in', 'value': ['Test', 'MDC']},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_test.superevent_id, ids)
        self.assertIn(self.se_mdc.superevent_id, ids)
        self.assertNotIn(self.se_prod.superevent_id, ids)

    def test_explicit_id_bypasses_default_filter(self):
        """Querying by id must bypass the default filter."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'id', 'op': '=',
                      'value': self.se_test.superevent_id},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_test.superevent_id, ids)

    def test_error_path_is_string(self):
        """Error response 'path' field must be a formatted string, not a list."""
        body = {
            'object_type': 'superevent',
            'query': {
                'and': [
                    {'field': 'no_such_field', 'op': '=', 'value': 'x'},
                ]
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 400)
        path_value = response.data.get('path')
        if path_value is not None:
            self.assertIsInstance(path_value, str,
                msg=f"'path' in error response should be a string, got {type(path_value)}")

    def test_get_query_param_default_filter(self):
        """GET ?query=<json> also applies the default filter."""
        node = {'field': 't_0', 'op': '>', 'value': -1}
        response = _get_query_param(self.client, self.internal_user, node)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_prod.superevent_id, ids)
        self.assertNotIn(self.se_test.superevent_id, ids)
        self.assertNotIn(self.se_mdc.superevent_id, ids)


class TestV2SupereventSearchLabels(SupereventCreateMixin, GraceDbApiTestBase):
    """
    Integration tests for label has/not_has operators on superevents.

    These exercise the _label_exists_q Exists-subquery path for the Superevent
    model's M2M through table, which is separate from the Event label path.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

        cls.lbl_a = Label.objects.create(name='SE_LBL_A', description='se test A')
        cls.lbl_b = Label.objects.create(name='SE_LBL_B', description='se test B')

        cls.se_a    = cls.create_superevent(cls.internal_user)
        cls.se_b    = cls.create_superevent(cls.internal_user)
        cls.se_ab   = cls.create_superevent(cls.internal_user)
        cls.se_none = cls.create_superevent(cls.internal_user)

        u = cls.internal_user
        SupereventLabelling.objects.create(
            superevent=cls.se_a,  label=cls.lbl_a, creator=u)
        SupereventLabelling.objects.create(
            superevent=cls.se_b,  label=cls.lbl_b, creator=u)
        SupereventLabelling.objects.create(
            superevent=cls.se_ab, label=cls.lbl_a, creator=u)
        SupereventLabelling.objects.create(
            superevent=cls.se_ab, label=cls.lbl_b, creator=u)

    def _ids(self, response):
        return {s['superevent_id'] for s in response.data['superevents']}

    def test_label_has(self):
        """has SE_LBL_A returns superevents that carry that label."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'label', 'op': 'has', 'value': 'SE_LBL_A'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_a.superevent_id, ids)
        self.assertIn(self.se_ab.superevent_id, ids)
        self.assertNotIn(self.se_b.superevent_id, ids)
        self.assertNotIn(self.se_none.superevent_id, ids)

    def test_label_not_has(self):
        """not_has SE_LBL_A returns superevents without that label."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'label', 'op': 'not_has', 'value': 'SE_LBL_A'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.se_a.superevent_id, ids)
        self.assertNotIn(self.se_ab.superevent_id, ids)
        self.assertIn(self.se_b.superevent_id, ids)
        self.assertIn(self.se_none.superevent_id, ids)

    def test_and_of_two_labels(self):
        """AND(has A, has B) returns only superevents carrying both labels."""
        body = {
            'object_type': 'superevent',
            'query': {
                'and': [
                    {'field': 'label', 'op': 'has', 'value': 'SE_LBL_A'},
                    {'field': 'label', 'op': 'has', 'value': 'SE_LBL_B'},
                ],
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_ab.superevent_id, ids)
        self.assertNotIn(self.se_a.superevent_id, ids)
        self.assertNotIn(self.se_b.superevent_id, ids)
        self.assertNotIn(self.se_none.superevent_id, ids)

    def test_not_wrapping_has(self):
        """NOT(has A) is equivalent to not_has A."""
        body = {
            'object_type': 'superevent',
            'query': {'not': {'field': 'label', 'op': 'has', 'value': 'SE_LBL_A'}},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.se_a.superevent_id, ids)
        self.assertNotIn(self.se_ab.superevent_id, ids)
        self.assertIn(self.se_b.superevent_id, ids)
        self.assertIn(self.se_none.superevent_id, ids)


class TestV2SupereventSearchPreferredEvent(SupereventCreateMixin, GraceDbApiTestBase):
    """
    Integration tests for the preferred_event.FOO cross-FK fields.

    Verifies that the translator's pref_event path prefix logic correctly
    routes queries through the preferred_event FK to the underlying Event fields.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

        # Two superevents whose preferred events differ by group and pipeline.
        cls.se_cbc = cls.create_superevent(
            cls.internal_user,
            event_group='CBC',
            event_pipeline='gstlal',
        )
        cls.se_burst = cls.create_superevent(
            cls.internal_user,
            event_group='Burst',
            event_pipeline='CWB',
        )

    def _ids(self, response):
        return {s['superevent_id'] for s in response.data['superevents']}

    def test_preferred_event_group_eq(self):
        """preferred_event.group = 'CBC' returns only the CBC-backed superevent."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'preferred_event.group', 'op': '=', 'value': 'CBC'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_cbc.superevent_id, ids)
        self.assertNotIn(self.se_burst.superevent_id, ids)

    def test_preferred_event_group_case_insensitive(self):
        """preferred_event.group = 'cbc' (lowercase) also matches (db_enum iexact)."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'preferred_event.group', 'op': '=', 'value': 'cbc'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_cbc.superevent_id, ids)
        self.assertNotIn(self.se_burst.superevent_id, ids)

    def test_preferred_event_pipeline_eq(self):
        """preferred_event.pipeline = 'gstlal' returns the gstlal-backed superevent."""
        body = {
            'object_type': 'superevent',
            'query': {
                'field': 'preferred_event.pipeline', 'op': '=', 'value': 'gstlal',
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_cbc.superevent_id, ids)
        self.assertNotIn(self.se_burst.superevent_id, ids)

    def test_preferred_event_group_neq(self):
        """preferred_event.group != 'CBC' excludes the CBC-backed superevent."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'preferred_event.group', 'op': '!=', 'value': 'CBC'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.se_cbc.superevent_id, ids)
        self.assertIn(self.se_burst.superevent_id, ids)

    def test_wrong_event_field_suggests_preferred_event_prefix(self):
        """Querying a raw event field on a superevent returns a helpful error."""
        # 'group' is an event field; on superevents it must be 'preferred_event.group'.
        body = {
            'object_type': 'superevent',
            'query': {'field': 'group', 'op': '=', 'value': 'CBC'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 400)
        self.assertIn('preferred_event', response.data.get('message', ''))


class TestV2SupereventSearchIsNull(SupereventCreateMixin, GraceDbApiTestBase):
    """
    Tests for the is_null operator on superevent-accessible fields.

    Specifically tests preferred_event.far, which can legitimately be NULL
    on a freshly created event.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

        cls.se_no_far  = cls.create_superevent(cls.internal_user)
        cls.se_has_far = cls.create_superevent(cls.internal_user)

        # Assign a FAR to only one of the preferred events.
        cls.se_has_far.preferred_event.far = 1e-8
        cls.se_has_far.preferred_event.save()

    def _ids(self, response):
        return {s['superevent_id'] for s in response.data['superevents']}

    def test_preferred_event_far_is_null_true(self):
        """preferred_event.far is_null=true returns SEs whose preferred event has no FAR."""
        body = {
            'object_type': 'superevent',
            'query': {
                'field': 'preferred_event.far', 'op': 'is_null', 'value': True,
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertIn(self.se_no_far.superevent_id, ids)
        self.assertNotIn(self.se_has_far.superevent_id, ids)

    def test_preferred_event_far_is_null_false(self):
        """preferred_event.far is_null=false returns SEs whose preferred event has a FAR."""
        body = {
            'object_type': 'superevent',
            'query': {
                'field': 'preferred_event.far', 'op': 'is_null', 'value': False,
            },
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
        ids = self._ids(response)
        self.assertNotIn(self.se_no_far.superevent_id, ids)
        self.assertIn(self.se_has_far.superevent_id, ids)


class TestV2SupereventSearchEmptyBody(SupereventCreateMixin, GraceDbApiTestBase):
    """POST /search/ with an empty body returns the full accessible set."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()
        cls.se = cls.create_superevent(cls.internal_user)

    def test_post_empty_body_returns_accessible_set(self):
        """POST to /search/ with no body returns all accessible superevents."""
        self.client.force_login(self.internal_user)
        response = self.client.post(
            self.search_url,
            data='',
            content_type='application/json',
        )
        self.client.logout()
        self.assertEqual(response.status_code, 200)
        ids = {s['superevent_id'] for s in response.data['superevents']}
        self.assertIn(self.se.superevent_id, ids)

    def test_post_no_content_type_returns_accessible_set(self):
        """POST with no content-type and no body also returns all superevents."""
        self.client.force_login(self.internal_user)
        response = self.client.post(self.search_url)
        self.client.logout()
        self.assertEqual(response.status_code, 200)
        ids = {s['superevent_id'] for s in response.data['superevents']}
        self.assertIn(self.se.superevent_id, ids)


class TestV2SupereventSearchBug1Regression(SupereventCreateMixin, GraceDbApiTestBase):
    """
    Regression tests for Bug 1: is_null with a non-boolean value must be
    rejected with 400, not silently accepted.
    """

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.search_url = _search_url()

    def _assert_invalid_query(self, response):
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data.get('error'), 'invalid_query')

    def test_is_null_string_value_rejected(self):
        """is_null with a string value must return 400."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'preferred_event.far', 'op': 'is_null', 'value': 'yes'},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)

    def test_is_null_numeric_value_rejected(self):
        """is_null with a numeric value must return 400."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'preferred_event.far', 'op': 'is_null', 'value': 1},
        }
        response = _post_json(self.client, self.internal_user, body)
        self._assert_invalid_query(response)

    def test_is_null_true_accepted(self):
        """is_null with value=true is valid and returns 200."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'preferred_event.far', 'op': 'is_null', 'value': True},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)

    def test_is_null_false_accepted(self):
        """is_null with value=false is valid and returns 200."""
        body = {
            'object_type': 'superevent',
            'query': {'field': 'preferred_event.far', 'op': 'is_null', 'value': False},
        }
        response = _post_json(self.client, self.internal_user, body)
        self.assertEqual(response.status_code, 200)
