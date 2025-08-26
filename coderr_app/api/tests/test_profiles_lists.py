import re  # für robuste Dateinamen-Prüfung
import pytest  # Test-Framework
from django.urls import reverse, NoReverseMatch  # URL-Auflösung (mit Fallback)
from django.contrib.auth import get_user_model  # generisch für das Usermodell
from django.core.files.uploadedfile import SimpleUploadedFile  # Fake-Datei
from rest_framework.test import APIClient  # DRF-Testclient
from django.db import transaction  # atomar für get_or_create
from auth_app.models import Profile  # Profilmodell

User = get_user_model()  # Referenz auf das Usermodell


# ------------------------ Hilfsfunktionen ------------------------

def build_url(name: str, fallback: str) -> str:
    # versucht zunächst, die Route per Namen zu finden
    try:
        return reverse(name)
    except NoReverseMatch:
        # Fallback, falls URL-Name im Projekt anders heißt oder fehlt
        return fallback

def create_user(username: str, email: str):
    # einfacher User ohne Zwangs-Passwort – wir nutzen force_authenticate
    return User.objects.create(username=username, email=email, first_name='', last_name='')

def get_or_create_profile(user, type_: str, with_file: bool = True, set_nulls: bool = False):
    # holt oder erzeugt ein Profil (OneToOne → UNIQUE), damit kein IntegrityError entsteht
    with transaction.atomic():
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'type': type_,
                'location': '',
                'tel': '',
                'description': '',
                'working_hours': '',
            },
        )

    # Typ setzen (falls bereits vorhanden war)
    updated = False
    if profile.type != type_:
        profile.type = type_
        updated = True

    # optional eine Testdatei anhängen (liefert im Serializer einen Dateinamen)
    if with_file and not getattr(profile, 'file', None):
        profile.file = SimpleUploadedFile(
            name='profile_picture.jpg',
            content=b'\x47\x49\x46',  # ein paar Bytes reichen
            content_type='image/jpeg',
        )
        updated = True

    # für Null-→''-Test einige Felder auf None setzen (wenn gewünscht)
    if set_nulls:
        for f in ['location', 'tel', 'description', 'working_hours']:
            setattr(profile, f, None)
        # first/last_name kommen vom User; auf None setzen wir hier nicht, da Userfelder meist non-null sind

    if updated or set_nulls:
        profile.save()

    return profile


# ------------------------ Fixtures ------------------------

@pytest.fixture
def api_client():
    # DRF-Testclient Instanz
    return APIClient()

@pytest.fixture
def auth_user_business(api_client):
    # ein eingeloggter User (z. B. Business-Nutzer)
    user = create_user('max_business', 'max@biz.de')
    api_client.force_authenticate(user=user)  # für auth-Tests direkt authentifizieren
    return user

@pytest.fixture
def business_profile(auth_user_business):
    # Profil für den eingeloggten User, Typ 'business', mit Datei
    return get_or_create_profile(auth_user_business, 'business', with_file=True, set_nulls=False)

@pytest.fixture
def another_customer_user():
    # ein zweiter User, der 'customer' ist (für Filter-Tests)
    return create_user('customer_jane', 'jane@cust.de')

@pytest.fixture
def customer_profile(another_customer_user):
    # Profil für den zweiten User, Typ 'customer', mit Datei, und mit Null-Feldern (um ''-Konvertierung zu prüfen)
    return get_or_create_profile(another_customer_user, 'customer', with_file=True, set_nulls=True)


# ------------------------ Tests: /api/profiles/business/ ------------------------

@pytest.mark.django_db
def test_business_list_requires_auth_401(api_client):
    # Endpoint per Namen oder Fallback zusammenbauen
    url = build_url('profiles-business', '/api/profiles/business/')
    # ohne Authentifizierung GET ausführen
    resp = api_client.get(url)
    # Erwartet: 401 Unauthorized
    assert resp.status_code == 401

@pytest.mark.django_db
def test_business_list_returns_200_and_schema(api_client, auth_user_business, business_profile, customer_profile):
    # auth_user_business ist bereits im Client authentifiziert (via Fixture)
    url = build_url('profiles-business', '/api/profiles/business/')
    resp = api_client.get(url)
    assert resp.status_code == 200  # erfolgreicher GET

    data = resp.json()  # JSON-Liste
    assert isinstance(data, list)

    # Es sollte mindestens EIN Business-Profil enthalten sein (das des eingeloggten Users)
    assert any(item.get('user') == auth_user_business.id for item in data)

    # Es sollte KEIN reines Customer-Profil enthalten sein (Filter funktioniert)
    assert all(item.get('type') == 'business' for item in data)

    # Ein Eintrag prüfen (den des eingeloggten Business-Users herausfischen)
    entry = next(item for item in data if item.get('user') == auth_user_business.id)

    # Pflichtfelder vorhanden
    for key in ['user', 'username', 'first_name', 'last_name', 'file', 'location', 'tel', 'description', 'working_hours', 'type']:
        assert key in entry

    # first_name/last_name/location/tel/description/working_hours → nie null (leerstring ok)
    for key in ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']:
        assert entry[key] is not None

    # Dateiname robust prüfen (Suffixe möglich)
    assert entry['file'] == '' or (entry['file'].startswith('profile_picture') and entry['file'].endswith('.jpg'))

    # Typ korrekt
    assert entry['type'] == 'business'


# ------------------------ Tests: /api/profiles/customer/ ------------------------

@pytest.mark.django_db
def test_customer_list_requires_auth_401(api_client):
    url = build_url('profiles-customer', '/api/profiles/customer/')
    resp = api_client.get(url)
    assert resp.status_code == 401  # ohne Auth → 401

@pytest.mark.django_db
def test_customer_list_returns_200_and_schema(api_client, auth_user_business, customer_profile, business_profile):
    # Wir sind als irgendein User authentifiziert; Liste soll trotzdem nur 'customer' liefern
    url = build_url('profiles-customer', '/api/profiles/customer/')
    resp = api_client.get(url)
    assert resp.status_code == 200

    data = resp.json()
    assert isinstance(data, list)

    # Alle Einträge müssen Typ 'customer' haben
    assert all(item.get('type') == 'customer' for item in data)

    # Den Customer-Eintrag des anderen Users finden
    entry = next(item for item in data if item.get('user') == customer_profile.user_id)

    # Pflichtfelder vorhanden
    for key in ['user', 'username', 'first_name', 'last_name', 'file', 'location', 'tel', 'description', 'working_hours', 'type']:
        assert key in entry

    # first_name/last_name/location/tel/description/working_hours → nie null ('' ist okay)
    for key in ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']:
        assert entry[key] is not None

    # Da wir im Fixture Nulls gesetzt haben, müssen diese im Response zu '' geworden sein
    # (location/tel/description/working_hours)
    for key in ['location', 'tel', 'description', 'working_hours']:
        assert entry[key] == ''  # Null-→''-Konvertierung greift

    # Dateiname robust prüfen
    assert entry['file'] == '' or (entry['file'].startswith('profile_picture') and entry['file'].endswith('.jpg'))
