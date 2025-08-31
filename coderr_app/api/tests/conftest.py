import pytest                                   # pytest-Fixture-System
from django.contrib.auth.models import User     # User-Modell
from rest_framework.authtoken.models import Token
from auth_app.models import Profile             # dein Profil (customer/business)
from coderr_app.models import Offer, OfferDetail

@pytest.fixture
def customer_user(db):
    # User anlegen
    u = User.objects.create_user(username='cust', password='pw123456', email='c@x.de')
    # Profil als 'customer'
    Profile.objects.create(user=u, type='customer')
    # Token für Auth
    Token.objects.get_or_create(user=u)
    return u

@pytest.fixture
def business_user(db):
    u = User.objects.create_user(username='biz', password='pw123456', email='b@x.de')
    Profile.objects.create(user=u, type='business')
    Token.objects.get_or_create(user=u)
    return u

@pytest.fixture
def another_business_user(db):
    u = User.objects.create_user(username='biz2', password='pw123456', email='b2@x.de')
    Profile.objects.create(user=u, type='business')
    Token.objects.get_or_create(user=u)
    return u

@pytest.fixture
def auth_header_for(user):
    # kleine Helfer-Fixture, erzeugt ein Header-Dict mit Bearer-Token für einen User
    def _mk(u):
        token, _ = Token.objects.get_or_create(user=u)
        return {'HTTP_AUTHORIZATION': f'Token {token.key}'}
    return _mk

@pytest.fixture
def sample_offerdetail_new_schema(business_user):
    # Business erstellt ein Offer + neues OfferDetail (mit modernen Feldern)
    offer = Offer.objects.create(user=business_user, title='API Entwicklung #X', description='desc')
    detail = OfferDetail.objects.create(
        offer=offer,
        price='150.00',
        delivery_time=5,                 # altes Feld bleibt gefüllt, schadet nicht
        title='Basic API',
        revisions=3,
        delivery_time_in_days=5,
        features=['REST', 'Docs'],
        offer_type='basic',
        name=''                          # bei neuen Datensätzen oft leer
    )
    return detail

@pytest.fixture
def sample_offerdetail_old_schema(another_business_user):
    # Business2: OfferDetail im alten Schema (nur name/delivery_time befüllt)
    offer = Offer.objects.create(user=another_business_user, title='Website #Y', description='desc')
    detail = OfferDetail.objects.create(
        offer=offer,
        price='100.00',
        delivery_time=7,                 # alt
        name='Standard',                 # alt
        # title/offer_type/delivery_time_in_days/features/revisions bewusst leer
    )
    return detail