from __future__ import absolute_import

from django.conf import settings
from django.urls import reverse

from api.tests.utils import GraceDbApiTestBase
from events.tests.mixins import EventSetup
from ...settings import API_VERSION


def v_reverse(viewname, *args, **kwargs):
    """Easily customizable versioned API reverse for testing"""
    viewname = 'api:{version}:'.format(version=API_VERSION) + viewname
    return reverse(viewname, *args, **kwargs)


class TestPublicAccess(EventSetup, GraceDbApiTestBase):

    def test_event_list(self):
        """Unauthenticated user can't access event list"""
        url = v_reverse('events:event-list')
        methods = ["GET", "POST"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_detail(self):
        """Unauthenticated user can't access event detail"""
        url = v_reverse('events:event-detail', args=['G123456'])
        methods = ["GET", "PUT"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_log_list(self):
        """Unauthenticated user can't access event log list"""
        url = v_reverse('events:eventlog-list', args=['G123456'])
        methods = ["GET", "POST"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_log_detail(self):
        """Unauthenticated user can't access event log detail"""
        url = v_reverse('events:eventlog-detail', args=['G123456', 1])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_voevent_list(self):
        """Unauthenticated user can't access event VOEvent list"""
        url = v_reverse('events:voevent-list', args=['G123456'])
        methods = ["GET", "POST"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_voevent_detail(self):
        """Unauthenticated user can't access event VOEvent detail"""
        url = v_reverse('events:voevent-detail', args=['G123456', 1])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_embbeventlog_list(self):
        """Unauthenticated user can't access event EMBBEventLog list"""
        url = v_reverse('events:embbeventlog-list', args=['G123456'])
        methods = ["GET", "POST"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_embbeventlog_detail(self):
        """Unauthenticated user can't access event EMBBEventLog detail"""
        url = v_reverse('events:embbeventlog-detail', args=['G123456', 1])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_emobservation_list(self):
        """Unauthenticated user can't access event EMObservation list"""
        url = v_reverse('events:emobservation-list', args=['G123456'])
        methods = ["GET", "POST"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_emobservation_detail(self):
        """Unauthenticated user can't access event EMObservation detail"""
        url = v_reverse('events:emobservation-detail', args=['G123456', 1])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_tag_list(self):
        """Unauthenticated user can't access event tag list"""
        url = v_reverse('events:eventtag-list', args=['G123456'])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_tag_detail(self):
        """Unauthenticated user can't access event tag detail"""
        url = v_reverse('events:eventtag-detail', args=['G123456', 'tagname'])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_log_tag_list(self):
        """Unauthenticated user can't access event log tag list"""
        url = v_reverse('events:eventlogtag-list', args=['G123456', 1])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_log_tag_detail(self):
        """Unauthenticated user can't access event log tag detail"""
        url = v_reverse('events:eventlogtag-detail', args=['G123456',
            1, 'tagname'])
        methods = ["GET", "PUT", "DELETE"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_permission_list(self):
        """Unauthenticated user can't access event permission list"""
        url = v_reverse('events:eventpermission-list', args=['G123456'])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_group_permission_list(self):
        """Unauthenticated user can't access event group permission list"""
        url = v_reverse('events:groupeventpermission-list', args=['G123456',
            'group_name'])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_group_permission_detail(self):
        """Unauthenticated user can't access event group permission list"""
        url = v_reverse('events:groupeventpermission-detail', args=['G123456',
            'group_name', 'perm_name'])
        methods = ["GET", "PUT", "DELETE"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_files(self):
        """Unauthenticated user can't access event files (list or detail)"""
        url = v_reverse('events:files', args=['G123456', 'file_name'])
        methods = ["GET", "PUT"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_labels(self):
        """Unauthenticated user can't access event labels (list or detail)"""
        url = v_reverse('events:labels', args=['G123456', 'label_name'])
        methods = ["GET", "PUT", "DELETE"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_neighbors(self):
        """Unauthenticated user can't access event neighbors list"""
        url = v_reverse('events:labels', args=['G123456'])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )

    def test_event_signoff_list(self):
        """Unauthenticated user can't access event signoff list"""
        url = v_reverse('events:labels', args=['G123456'])
        methods = ["GET"]
        for http_method in methods:
            response = self.request_as_user(url, http_method)
            self.assertContains(
                response,
                'Authentication credentials were not provided',
                status_code=403
            )
