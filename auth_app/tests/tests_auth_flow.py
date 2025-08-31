import json
import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


def assert_optional_empty(profile_json):
    for key in ['file', 'location', 'tel', 'description', 'working_hours']:
        val = profile_json.get(key)
        assert (val is None) or (val == ''), f'Feld {key} sollte leer sein, ist aber: {val!r}'


def test_registration_customer_minimal_profile(api_client):
    payload = {
        'username': 'testuser_customer',
        'email': 'testuser_customer@example.de',
        'password': 'pass1234',
        'repeated_password': 'pass1234',
        'type': 'customer',
    }
    res = api_client.post('/api/registration/', payload, format='json')
    assert res.status_code in (200, 201), res.content                  
    data = res.json()
    for k in ['token', 'username', 'email', 'user_id']:
        assert k in data, f'Schlüssel {k} fehlt in Registration-Response'
    assert data['username'] == payload['username']
    assert data['email'] == payload['email']
    user_id = data['user_id']

    prof = api_client.get(f'/api/profile/{user_id}/')
    assert prof.status_code == 200, prof.content
    p = prof.json()
    for k in ['user', 'username', 'email', 'type', 'created_at']:
        assert k in p, f'{k} fehlt im Profil-Response'
    assert p['type'] == 'customer'
    assert_optional_empty(p)


def test_registration_business_minimal_profile(api_client):
    payload = {
        'username': 'testuser_business',
        'email': 'testuser_business@example.com',
        'password': 'pass1234',
        'repeated_password': 'pass1234',
        'type': 'business',
    }
    res = api_client.post('/api/registration/', payload, format='json')
    assert res.status_code in (200, 201), res.content
    user_id = res.json()['user_id']

    prof = api_client.get(f'/api/profile/{user_id}/')
    assert prof.status_code == 200, prof.content
    p = prof.json()
    assert p['type'] == 'business'
    assert_optional_empty(p)


def test_login_returns_token_userinfo(api_client):
    payload = {
        'username': 'login_tester',
        'email': 'login_tester@example.es',
        'password': 'pass1234',
        'repeated_password': 'pass1234',
        'type': 'customer',
    }
    reg = api_client.post('/api/registration/', payload, format='json')
    assert reg.status_code in (200, 201), reg.content

    login_payload = {
        'username': payload['username'],
        'password': payload['password'],
    }
    res = api_client.post('/api/login/', login_payload, format='json')
    assert res.status_code == 200, res.content
    data = res.json()
    for k in ['token', 'username', 'email', 'user_id']:
        assert k in data, f'Schlüssel {k} fehlt in Login-Response'
    assert data['username'] == payload['username']
    assert data['email'] == payload['email']