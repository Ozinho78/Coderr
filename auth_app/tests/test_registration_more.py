from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from auth_app.models import Profile


class RegistrationMoreTests(APITestCase):
    def setUp(self):
        self.url = reverse("registration")
        self.valid = {
            "username": "morpheus",
            "email": "morpheus@example.com",
            "password": "Str0ngPassw0rd!",
            "repeated_password": "Str0ngPassw0rd!",
            "type": "customer",
        }

    def test_invalid_type_returns_400(self):
        payload = {**self.valid, "type": "freelancer"}  # ungültiger Wert
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("type", res.data)

    def test_profile_created_with_correct_type(self):
        res = self.client.post(self.url, self.valid, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username="morpheus")
        self.assertTrue(hasattr(user, "profile"))
        self.assertEqual(user.profile.type, "customer")

    def test_duplicate_username_case_insensitive_returns_400(self):
        User.objects.create_user(username="Neo", email="neo@matrix.io", password="Xx123456!!")
        payload = {**self.valid, "username": "neo", "email": "another@example.com"}
        res = self.client.post(self.url, payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("username", res.data)

    def test_token_is_returned_and_looks_nonempty(self):
        res = self.client.post(self.url, {**self.valid, "username": "trinity", "email": "trinity@example.com"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        token = res.data.get("token")
        self.assertTrue(isinstance(token, str) and len(token) >= 10)  # grober Smoke-Test