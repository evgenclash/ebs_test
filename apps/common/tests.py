from django.test import TestCase
from rest_framework.reverse import reverse
from rest_framework.test import APIClient


class TestCommon(TestCase):

    def setUp(self) -> None:
        self.client = APIClient()

    def test_health_view(self):
        response = self.client.get(reverse('health_view'), )
        self.assertEqual(response.status_code, 200)
