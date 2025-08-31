from django.contrib.auth.models import User                      # User erstellen
from django.test import TestCase                                 # Django-Testbasis
from rest_framework.test import APIClient                        # DRF-Testclient
from auth_app.models import Profile
from coderr_app.models import Review
from django.utils import timezone                                # Zeitstempel setzen

class ReviewApiTests(TestCase):
    def setUp(self):
        # DRF-Client initialisieren
        self.client = APIClient()

        # --- User + Profile anlegen -----------------------------------------
        # Business-User
        self.business = User.objects.create_user(username='biz', password='x')
        Profile.objects.create(user=self.business, type='business')

        # Zwei Customer-User (als Reviewer)
        self.cust1 = User.objects.create_user(username='c1', password='x')
        Profile.objects.create(user=self.cust1, type='customer')

        self.cust2 = User.objects.create_user(username='c2', password='x')
        Profile.objects.create(user=self.cust2, type='customer')

        # --- Reviews anlegen -------------------------------------------------
        # erstes Review (älter, niedrigeres Rating)
        self.rev1 = Review.objects.create(
            business_user=self.business,
            reviewer=self.cust1,
            rating=3,
            description='ok'
        )
        # zweites Review (neuer, höheres Rating)
        self.rev2 = Review.objects.create(
            business_user=self.business,
            reviewer=self.cust2,
            rating=5,
            description='top'
        )

        # updated_at kontrolliert setzen: rev2 soll "neuer" sein
        Review.objects.filter(pk=self.rev1.pk).update(updated_at=timezone.now() - timezone.timedelta(days=1))
        Review.objects.filter(pk=self.rev2.pk).update(updated_at=timezone.now())

        # Test-User zum Authentifizieren (kann irgendein existierender User sein)
        self.any_user = self.cust1

    def test_requires_authentication(self):
        # ohne Auth sollte 401 kommen
        resp = self.client.get('/api/reviews/')
        self.assertEqual(resp.status_code, 401)

    def test_default_ordering_updated_at_desc(self):
        # mit Auth (force_authenticate um Token/Session zu sparen)
        self.client.force_authenticate(user=self.any_user)
        resp = self.client.get('/api/reviews/')
        self.assertIsInstance(resp.data, list)
        self.assertGreaterEqual(len(resp.data), 2)
        self.assertEqual(resp.data[0]['id'], self.rev2.id)  # neuestes zuerst

    def test_filter_by_business_user_id(self):
        self.client.force_authenticate(user=self.any_user)
        # Nach business_user_id filtern (soll beide Reviews zurückgeben)
        resp = self.client.get(f'/api/reviews/?business_user_id={self.business.id}')
        self.assertEqual(resp.status_code, 200)
        returned_ids = [item['id'] for item in resp.data['results']]
        self.assertCountEqual(returned_ids, [self.rev1.id, self.rev2.id])

    def test_filter_by_reviewer_id(self):
        self.client.force_authenticate(user=self.any_user)
        # Nur Reviews von cust1
        resp = self.client.get(f'/api/reviews/?reviewer_id={self.cust1.id}')
        self.assertEqual(resp.status_code, 200)
        # genau ein Review (rev1)
        self.assertEqual(len(resp.data['results']), 1)
        self.assertEqual(resp.data['results'][0]['id'], self.rev1.id)

    def test_ordering_by_rating(self):
        self.client.force_authenticate(user=self.any_user)
        # ordering=rating → aufsteigend: zuerst rating=3 (rev1), dann rating=5 (rev2)
        resp = self.client.get('/api/reviews/?ordering=rating')
        self.assertEqual(resp.status_code, 200)
        ids = [item['id'] for item in resp.data['results']]
        self.assertEqual(ids, [self.rev1.id, self.rev2.id])  # 3 dann 5
