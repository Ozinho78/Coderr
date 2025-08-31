import pytest
from django.core.management import call_command
from coderr_app.models import Offer, OfferDetail

@pytest.mark.django_db
def test_normalize_offerdetails_command(business_user):
    offer = Offer.objects.create(user=business_user, title='T', description='x')
    d = OfferDetail.objects.create(
        offer=offer,
        price='10.00',
        delivery_time=4,
        name='Basic',            # alt
        title='',                # leer
        offer_type='',           # leer
        delivery_time_in_days=None,  # das kann i. d. R. None sein; wenn dein Feld NOT NULL ist, setze hier '4'
        revisions=0,             # <<< HIER statt None, damit INSERT nicht scheitert
        features=None,           # bleibt None; der Command setzt dann []
    )
    # Dry-run
    call_command('normalize_offerdetails', '--dry-run')
    # Real run
    call_command('normalize_offerdetails')

    d.refresh_from_db()
    assert d.title == 'Basic'
    assert d.offer_type == 'basic'
    assert d.delivery_time_in_days == 4
    assert d.revisions == 0
    assert d.features == []