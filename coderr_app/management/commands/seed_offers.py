from decimal import Decimal  # Geldwerte
from django.core.management.base import BaseCommand  # Basis für Commands
from django.db import transaction  # atomar
from auth_app.models import Profile  # Business-Profile
from coderr_app.models import Offer, OfferDetail  # Offer-Modelle

class Command(BaseCommand):
    help = 'Erzeugt Beispiel-Offers (1-3) für alle Business-Profile inkl. OfferDetails.'

    def add_arguments(self, parser):
        # optionaler Parameter: wie viele Offers pro User
        parser.add_argument('--max', type=int, default=3, help='Max Offers pro Business-User (1-3)')

    @transaction.atomic
    def handle(self, *args, **options):
        # Templates für Offers
        offer_templates = [
            {
                'title': 'Website Design',
                'description': 'Professionelles Webdesign inkl. responsivem Layout und Grund-SEO.',
                'details': [(Decimal('100.00'), 7), (Decimal('250.00'), 14), (Decimal('500.00'), 21)],
            },
            {
                'title': 'API Entwicklung',
                'description': 'Robuste REST-APIs mit Django REST Framework inkl. Tests.',
                'details': [(Decimal('150.00'), 5), (Decimal('300.00'), 10), (Decimal('600.00'), 20)],
            },
            {
                'title': 'Bugfix Paket',
                'description': 'Schnelle Fehlerbehebung und Code-Refactoring nach Bedarf.',
                'details': [(Decimal('80.00'), 3), (Decimal('180.00'), 7), (Decimal('350.00'), 14)],
            },
        ]

        # Parameter lesen
        max_offers = max(1, min(int(options['max']), 3))

        # Business-User holen
        business_profiles = Profile.objects.filter(type='business').select_related('user')

        created_offers = 0
        created_details = 0

        # Für jeden Business-User Offers + Details anlegen
        for prof in business_profiles:
            user = prof.user
            for idx, tpl in enumerate(offer_templates[:max_offers], start=1):
                title = f'{tpl["title"]} #{user.id}-{idx}'
                offer, created = Offer.objects.get_or_create(
                    user=user,
                    title=title,
                    defaults={'description': tpl['description']}
                )
                if created:
                    created_offers += 1

                for i, (price, days) in enumerate(tpl['details'], start=1):
                    name = ['Basic', 'Standard', 'Pro'][i-1]
                    detail, d_created = OfferDetail.objects.get_or_create(
                        offer=offer,
                        name=name,
                        defaults={'price': price, 'delivery_time': days}
                    )
                    if d_created:
                        created_details += 1

        # Abschlussmeldung in der Konsole
        self.stdout.write(self.style.SUCCESS(
            f'Fertig: {created_offers} Offers und {created_details} OfferDetails angelegt.'
        ))
