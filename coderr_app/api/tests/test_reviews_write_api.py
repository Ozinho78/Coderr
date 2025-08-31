# python manage.py test coderr_app.api.tests.test_reviews_write_api -v 2 --keepdb
from django.test import TestCase                             # Django TestCase-Basis
from django.contrib.auth.models import User                  # User-Modell
from django.utils import timezone                            # für Zeitstempel-Updates bei Bedarf
from rest_framework.test import APIClient                    # DRF-Testclient
from rest_framework import status                            # HTTP-Status-Codes
from auth_app.models import Profile                          # Profile (mit type = 'customer'/'business')
from coderr_app.models import Review                         # Review-Modell aus coderr_app


class ReviewWriteApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()                            # DRF-Testclient instanzieren

        # --- Testdaten: Business (Ziel der Bewertung) ---
        self.biz = User.objects.create_user(username='biz', password='x')  # Business-User
        Profile.objects.get_or_create(user=self.biz, defaults={'type': 'business'})  # unique je User

        # --- Testdaten: Zwei Customers (Reviewer) ---
        self.cust1 = User.objects.create_user(username='cust1', password='x')  # erster Customer
        Profile.objects.get_or_create(user=self.cust1, defaults={'type': 'customer'})  # Kundenprofil
        self.cust2 = User.objects.create_user(username='cust2', password='x')  # zweiter Customer
        Profile.objects.get_or_create(user=self.cust2, defaults={'type': 'customer'})  # Kundenprofil

        # --- Optional: ein weiterer Business-User (für Randfälle) ---
        self.biz2 = User.objects.create_user(username='biz2', password='x')   # weiterer Business
        Profile.objects.get_or_create(user=self.biz2, defaults={'type': 'business'})   # Businessprofil

        # Basis-URLs für die Endpoints
        self.list_url = '/api/reviews/'                         # POST/GET-Liste
        # Detail-URL wird pro Test aus der ID zusammengesetzt: f'/api/reviews/{id}/'

    # --------------------------------------------
    # POST /api/reviews/
    # --------------------------------------------

    def test_post_requires_authentication(self):
        # ohne Authentifizierung posten → 401
        payload = {'business_user': self.biz.id, 'rating': 4, 'description': 'ok'}
        resp = self.client.post(self.list_url, payload, format='json')  # POST ohne Login
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)  # muss 401 sein

    def test_post_requires_customer_profile(self):
        # als Business-User eingeloggt posten → 401 (nur Kunden dürfen erstellen)
        self.client.force_authenticate(user=self.biz)            # Login als Business (kein Customer)
        payload = {'business_user': self.biz2.id, 'rating': 4, 'description': 'ok'}  # Business bewertet Business (sollte eh nicht gehen)
        resp = self.client.post(self.list_url, payload, format='json')  # POST
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)  # laut Implementierung 401
        self.client.force_authenticate(user=None)                # Logout

    def test_post_success_201(self):
        # als Customer posten → 201 + korrektes Objekt
        self.client.force_authenticate(user=self.cust1)          # Login als Customer
        payload = {'business_user': self.biz.id, 'rating': 4, 'description': 'Alles war toll!'}  # gültiger Body
        resp = self.client.post(self.list_url, payload, format='json')  # POST
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)     # 201 erwartet
        data = resp.data                                           # Antwortdaten
        self.assertEqual(data['business_user'], self.biz.id)       # Business-ID korrekt
        self.assertEqual(data['reviewer'], self.cust1.id)          # Reviewer ist eingeloggter User
        self.assertEqual(data['rating'], 4)                         # Rating übernommen
        self.assertIn('created_at', data)                           # Timestamps vorhanden
        self.assertIn('updated_at', data)                           # Timestamps vorhanden
        self.client.force_authenticate(user=None)                   # Logout

    def test_post_duplicate_returns_400(self):
        # zweites Review gleicher Customer→Business → 400
        # Erstes Review anlegen
        Review.objects.create(business_user=self.biz, reviewer=self.cust1, rating=3, description='ok')  # vorhandene Bewertung
        self.client.force_authenticate(user=self.cust1)          # Login als gleicher Customer
        payload = {'business_user': self.biz.id, 'rating': 5, 'description': 'zweites Mal'}  # gleiche Paarung
        resp = self.client.post(self.list_url, payload, format='json')  # POST
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)  # Duplikat → 400 (laut Serializer-Validierung)
        self.client.force_authenticate(user=None)                # Logout

    def test_post_self_review_blocked(self):
        # Customer darf sich nicht selbst bewerten (theoretisch, wenn Customer==Business)
        # hier simulieren wir: cust1 versucht biz==cust1 (geht real nicht, aber Validierung schützen)
        self.client.force_authenticate(user=self.cust1)          # Login als Customer
        payload = {'business_user': self.cust1.id, 'rating': 4, 'description': 'self'}  # Business=Reviewer
        resp = self.client.post(self.list_url, payload, format='json')  # POST
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)  # 400 erwartet (non_field_errors)
        self.client.force_authenticate(user=None)                # Logout

    # --------------------------------------------
    # PATCH /api/reviews/{id}/
    # --------------------------------------------

    def test_patch_owner_only_200(self):
        # Ersteller (cust1) darf rating/description patchen → 200
        review = Review.objects.create(business_user=self.biz, reviewer=self.cust1, rating=3, description='ok')  # vorhandenes Review
        url = f'/api/reviews/{review.id}/'                         # Detail-URL
        self.client.force_authenticate(user=self.cust1)            # Login als Ersteller
        resp = self.client.patch(url, {'rating': 5, 'description': 'Noch besser!'}, format='json')  # PATCH
        self.assertEqual(resp.status_code, status.HTTP_200_OK)     # 200 erwartet
        self.assertEqual(resp.data['rating'], 5)                   # Rating aktualisiert
        self.assertEqual(resp.data['description'], 'Noch besser!') # Description aktualisiert
        self.client.force_authenticate(user=None)                  # Logout

    def test_patch_forbidden_for_non_owner_403(self):
        # Nicht-Ersteller (cust2) versucht zu patchen → 403
        review = Review.objects.create(business_user=self.biz, reviewer=self.cust1, rating=3, description='ok')  # Review gehört cust1
        url = f'/api/reviews/{review.id}/'                         # Detail-URL
        self.client.force_authenticate(user=self.cust2)            # Login als anderer User
        resp = self.client.patch(url, {'rating': 4}, format='json')  # PATCH
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)  # 403 erwartet
        self.client.force_authenticate(user=None)                  # Logout

    def test_patch_only_allowed_fields_400(self):
        # Versuch, ein nicht erlaubtes Feld zu ändern → 400
        review = Review.objects.create(business_user=self.biz, reviewer=self.cust1, rating=3, description='ok')  # vorhandenes Review
        url = f'/api/reviews/{review.id}/'                         # Detail-URL
        self.client.force_authenticate(user=self.cust1)            # Login als Ersteller
        resp = self.client.patch(url, {'business_user': self.biz2.id}, format='json')  # nicht erlaubt
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)  # 400 erwartet
        self.client.force_authenticate(user=None)                  # Logout

    def test_patch_invalid_rating_400(self):
        # rating außerhalb 1..5 → 400
        review = Review.objects.create(business_user=self.biz, reviewer=self.cust1, rating=3, description='ok')  # Review
        url = f'/api/reviews/{review.id}/'                         # Detail-URL
        self.client.force_authenticate(user=self.cust1)            # Login als Ersteller
        resp = self.client.patch(url, {'rating': 6}, format='json')  # ungültig
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)  # 400 erwartet
        self.client.force_authenticate(user=None)                  # Logout

    # --------------------------------------------
    # DELETE /api/reviews/{id}/
    # --------------------------------------------

    def test_delete_owner_only_204(self):
        # Ersteller darf löschen → 204
        review = Review.objects.create(business_user=self.biz, reviewer=self.cust1, rating=3, description='ok')  # Review
        url = f'/api/reviews/{review.id}/'                         # Detail-URL
        self.client.force_authenticate(user=self.cust1)            # Login als Ersteller
        resp = self.client.delete(url)                             # DELETE
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)  # 204 erwartet
        self.assertFalse(Review.objects.filter(id=review.id).exists())   # Review wirklich gelöscht
        self.client.force_authenticate(user=None)                  # Logout

    def test_delete_forbidden_for_non_owner_403(self):
        # Nicht-Ersteller darf nicht löschen → 403
        review = Review.objects.create(business_user=self.biz, reviewer=self.cust1, rating=3, description='ok')  # Review
        url = f'/api/reviews/{review.id}/'                         # Detail-URL
        self.client.force_authenticate(user=self.cust2)            # Login als anderer User
        resp = self.client.delete(url)                             # DELETE
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)  # 403 erwartet
        self.client.force_authenticate(user=None)                  # Logout

    def test_delete_not_found_404(self):
        # Löschen einer nicht existierenden ID → 404
        self.client.force_authenticate(user=self.cust1)            # irgendein eingeloggter User
        resp = self.client.delete('/api/reviews/999999/')          # nicht existent
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)  # 404 erwartet
        self.client.force_authenticate(user=None)                  # Logout
