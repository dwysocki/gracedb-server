from __future__ import absolute_import
import datetime
import ipdb
import json
import pytest

from django.conf import settings
from django.urls import reverse
from django.core.cache import cache

from guardian.shortcuts import assign_perm, remove_perm

from api.tests.utils import GraceDbApiTestBase
from core.tests.utils import GraceDbTestBase, \
    catalog_managers_group_and_user_setup
from gwtc.tests.mixins import gwtc_create_mixin
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    """Easily customizable versioned API reverse for testing"""
    viewname = 'api:{version}:'.format(version=API_VERSION) + viewname
    return reverse(viewname, *args, **kwargs)

class test_gwtc_list(GraceDbApiTestBase, gwtc_create_mixin,
    catalog_managers_group_and_user_setup):

    @classmethod
    def setUpClass(cls):
        super(test_gwtc_list, cls).setUpClass()
        cls.url = v_reverse('gwtc:gwtc-list')

    @classmethod
    def setUpTestData(cls):
        super(test_gwtc_list, cls).setUpTestData()

        # an initial catalog object:
        cls.gwtc_test_1 = cls.create_gwtc_catalog(user=cls.internal_user,
                              gwtc_number='test1')

        # a template json string for POST operations:
        cls.json_upload = '{{ "{superevent_id}":{{"{pipeline}":"{graceid}"}} }}'

        # two test superevents:
        cls.test_superevent1 = cls.create_superevent(cls.internal_user)
        cls.test_superevent2 = cls.create_superevent(cls.internal_user)

        # a test coincinspiralevent:
        cls.test_coinc = cls.create_coinc_event('CBC', 'gstlal')

        # smap jsons based on those two test superevents:
        cls.smap_superevent1 = cls.json_upload.format(superevent_id = cls.test_superevent1.superevent_id,
                                              pipeline = cls.test_superevent1.preferred_event.pipeline.name,
                                              graceid = cls.test_superevent1.preferred_event.graceid)
         
        cls.smap_superevent2 = cls.json_upload.format(superevent_id = cls.test_superevent2.superevent_id,
                                              pipeline = cls.test_superevent2.preferred_event.pipeline.name,
                                              graceid = cls.test_superevent2.preferred_event.graceid)

        # json with an invalid superevent ID (date not in range):
        cls.smap_bad_sid = cls.json_upload.format(superevent_id = "S123456ab",
                                              pipeline = cls.test_superevent1.preferred_event.pipeline.name,
                                              graceid = cls.test_superevent1.preferred_event.graceid)

        # json with valid superevent id, but it isn't in the database:
        cls.smap_no_sevent = cls.json_upload.format(superevent_id = "S231129ab",
                                              pipeline = cls.test_superevent1.preferred_event.pipeline.name,
                                              graceid = cls.test_superevent1.preferred_event.graceid)

        # json with graceid not in the database:
        cls.smap_no_gevent = cls.json_upload.format(superevent_id = cls.test_superevent2.superevent_id,
                                              pipeline = cls.test_superevent2.preferred_event.pipeline.name,
                                              graceid = "G12345")

        # json with invalid pipeline name in the upload:
        cls.smap_bad_pipeline = cls.json_upload.format(superevent_id = cls.test_superevent2.superevent_id,
                                              pipeline = "gstlol",
                                              graceid = cls.test_superevent2.preferred_event.graceid)

        # json with a valid coinc graceid, but it's not part of the associated superevent:
        cls.smap_coinc_gevent = cls.json_upload.format(superevent_id = cls.test_superevent2.superevent_id,
                                              pipeline = cls.test_superevent2.preferred_event.pipeline.name,
                                              graceid = cls.test_coinc.graceid)


    def test_internal_user_get_gwtc_list(self):
        """Internal user sees catalog entries"""
        response = self.request_as_user(self.url, "GET", self.internal_user)
        
        # confirm the user can access the catalogs
        self.assertEqual(response.status_code, 200)

        # confirm there is only one catalog entry:
        data = response.data['results']
        self.assertEqual(len(data), 1)

        # confirm the number is correct:
        data = data[0]
        gwtc_name = data['number']
        self.assertEqual(gwtc_name, 'test1')

        # confirm that the version is 1:
        gwtc_version = int(data['version'])
        self.assertEqual(gwtc_version, 1)


    def test_public_gwtc_access(self):
        """At this time, the public cannot see gwtc objects"""
        response = self.request_as_user(self.url, "GET")

        # confirm the public cannot see gwtc objects
        self.assertEqual(response.status_code, 403)


    def test_internal_user_not_create_gwtc(self):
        """Authenticated users not in catalog_managers cannot create gwtc's"""
        request_data = {"number": "test1", "smap": self.smap_superevent1}
        response = self.request_as_user(self.url, "POST", self.internal_user,
            data=request_data)

        # confirm the status code is correct:
        self.assertEqual(response.status_code, 403)


    def test_cm_user_create_gwtc(self):
        """Verify a catalog manager can create new gwtc objects"""

        request_data = {"number": "test1", "smap": self.smap_superevent1}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)

        # confirm the status code is correct:
        self.assertEqual(response.status_code, 201)

        # get the new list and confirm version numbers, etc:
        response = self.request_as_user(self.url, "GET", self.cm_user)

        # confirm there are two catalog entries:
        data = response.data['results']
        self.assertEqual(len(data), 2)


    def test_queries_and_paths(self):
        """Make another catalog with a different number, and then verify
           that the API query paths work."""

        # create a second number='test1' gwtc. this should be version 2:
        request_data = {"number": "test1", "smap": self.smap_superevent1}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)
        self.assertEqual(response.status_code, 201)

        # create a number='test2' gwtc:
        request_data = {"number": "test2", "smap": self.smap_superevent2}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)
        self.assertEqual(response.status_code, 201)

        # get all the gwtc's and confirm there are three:
        response = self.request_as_user(self.url, "GET", self.internal_user)
        data = response.data['results']
        self.assertEqual(len(data), 3)

        # get all 'test1' gwtc's and count there are two:
        response = self.request_as_user(self.url+'test1/',
            "GET", self.internal_user)
        data = response.data['results']
        self.assertEqual(len(data), 2)

        # get the 'latest' test1 gtwc, verify that it's version=2
        response = self.request_as_user(self.url+'test1/latest/',
            "GET", self.internal_user)
        gwtc_version = int(response.data['version'])
        self.assertEqual(gwtc_version, 2)
        


    def test_get_wrong_number(self):
        """Querying for the wrong number gives no results"""

        response = self.request_as_user(self.url+'test123/', 
            "GET", self.internal_user)

        # confirm the status code is 200:
        self.assertEqual(response.status_code, 200) 

        # confirm there are no catalog entries:
        data = response.data['results']
        self.assertEqual(len(data), 0)


    def test_create_bad_superevent_id(self):
        """User attempts to upload smap with invalid superevent_id"""

        request_data = {"number": "test1", "smap": self.smap_bad_sid}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)

        # confirm the status code is correct:
        self.assertEqual(response.status_code, 400)


    def test_create_no_superevent(self):
        """User attempts to upload smap with a superevent_id not in the db"""

        request_data = {"number": "test1", "smap": self.smap_no_gevent}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)

        # confirm the status code is correct:
        self.assertEqual(response.status_code, 400)


    def test_create_no_gevent(self):
        """User attempts to upload smap with a graceid not in the db"""

        request_data = {"number": "test1", "smap": self.smap_no_gevent}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)

        # confirm the status code is correct:
        self.assertEqual(response.status_code, 400)


    def test_create_pipeline_mismatch(self):
        """User attempts to upload smap with a mismatch between pipeline
           and the g-event"""

        request_data = {"number": "test1", "smap": self.smap_bad_pipeline}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)

        # confirm the status code is correct:
        self.assertEqual(response.status_code, 400)


    def test_coinc_not_in_superevent(self):
        """ User attempts to upload smap with valid graceic, but not part
            of the specified superevent """

        request_data = {"number": "test1", "smap": self.smap_coinc_gevent}
        response = self.request_as_user(self.url, "POST", self.cm_user,
            data=request_data)

        # confirm the status code is correct:
        self.assertEqual(response.status_code, 400)
