from django.test import override_settings

from rest_framework.test import APIClient

from core.tests.utils import GraceDbTestBase

# Need to allow requests without a client version header
# to access the API for tests, unless we want to set and
# update that header ourselves...
@override_settings(
    ALLOW_BLANK_USER_AGENT_TO_API=True,
)
class GraceDbApiTestBase(GraceDbTestBase):
    client_class = APIClient
