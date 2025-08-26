import json                                    # zum schöneren Debug von Responses
import pytest                                  # pytest Test-Framework
from rest_framework.test import APIClient      # DRF-Testclient für API-Calls


@pytest.fixture
def api_client():
    # Liefert einen frischen API-Client für jeden Test
    return APIClient()


def assert_optional_empty(profile_json):
    # Hilfsfunktion: prüft, dass optionale Profilfelder leer bleiben (None oder '')
    for key in ['file', 'location', 'tel', 'description', 'working_hours']:
        val = profile_json.get(key)
        assert (val is None) or (val == ''), f'Feld {key} sollte leer sein, ist aber: {val!r}'


def test_registration_customer_minimal_profile(api_client):
    # Registriert einen neuen Customer-Nutzer
    payload = {
        'username': 'testuser_customer',
        'email': 'testuser_customer@example.de',
        'password': 'pass1234',
        'repeated_password': 'pass1234',
        'type': 'customer',                     # wichtiger Teil: Kunde vs Business
    }
    res = api_client.post('/api/registration/', payload, format='json')  # POST /api/registration/
    assert res.status_code in (200, 201), res.content                    # 200/201 OK
    data = res.json()                                                     # Antwort als Dict
    # Response-Format prüfen
    for k in ['token', 'username', 'email', 'user_id']:
        assert k in data, f'Schlüssel {k} fehlt in Registration-Response'
    assert data['username'] == payload['username']
    assert data['email'] == payload['email']
    user_id = data['user_id']                                            # ID für Profil-GET merken

    # Direkt danach: Profil abrufen und prüfen, dass nur 'type' gesetzt wurde
    prof = api_client.get(f'/api/profile/{user_id}/')                    # GET /api/profile/<id>/
    assert prof.status_code == 200, prof.content
    p = prof.json()
    # Pflichtfelder vorhanden?
    for k in ['user', 'username', 'email', 'type', 'created_at']:
        assert k in p, f'{k} fehlt im Profil-Response'
    assert p['type'] == 'customer'                                       # gewählter Typ gesetzt
    # optionale Felder müssen leer bleiben
    assert_optional_empty(p)


def test_registration_business_minimal_profile(api_client):
    # Registriert einen neuen Business-Nutzer
    payload = {
        'username': 'testuser_business',
        'email': 'testuser_business@example.com',
        'password': 'pass1234',
        'repeated_password': 'pass1234',
        'type': 'business',                    # diesmal Business
    }
    res = api_client.post('/api/registration/', payload, format='json')
    assert res.status_code in (200, 201), res.content
    user_id = res.json()['user_id']

    # Profil prüfen
    prof = api_client.get(f'/api/profile/{user_id}/')
    assert prof.status_code == 200, prof.content
    p = prof.json()
    assert p['type'] == 'business'                                      # gewählter Typ übernommen
    assert_optional_empty(p)                                            # Rest bleibt leer


def test_login_returns_token_userinfo(api_client):
    # Erst registrieren...
    payload = {
        'username': 'login_tester',
        'email': 'login_tester@example.es',
        'password': 'pass1234',
        'repeated_password': 'pass1234',
        'type': 'customer',
    }
    reg = api_client.post('/api/registration/', payload, format='json')
    assert reg.status_code in (200, 201), reg.content

    # ...dann Login prüfen
    login_payload = {
        'username': payload['username'],
        'password': payload['password'],
    }
    res = api_client.post('/api/login/', login_payload, format='json')  # POST /api/login/
    assert res.status_code == 200, res.content
    data = res.json()
    # erwartetes Response-Format prüfen
    for k in ['token', 'username', 'email', 'user_id']:
        assert k in data, f'Schlüssel {k} fehlt in Login-Response'
    assert data['username'] == payload['username']
    assert data['email'] == payload['email']
