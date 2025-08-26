# ---- Imports & Setup ---------------------------------------------------------
import re
import pytest  # pytest für Tests
from django.urls import reverse, NoReverseMatch  # URL-Auflösung per Namen
from django.contrib.auth import get_user_model  # generisch für das Usermodell
from django.db import transaction                      # für atomare get_or_create-Operation
from rest_framework.test import APIClient  # DRF-Testclient
from django.core.files.uploadedfile import SimpleUploadedFile  # Fake-Datei für file-Feld
from auth_app.models import Profile  # dein Profilmodell

User = get_user_model()  # Referenz auf das Usermodell


# ---- Hilfsfunktionen ---------------------------------------------------------

def build_profile_url(pk: int) -> str:
    # versucht zunächst, die Route per Namen zu finden
    try:
        return reverse('profile-detail', kwargs={'pk': pk})  # bevorzugt: URL-Namen verwenden
    except NoReverseMatch:
        # Fallback, falls der URL-Name im Projekt anders heißt oder nicht registriert ist
        return f'/api/profile/{pk}/'  # direkter Pfad als Rückfallebene


def create_user(username='max_mustermann', email='old_email@business.de'):
    # User wird erstellt; ein Profil kann durch Signals automatisch entstehen
    # first_name/last_name leer, damit PATCH sie setzt
    return User.objects.create(username=username, email=email, first_name='', last_name='')
    # return User.objects.create(username=username, email=email, first_name='', last_name='')


def create_profile(user, type_='business', with_file=True):
    # Falls ein Profil durch Signals schon existiert, nicht erneut anlegen → get_or_create
    with transaction.atomic():
        profile, created = Profile.objects.get_or_create(
            user=user,                                  # OneToOne – Schlüssel
            defaults={                                  # Defaults wenn neu
                'location': '',
                'tel': '',
                'description': '',
                'working_hours': '',
                'type': type_,
            },
        )

    # Wenn das Profil schon existierte, sorgen wir dafür, dass unsere Test-Annahmen stimmen:
    # - type setzen (falls im Projekt kein default) 
    # - optional eine Datei anhängen, damit Serializer 'file' → 'profile_picture.jpg' liefert
    updated = False

    if profile.type != type_:
        profile.type = type_
        updated = True

    if with_file:
        # Nur setzen, wenn noch keine Datei vorhanden
        if not getattr(profile, 'file', None):
            profile.file = SimpleUploadedFile(
                name='profile_picture.jpg',
                content=b'\x47\x49\x46',               # ein paar Bytes reichen für den Test
                content_type='image/jpeg',
            )
            updated = True

    # sicherstellen, dass Textfelder nicht None sind (Serializer ersetzt None → '')
    for f in ['location', 'tel', 'description', 'working_hours']:
        if getattr(profile, f, None) is None:
            setattr(profile, f, '')
            updated = True

    if updated:
        profile.save()

    return profile




# def create_profile(user, type_='business', with_file=True):
#     # optional eine Fake-Bilddatei erzeugen, damit 'file' im Serializer einen Dateinamen liefert
#     uploaded = None  # Standard: keine Datei
#     if with_file:
#         uploaded = SimpleUploadedFile(  # kleine Dummy-Datei mit Bild-Mime
#             name='profile_picture.jpg',
#             content=b'\x47\x49\x46',  # ein paar Bytes
#             content_type='image/jpeg',
#         )
#     # Profilmodell anlegen; übrige Felder leer lassen (werden im Test gepatcht)
#     return Profile.objects.create(
#         user=user,
#         file=uploaded,
#         location='',
#         tel='',
#         description='',
#         working_hours='',
#         type=type_,  # z. B. 'business'
#     )


# ---- Fixtures ----------------------------------------------------------------

@pytest.fixture
def api_client():
    # DRF-APIClient-Instanz pro Test
    return APIClient()


@pytest.fixture
def owner_user():
    # der Besitzer des Profils (darf PATCH)
    return create_user(username='max_mustermann', email='old_email@business.de')


@pytest.fixture
def other_user():
    # ein anderer authentifizierter User (darf NICHT PATCH)
    return create_user(username='someone_else', email='other@example.com')


@pytest.fixture
def owner_profile(owner_user):
    # Profil für den Besitzer; enthält eine Datei, damit der Serializer 'file' → 'profile_picture.jpg' liefert
    return create_profile(owner_user, type_='business', with_file=True)


# ---- Tests -------------------------------------------------------------------

@pytest.mark.django_db  # aktiviert die Testdatenbank
def test_patch_own_profile_returns_200(api_client, owner_user, owner_profile):
    # URL für das konkrete Profil bestimmen
    url = build_profile_url(owner_profile.pk)

    # Patch-Daten wie in deinem Beispiel
    payload = {
        'first_name': 'Max',
        'last_name': 'Mustermann',
        'location': 'Berlin',
        'tel': '987654321',
        'description': 'Updated business description',
        'working_hours': '10-18',
        'email': 'new_email@business.de',
    }

    # Als Eigentümer authentifizieren (kein echter Login nötig)
    api_client.force_authenticate(user=owner_user)

    # PATCH-Request mit JSON-Payload absenden
    resp = api_client.patch(url, data=payload, format='json')

    # Erwartet: 200 OK
    assert resp.status_code == 200

    # Response-JSON extrahieren
    data = resp.json()

    # Kern-Felder prüfen (genau wie dein gewünschtes Schema)
    assert data['user'] == owner_user.id  # User-ID muss stimmen
    assert data['username'] == 'max_mustermann'  # Username aus dem User
    assert data['first_name'] == 'Max'  # aus Payload
    assert data['last_name'] == 'Mustermann'  # aus Payload
    assert data['location'] == 'Berlin'  # aus Payload
    assert data['tel'] == '987654321'  # aus Payload
    assert data['description'] == 'Updated business description'  # aus Payload
    assert data['working_hours'] == '10-18'  # aus Payload
    assert data['type'] == 'business'  # unverändert vom Profil
    assert data['email'] == 'new_email@business.de'  # E-Mail im verknüpften User aktualisiert

    # 'file' sollte der Basisname der hochgeladenen Datei sein
    # assert data['file'] == 'profile_picture.jpg'
    # robust gegen Suffixe wie '_luSpwwK'
    # assert re.fullmatch(r'profile_picture.*\.jpg', data['file']) is not None
    assert data['file'].startswith('profile_picture') and data['file'].endswith('.jpg') # ohne re

    # 'created_at' sollte vorhanden und ein String sein (konkrete Zeit hängt vom DB-Autowert ab)
    assert isinstance(data['created_at'], str) and data['created_at'] != ''


@pytest.mark.django_db
def test_patch_unauthenticated_returns_401(api_client, owner_profile):
    # URL für das Profil
    url = build_profile_url(owner_profile.pk)

    # Ohne Authentifizierung patchen
    resp = api_client.patch(url, data={'first_name': 'X'}, format='json')

    # Erwartet: 401 Unauthorized (durch IsAuthenticatedOrReadOnly)
    assert resp.status_code == 401


@pytest.mark.django_db
def test_patch_other_user_returns_403(api_client, owner_profile, other_user):
    # URL für das Profil
    url = build_profile_url(owner_profile.pk)

    # Als anderer (nicht-Eigentümer) authentifizieren
    api_client.force_authenticate(user=other_user)

    # Versuch zu patchen
    resp = api_client.patch(url, data={'first_name': 'Hacker'}, format='json')

    # Erwartet: 403 Forbidden (durch IsOwnerOrReadOnly)
    assert resp.status_code == 403


@pytest.mark.django_db
def test_patch_non_existing_profile_returns_404(api_client, owner_user):
    # eine nicht existierende PK wählen (z. B. sehr hohe Zahl)
    url = build_profile_url(999999)

    # als legitimer User authentifizieren
    api_client.force_authenticate(user=owner_user)

    # PATCH auf nicht vorhandenes Profil
    resp = api_client.patch(url, data={'first_name': 'Max'}, format='json')

    # Erwartet: 404 Not Found (Generic-View löst das aus)
    assert resp.status_code == 404
