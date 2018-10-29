from django.urls import reverse as django_reverse

from rest_framework.test import APIRequestFactory, APISimpleTestCase

from api.utils import api_reverse


class TestApiReverse(APISimpleTestCase):
    """Test behavior of custom api_reverse function"""

    @classmethod
    def setUpClass(cls):
        super(TestApiReverse, cls).setUpClass()
        cls.api_version = 'v1'
        cls.api_url = django_reverse('api:{version}:root'.format(
            version=cls.api_version))
        cls.non_api_url = django_reverse('home')

    def setUp(self):
        super(TestApiReverse, self).setUp()
        self.factory = APIRequestFactory()

        # Create requests
        self.api_request = self.factory.get(self.api_url)
        self.non_api_request = self.factory.get(self.non_api_url)

        # Simulate version checking that is done in an API view's
        # initial() method
        self.api_request.version = self.api_version

    def test_full_viewname_with_request_to_api(self):
        """
        Reverse a fully namespaced viewname, including a request to the API
        """
        url = api_reverse('api:v1:root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_full_viewname_with_request_to_api_different_version(self):
        """
        Reverse a fully namespaced viewname with a different version than
        the corresponding request to the API
        """
        url = api_reverse('api:v2:root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v2:root'))

    def test_full_viewname_with_request_to_non_api(self):
        """
        Reverse a fully namespaced viewname, including a request to a non-API
        page
        """
        url = api_reverse('api:v1:root', request=self.non_api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_full_viewname_with_no_request(self):
        """
        Reverse a fully namespaced viewname, with no associated request
        """
        url = api_reverse('api:v1:root', absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_versioned_viewname_with_request_to_api(self):
        """
        Reverse a versioned viewname, including a request to the API
        """
        url = api_reverse('v1:root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_versioned_viewname_with_request_to_api_different_version(self):
        """
        Reverse a versioned viewname with a different version than
        the corresponding request to the API
        """
        url = api_reverse('v2:root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v2:root'))

    def test_versioned_viewname_with_request_to_non_api(self):
        """
        Reverse a versioned viewname, including a request to a non-API page
        """
        url = api_reverse('v1:root', request=self.non_api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_versioned_viewname_with_no_request(self):
        """
        Reverse a versioned viewname, with no associated request
        """
        url = api_reverse('v1:root', absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_api_unversioned_viewname_with_request_to_api(self):
        """
        Reverse an api-namespaced but unversioned viewname, including a request
        to the API
        """
        url = api_reverse('api:root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_api_unversioned_viewname_with_request_to_non_api(self):
        """
        Reverse an api-namespaced but unversioned viewname, including a request
        to a non-API page
        """
        url = api_reverse('api:root', request=self.non_api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:default:root'))

    def test_api_unversioned_viewname_with_no_request(self):
        """
        Reverse an api-namespaced bu unversioned viewname, with no associated
        request
        """
        url = api_reverse('api:root', absolute_path=False)
        self.assertEqual(url, django_reverse('api:default:root'))

    def test_relative_viewname_with_request_to_api(self):
        url = api_reverse('root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_relative_viewname_with_request_to_non_api(self):
        url = api_reverse('root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_relative_viewname_with_no_request(self):
        url = api_reverse('root', request=self.api_request,
            absolute_path=False)
        self.assertEqual(url, django_reverse('api:v1:root'))

    def test_reverse_non_api_url(self):
        pass
