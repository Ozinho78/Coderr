import pytest
from django.contrib.auth.models import User
from django.db import transaction
from rest_framework.authtoken.models import Token
from auth_app.models import Profile
from coderr_app.models import Offer, OfferDetail

def _ensure_profile(user, type_):
    # erzeugt ODER holt das Profil (Signal kann es schon erstellt haben)
    with transaction.atomic():
        profile, _created = Profile.objects.get_or_create(
            user=user,
            defaults={
                'type': type_,
                'location': '',
                'tel': '',
                'description': '',
                'working_hours': '',
            },
        )
    # falls vorhandenes Profil einen anderen Typ hatte → korrigieren
    if profile.type != type_:
        profile.type = type_
        profile.save(update_fields=['type'])
    return profile

@pytest.fixture
def staff_user(db, django_user_model):
    u = django_user_model.objects.create_user(username='admin', email='a@x.de', password='pw123456', is_staff=True)
    return u

@pytest.fixture
def customer_user(db):
    u = User.objects.create_user(username='cust', password='pw123456', email='c@x.de')
    _ensure_profile(u, 'customer')
    Token.objects.get_or_create(user=u)
    return u

@pytest.fixture
def business_user(db):
    u = User.objects.create_user(username='biz', password='pw123456', email='b@x.de')
    _ensure_profile(u, 'business')
    Token.objects.get_or_create(user=u)
    return u

@pytest.fixture
def another_business_user(db):
    u = User.objects.create_user(username='biz2', password='pw123456', email='b2@x.de')
    _ensure_profile(u, 'business')
    Token.objects.get_or_create(user=u)
    return u

@pytest.fixture
def auth_header_for():
    # Fabrik: erzeuge einen HTTP_AUTHORIZATION-Header für den gegebenen User
    def _mk(u):
        token, _ = Token.objects.get_or_create(user=u)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}
    return _mk

@pytest.fixture
def sample_offerdetail_new_schema(business_user):
    offer = Offer.objects.create(user=business_user, title='API Entwicklung #X', description='desc')
    detail = OfferDetail.objects.create(
        offer=offer,
        price='150.00',
        delivery_time=5,
        title='Basic API',
        revisions=3,
        delivery_time_in_days=5,
        features=['REST', 'Docs'],
        offer_type='basic',
        name='',
    )
    return detail

@pytest.fixture
def sample_offerdetail_old_schema(another_business_user):
    offer = Offer.objects.create(user=another_business_user, title='Website #Y', description='desc')
    detail = OfferDetail.objects.create(
        offer=offer,
        price='100.00',
        delivery_time=7,
        name='Standard',
        # alte Felder bewusst un-/leer lassen
    )
    return detail