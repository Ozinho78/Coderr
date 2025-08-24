from django.contrib.auth.models import User
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


class RegistrationValidatorTests(APITestCase):
    def setUp(self):
        self.url = reverse("registration")

    def _payload(self, **overrides):
        base = {
            "username": "neo",
            "email": "neo@example.com",
            "password": "StrongPassw0rd!",
            "repeated_password": "StrongPassw0rd!",
            "type": "customer",
        }
        base.update(overrides)
        return base

    def _assert_field_error(self, res, field):
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(field, res.data)
        # Fehlermeldung kann string ODER liste sein – beides ok
        msg = res.data[field]
        self.assertTrue(isinstance(msg, (list, str)))

    def test_invalid_email_format_returns_400(self):
        res = self.client.post(
            self.url,
            self._payload(email="not-an-email"),
            format="json",
        )
        self._assert_field_error(res, "email")

    def test_weak_password_returns_400(self):
        # Länge >= 8, aber schwach -> triggert deinen Passwort-Validator statt min_length
        weak = "aaaaaaaa"  # 8x 'a'
        res = self.client.post(
            self.url,
            self._payload(password=weak, repeated_password=weak),
            format="json",
        )
        self._assert_field_error(res, "password")

    def test_password_mismatch_returns_400(self):
        res = self.client.post(
            self.url,
            self._payload(repeated_password="Different123!"),
            format="json",
        )
        self._assert_field_error(res, "repeated_password")

    def test_duplicate_email_case_insensitive_returns_400(self):
        # existierender Benutzer mit gleicher E-Mail in anderer Groß/Kleinschreibung
        User.objects.create_user(username="existing", email="USER@Example.com", password="Xx123456!!")
        res = self.client.post(
            self.url,
            self._payload(username="newuser", email="user@example.com"),
            format="json",
        )
        self._assert_field_error(res, "email")

    def test_success_still_returns_token_201(self):
        res = self.client.post(
            self.url,
            self._payload(username="trinity", email="trinity@example.com"),
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        for key in ("token", "username", "email", "user_id"):
            self.assertIn(key, res.data)
        self.assertEqual(res.data["username"], "trinity")
        self.assertEqual(res.data["email"], "trinity@example.com")
        
