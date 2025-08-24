from unittest.mock import patch
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


class ExceptionHandlerTests(APITestCase):
    def setUp(self):
        self.url = reverse("registration")
        self.payload = {
            "username": "buggy",
            "email": "buggy@example.com",
            "password": "Str0ngPassw0rd!",
            "repeated_password": "Str0ngPassw0rd!",
            "type": "customer",
        }

    @patch("rest_framework.authtoken.models.Token.objects.get_or_create", side_effect=RuntimeError("boom"))
    def test_unexpected_error_returns_custom_500(self, _mock_token):
        res = self.client.post(self.url, self.payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
        self.assertEqual(res.data, {"error": "Interner Serverfehler"})