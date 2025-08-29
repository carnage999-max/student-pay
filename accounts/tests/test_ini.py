from rest_framework.test import APIClient, APITestCase


class BaseUserTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.password = 'Testpass123'