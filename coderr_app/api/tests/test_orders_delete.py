import json
import pytest
from django.urls import reverse

def _create_order_via_api(client, customer_user, auth_header_for, detail_id):
    url = reverse('orders-list-create')
    headers = auth_header_for(customer_user)
    res = client.post(url, data=json.dumps({'offer_detail_id': detail_id}), content_type='application/json', **headers)
    assert res.status_code == 201
    return res.json()['id']

@pytest.mark.django_db
def test_delete_orders_401_unauth(client, customer_user, sample_offerdetail_new_schema, auth_header_for):
    # Order korrekt anlegen (mit Auth)
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)

    # Danach: ohne Auth löschen → 401
    url = reverse('orders-status-update', kwargs={'pk': order_id})
    res = client.delete(url)
    assert res.status_code == 401

@pytest.mark.django_db
def test_delete_orders_403_non_staff(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)
    url = reverse('orders-status-update', kwargs={'pk': order_id})
    # eingeloggt, aber nicht staff → 403
    res = client.delete(url, **auth_header_for(business_user))
    assert res.status_code == 403

@pytest.mark.django_db
def test_delete_orders_204_staff_ok(client, customer_user, staff_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)
    url = reverse('orders-status-update', kwargs={'pk': order_id})
    res = client.delete(url, **auth_header_for(staff_user))
    assert res.status_code == 204
    # Doppelt löschen → 404
    res2 = client.delete(url, **auth_header_for(staff_user))
    assert res2.status_code == 404
