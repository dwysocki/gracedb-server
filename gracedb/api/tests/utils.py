from rest_framework.test import APIClient

from core.tests.utils import GraceDbTestBase


class GraceDbApiTestBase(GraceDbTestBase):
    client_class = APIClient
