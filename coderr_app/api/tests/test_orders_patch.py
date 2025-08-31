import json                                 # für JSON-Body
import pytest                               # pytest Deko/Assertions
from django.urls import reverse             # URL-Reverse by name
from coderr_app.models import Order         # Order für evtl. direkte Checks

# kleine Hilfsfunktion: erzeugt via POST eine Order und liefert deren id zurück
def _create_order_via_api(client, customer_user, auth_header_for, offerdetail_id):
    url = reverse('orders-list-create')     # POST /api/orders/
    headers = auth_header_for(customer_user)  # Auth-Header für den Customer
    payload = {'offer_detail_id': offerdetail_id}  # Body entspricht Spezifikation
    res = client.post(url, data=json.dumps(payload), content_type='application/json', **headers)  # Request senden
    assert res.status_code == 201           # sicherstellen, dass Anlegen klappt
    return res.json()['id']                 # neue Order-ID zurückgeben

@pytest.mark.django_db
def test_patch_orders_401_unauth(client, customer_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # Order anlegen
    url = reverse('orders-status-update', kwargs={'pk': order_id})  # PATCH-URL mit id
    res = client.patch(url, data=json.dumps({'status': 'completed'}), content_type='application/json')  # ohne Auth
    assert res.status_code == 401           # nicht authentifiziert → 401

@pytest.mark.django_db
def test_patch_orders_404_not_found(client, business_user, sample_offerdetail_new_schema, auth_header_for, customer_user):
    # Order normal anlegen, aber patchen mit nicht existenter ID
    _ = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # eine echte Order (nicht genutzt)
    url = reverse('orders-status-update', kwargs={'pk': 999999})  # nicht vorhandene ID
    headers = auth_header_for(business_user)   # irgendein eingeloggter Business (Auth nötig für 404)
    res = client.patch(url, data=json.dumps({'status': 'completed'}), content_type='application/json', **headers)
    assert res.status_code == 404            # unbekannte Order → 404

@pytest.mark.django_db
def test_patch_orders_403_customer_not_allowed(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # Order anlegen
    url = reverse('orders-status-update', kwargs={'pk': order_id})  # Patch-URL
    headers = auth_header_for(customer_user)  # Kunde (nicht erlaubt)
    res = client.patch(url, data=json.dumps({'status': 'completed'}), content_type='application/json', **headers)
    assert res.status_code == 403            # Kunde darf Status nicht ändern

@pytest.mark.django_db
def test_patch_orders_403_other_business_not_owner(client, customer_user, another_business_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # Order anlegen
    url = reverse('orders-status-update', kwargs={'pk': order_id})  # Patch-URL
    headers = auth_header_for(another_business_user)  # Business, aber NICHT Owner des Offers/Orders
    res = client.patch(url, data=json.dumps({'status': 'completed'}), content_type='application/json', **headers)
    assert res.status_code == 403            # falscher Business → 403

@pytest.mark.django_db
def test_patch_orders_400_invalid_status_value(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # Order anlegen
    url = reverse('orders-status-update', kwargs={'pk': order_id})  # Patch-URL
    headers = auth_header_for(business_user)  # richtiger Business (Owner des Offers)
    res = client.patch(url, data=json.dumps({'status': 'nope'}), content_type='application/json', **headers)  # ungültiger Status
    assert res.status_code == 400            # Validierungsfehler
    assert 'Ungültiger Status' in json.loads(res.content.decode('utf-8'))['status'][0] or 'Ungültiger Status' in res.json().get('detail', '')

@pytest.mark.django_db
def test_patch_orders_400_extra_fields_forbidden(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # Order anlegen
    url = reverse('orders-status-update', kwargs={'pk': order_id})  # Patch-URL
    headers = auth_header_for(business_user)  # richtiger Business
    bad_payload = {'status': 'completed', 'price': 999}  # zusätzliches Feld nicht erlaubt
    res = client.patch(url, data=json.dumps(bad_payload), content_type='application/json', **headers)
    assert res.status_code == 400            # nur 'status' erlaubt
    # Info-Text kommt aus OrderStatusPatchSerializer.validate(...)
    assert 'Nur das Feld "status" darf aktualisiert werden.' in res.json().get('non_field_errors', [''])[0]

@pytest.mark.django_db
def test_patch_orders_200_success_updates_status_and_returns_full_order(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # Order anlegen
    url = reverse('orders-status-update', kwargs={'pk': order_id})  # Patch-URL
    headers = auth_header_for(business_user)  # richtiger Business (Owner)
    res = client.patch(url, data=json.dumps({'status': 'completed'}), content_type='application/json', **headers)
    assert res.status_code == 200            # OK
    data = res.json()                        # komplette Order zurück
    # Felder wie in der Vorgabe prüfen (Spot-Checks)
    assert data['id'] == order_id            # gleiche ID
    assert data['status'] == 'completed'     # Status aktualisiert
    # Zeitstempel vorhanden (updated_at kommt von auto_now)
    assert 'created_at' in data
    assert 'updated_at' in data

@pytest.mark.django_db
def test_put_orders_400_only_patch_allowed(client, customer_user, business_user, sample_offerdetail_new_schema, auth_header_for):
    order_id = _create_order_via_api(client, customer_user, auth_header_for, sample_offerdetail_new_schema.id)  # Order anlegen
    url = reverse('orders-status-update', kwargs={'pk': order_id})  # URL
    headers = auth_header_for(business_user)  # richtiger Business
    res = client.put(url, data=json.dumps({'status': 'completed'}), content_type='application/json', **headers)  # PUT statt PATCH
    assert res.status_code == 400            # laut View nur PATCH zulässig
    assert 'Nur PATCH ist erlaubt.' in res.json().get('detail', '')