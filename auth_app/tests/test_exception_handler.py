import logging
import pytest
from django.test import RequestFactory
from rest_framework.test import APIClient
from unittest import mock
from rest_framework.authtoken.models import Token

logger = logging.getLogger("core.utils.exceptions")

@pytest.mark.django_db
def test_unexpected_error_returns_custom_500(caplog):
    client = APIClient()

    # Logging für diesen Test abfangen
    caplog.set_level(logging.CRITICAL, logger="core.utils.exceptions")

    # Mock: Token.objects.get_or_create wirft absichtlich einen Fehler
    with mock.patch.object(Token.objects, "get_or_create", side_effect=RuntimeError("boom")):
        response = client.post("/api/registration/", {
            "username": "errortest",
            "email": "errortest@example.com",
            "password": "StrongPass123!",
            "repeated_password": "StrongPass123!",
            "type": "customer",
        }, format="json")

    assert response.status_code == 500
    assert response.json()["detail"] == "Internal Server Error"