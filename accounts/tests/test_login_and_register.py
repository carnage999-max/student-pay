import logging
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from factories import DepartmentFactory
from .test_ini import BaseUserTestCase


class RegisterUserTests(BaseUserTestCase):
    def test_register_user(self):
        user = DepartmentFactory.build()
        reg_data = {"email": user.email, "dept_name": user.dept_name, "password": user.password}
        response = self.client.post(reverse("register-list"), data=reg_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('access_token', response.json())
        self.assertIn("refresh_token", response.json())
        
    def test_register_user_with_missing_required_fields(self):
        user = DepartmentFactory.build()
        reg_data = {"email": user.email, "password": user.password}
        response = self.client.post(reverse('register-list'), data=reg_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        
    def test_register_existing_user(self):
        user = DepartmentFactory.create()
        reg_data = {'email':user.email, 'dept_name': user.dept_name, 'password': 'Testpass123'}
        response = self.client.post(reverse('register-list'), data=reg_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.json()['error'])
        
class LoginUserTests(BaseUserTestCase):
    def setUp(self):
        super().setUp()
        self.user = DepartmentFactory.create()
        
    def test_user_login(self):
        login_data = {'email': self.user.email, 'password': self.password}
        response = self.client.post(reverse('login-list'), data=login_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.json())
        self.assertIn("refresh_token", response.json())
        
    def test_user_login_incorrect_credentials(self):
        response = self.client.post(reverse('login-list'), data={'email': self.user.email, 'password': "wrongpassword"})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertEqual(response.json()['error'], "Email or Password is incorrect")

