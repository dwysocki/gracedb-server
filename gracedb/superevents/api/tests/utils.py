from rest_framework.test import APIClient

from core.tests.utils import GraceDbTestBase


class GraceDbApiTestBase(GraceDbTestBase):
    client_class = APIClient

    def request_as_user(self, url, method, user=None, data=None):
        """Shortcut function for making a request to the API"""
        # Get client method for HTTP method requested
        try:
            method_func = getattr(self.client, method.lower())
        except Exception as e:
            raise ValueError('{method} is not a valid HTTP method'.format(
                method=method))

        if user is not None:
            # Set up user dict
            user_dict = {
                'HTTP_REMOTE_USER': user.username,
                'HTTP_ISMEMBEROF': ';'.join([g.name for g in user.groups.all()]),
            }

            # Make request and return response
            return method_func(url, data, **user_dict)
        else:
            # Anonymous user
            return method_func(url, data)
