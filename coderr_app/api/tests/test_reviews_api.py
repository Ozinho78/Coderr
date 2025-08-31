# python manage.py test coderr_app.api.tests.test_reviews_api
# pytest coderr_app/api/tests/test_reviews_api.py -q
from django.contrib.auth.models import User                 # User-Testobjekte
from django.test import TestCase                            # Django-Testbasis
from rest_framework.test import APIClient                   # DRF-Client
from django.utils import timezone                           # Zeitstempel
from auth_app.models import Profile                         # <<< KORREKT: Profile kommt aus auth_app
from coderr_app.models import Review                        # Review-Modell (coderr_app)

class ReviewApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()                           # Testclient

        # ---------- User + Profile anlegen (robust) ----------
        # Business-User (wird bewertet)
        self.business = User.objects.create_user(username='biz', password='x')
        Profile.objects.get_or_create(                      # <<< WICHTIG: unique user_id respektieren
            user=self.business,
            defaults={'type': 'business'}
        )

        # Zwei Customer-User (als Reviewer)
        self.cust1 = User.objects.create_user(username='c1', password='x')
        Profile.objects.get_or_create(user=self.cust1, defaults={'type': 'customer'})

        self.cust2 = User.objects.create_user(username='c2', password='x')
        Profile.objects.get_or_create(user=self.cust2, defaults={'type': 'customer'})

        # ---------- Zwei Reviews ----------
        self.rev1 = Review.objects.create(
            business_user=self.business,                   # Ziel: Business-User
            reviewer=self.cust1,                           # Rezensent: Customer 1
            rating=3,
            description='ok'
        )
        self.rev2 = Review.objects.create(
            business_user=self.business,
            reviewer=self.cust2,
            rating=5,
            description='top'
        )

        # updated_at so setzen, dass rev2 "neuer" ist
        Review.objects.filter(pk=self.rev1.pk).update(
            updated_at=timezone.now() - timezone.timedelta(days=1)
        )
        Review.objects.filter(pk=self.rev2.pk).update(updated_at=timezone.now())

        # irgendein eingeloggter User für Auth-Tests
        self.any_user = self.cust1

    def test_requires_authentication(self):
        # Ohne Auth → 401
        resp = self.client.get('/api/reviews/')
        self.assertEqual(resp.status_code, 401)

    def test_default_ordering_updated_at_desc(self):
        # Mit Auth → 200 + neueste zuerst (rev2)
        self.client.force_authenticate(user=self.any_user)
        resp = self.client.get('/api/reviews/')
        self.assertEqual(resp.status_code, 200)
        self.assertIsInstance(resp.data, list)             # flache Liste (keine Pagination)
        self.assertGreaterEqual(len(resp.data), 2)
        self.assertEqual(resp.data[0]['id'], self.rev2.id) # rev2 zuerst

    def test_filter_by_business_user_id(self):
        # Filter business_user_id → beide Reviews (rev1, rev2)
        self.client.force_authenticate(user=self.any_user)
        resp = self.client.get(f'/api/reviews/?business_user_id={self.business.id}')
        self.assertEqual(resp.status_code, 200)
        ids = [x['id'] for x in resp.data]
        self.assertCountEqual(ids, [self.rev1.id, self.rev2.id])

    def test_filter_by_reviewer_id(self):
        # Filter reviewer_id=cust1 → nur rev1
        self.client.force_authenticate(user=self.any_user)
        resp = self.client.get(f'/api/reviews/?reviewer_id={self.cust1.id}')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]['id'], self.rev1.id)

    def test_ordering_by_rating(self):
        # ordering=rating → aufsteigend: 3, dann 5 → rev1, rev2
        self.client.force_authenticate(user=self.any_user)
        resp = self.client.get('/api/reviews/?ordering=rating')
        self.assertEqual(resp.status_code, 200)
        ids = [x['id'] for x in resp.data]
        self.assertEqual(ids, [self.rev1.id, self.rev2.id])
