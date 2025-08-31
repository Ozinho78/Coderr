import pytest
from django.urls import reverse
import json

@pytest.mark.django_db
def test_completed_order_count_requires_auth(client, business_user):
    url = reverse('orders-completed-count', kwargs={'business_user_id': business_user.id})
    res = client.get(url)
    assert res.status_code == 401

@pytest.mark.django_db
def test_completed_order_count_404_if_not_business(client, customer_user, auth_header_for):
    url = reverse('orders-completed-count', kwargs={'business_user_id': customer_user.id})
    res = client.get(url, **auth_header_for(customer_user))
    assert res.status_code == 404

@pytest.mark.django_db
def test_completed_order_count_ok(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    # Bestellung anlegen
    url_create = reverse('orders-list-create')
    res = client.post(url_create, data=json.dumps({'offer_detail_id': sample_offerdetail_new_schema.id}),
                      content_type='application/json', **auth_header_for(customer_user))
    assert res.status_code == 201
    order_id = res.json()['id']

    # Bestellung auf completed patchen
    url_patch = reverse('orders-status-update', kwargs={'pk': order_id})
    res = client.patch(url_patch, data=json.dumps({'status': 'completed'}),
                       content_type='application/json', **auth_header_for(business_user))
    assert res.status_code == 200

    # Zählen lassen
    url_count = reverse('orders-completed-count', kwargs={'business_user_id': business_user.id})
    res = client.get(url_count, **auth_header_for(customer_user))  # jeder eingeloggte darf abrufen
    assert res.status_code == 200
    assert res.json()['completed_order_count'] >= 1
