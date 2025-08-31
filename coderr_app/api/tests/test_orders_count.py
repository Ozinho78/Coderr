import json
import pytest
from django.urls import reverse

def _create_order_via_api(client, user, auth_header_for, detail_id):
    url = reverse('orders-list-create')
    res = client.post(url, data=json.dumps({'offer_detail_id': detail_id}), content_type='application/json', **auth_header_for(user))
    assert res.status_code == 201
    return res.json()['id']

@pytest.mark.django_db
def test_order_count_401_requires_auth(client, business_user):
    url = reverse('orders-in-progress-count', kwargs={'business_user_id': business_user.id})
    res = client.get(url)
    assert res.status_code == 401

@pytest.mark.django_db
def test_order_count_404_if_not_business(client, customer_user, auth_header_for):
    url = reverse('orders-in-progress-count', kwargs={'business_user_id': customer_user.id})
    res = client.get(url, **auth_header_for(customer_user))
    assert res.status_code == 404

@pytest.mark.django_db
def test_order_count_200_ok_returns_number(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    # zwei Orders im Status in_progress (Default) auf den Business
    _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)
    _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)

    url = reverse('orders-in-progress-count', kwargs={'business_user_id': business_user.id})
    res = client.get(url, **auth_header_for(customer_user))  # jeder eingeloggte darf abrufen
    assert res.status_code == 200
    assert res.json()['order_count'] >= 2
