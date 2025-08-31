import json
import pytest
from django.urls import reverse
from coderr_app.models import Order

@pytest.mark.django_db
def test_get_orders_401(client):
    # ohne Auth sollte 401 kommen
    url = reverse('orders-list-create')        # entspricht path('orders/', ...)
    res = client.get(url)
    assert res.status_code == 401

@pytest.mark.django_db
def test_post_orders_401(client):
    # ohne Auth → 401
    url = reverse('orders-list-create')
    res = client.post(url, data={'offer_detail_id': 123}, content_type='application/json')
    assert res.status_code == 401

@pytest.mark.django_db
def test_post_orders_403_non_customer(client, business_user, auth_header_for, sample_offerdetail_new_schema):
    # als Business posten → 403 (nur 'customer' dürfen anlegen)
    url = reverse('orders-list-create')
    headers = auth_header_for(business_user)
    payload = {'offer_detail_id': sample_offerdetail_new_schema.id}
    res = client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
    assert res.status_code == 403
    assert 'Nur Kunden' in res.json().get('detail', '')

@pytest.mark.django_db
def test_post_orders_404_invalid_detail(client, customer_user, auth_header_for):
    # ungültige ID → 404
    url = reverse('orders-list-create')
    headers = auth_header_for(customer_user)
    payload = {'offer_detail_id': 999999}
    res = client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
    assert res.status_code == 404

@pytest.mark.django_db
def test_post_orders_403_own_offer(client, customer_user, auth_header_for):
    # Kunde darf NICHT eigenes Offer bestellen
    # Kunde erzeugt (fälschlich) selbst ein Offer → sollte 403 bei POST geben
    from coderr_app.models import Offer, OfferDetail
    offer = Offer.objects.create(user=customer_user, title='Eigenes', description='x')
    detail = OfferDetail.objects.create(offer=offer, price='50.00', delivery_time=3, name='Basic')
    url = reverse('orders-list-create')
    headers = auth_header_for(customer_user)
    payload = {'offer_detail_id': detail.id}
    res = client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
    assert res.status_code == 403

@pytest.mark.django_db
def test_post_orders_201_new_schema(client, customer_user, auth_header_for, sample_offerdetail_new_schema):
    # Glücksfall: Detail mit modernem Schema → alle Felder werden sauber übernommen
    url = reverse('orders-list-create')
    headers = auth_header_for(customer_user)
    payload = {'offer_detail_id': sample_offerdetail_new_schema.id}

    res = client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
    assert res.status_code == 201

    data = res.json()
    # Grundstruktur prüfen
    for key in ['id','customer_user','business_user','title','revisions','delivery_time_in_days','price','features','offer_type','status','created_at','updated_at']:
        assert key in data

    # Werte aus dem OfferDetail übernommen?
    assert data['title'] == 'Basic API'
    assert data['revisions'] == 3
    assert data['delivery_time_in_days'] == 5
    assert data['features'] == ['REST', 'Docs']
    assert data['offer_type'] == 'basic'
    assert data['status'] == 'in_progress'

@pytest.mark.django_db
def test_post_orders_201_old_schema_fallbacks(client, customer_user, auth_header_for, sample_offerdetail_old_schema):
    # Altes Schema: name/delivery_time → Fallbacks greifen
    url = reverse('orders-list-create')
    headers = auth_header_for(customer_user)
    payload = {'offer_detail_id': sample_offerdetail_old_schema.id}

    res = client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
    assert res.status_code == 201
    data = res.json()

    # Fallbacks aus der View: title=detail.title or detail.name or 'Bestellung'
    assert data['title'] in ('Standard', 'Bestellung')
    # delivery_time_in_days = delivery_time_in_days or delivery_time or 0
    assert data['delivery_time_in_days'] in (7, 0)
    # offer_type = offer_type or name.lower() or 'basic'
    assert data['offer_type'] in ('standard', 'basic')

@pytest.mark.django_db
def test_get_orders_only_own(client, customer_user, business_user, auth_header_for, sample_offerdetail_new_schema):
    # 1) Kunde legt eine Order an
    url = reverse('orders-list-create')
    headers = auth_header_for(customer_user)
    payload = {'offer_detail_id': sample_offerdetail_new_schema.id}
    res = client.post(url, data=json.dumps(payload), content_type='application/json', **headers)
    assert res.status_code == 201
    order_id = res.json()['id']

    # 2) Kunde sieht die Order in GET
    res_get = client.get(url, **headers)
    assert res_get.status_code == 200
    ids = [o['id'] for o in res_get.json()]
    assert order_id in ids

    # 3) Ein völlig Unbeteiligter (anderer Business) darf sie nicht in seiner Liste sehen
    other_headers = auth_header_for(business_user)
    res_get_other = client.get(url, **other_headers)
    assert res_get_other.status_code == 200
    other_ids = [o['id'] for o in res_get_other.json()]
    assert order_id not in other_ids