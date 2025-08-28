from faker import Faker
import logging
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework_simplejwt.tokens import RefreshToken
from factories import DepartmentFactory


logger = logging.getLogger(__name__)


class BaseUserTestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()


class RegisterUserTests(BaseUserTestCase):
    def test_register_user(self):
        user = DepartmentFactory.build()
        reg_data = {"email": user.email, "dept_name": user.dept_name, "password": user.password}
        print(f"Creating User: {user.email, user.dept_name}")
        response = self.client.post(reverse("register-list"), data=reg_data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        
    def test_register_user_with_missing_required_fields(self):
        user = DepartmentFactory.build()
        reg_data = {"email": user.email, "password": user.password}
        response = self.client.post(reverse('register-list'), data=reg_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_register_existing_user(self):
        user = DepartmentFactory.create(email="user1@test.com", dept_name='department', password='passout908989P')
        reg_data = {'email':user.email, 'dept_name': user.dept_name, 'password': user.password}
        response = self.client.post(reverse('register-list'), data=reg_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.json()['error'])
        
class LoginUserTests(BaseUserTestCase):
    def test_user_login(self):
        user = DepartmentFactory()
        response = self.client.post(reverse('login-list'), data={'email': user.email, 'password': user.password})
        print(response.json())
        self.assertEqual(response.status_code, status.HTTP_200_OK)
