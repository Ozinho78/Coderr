# python manage.py normalize_offerdetails --dry-run   # zeigt nur an
# python manage.py normalize_offerdetails             # schreibt Änderungen

from django.core.management.base import BaseCommand
from django.db import transaction
from coderr_app.models import OfferDetail

class Command(BaseCommand):
    help = 'Bereinigt ältere OfferDetail-Datensätze und setzt sinnvolle Defaults.'

    def add_arguments(self, parser):
        # optional: --dry-run um nur zu zählen, nichts zu speichern
        parser.add_argument('--dry-run', action='store_true', help='Nur anzeigen, nicht speichern')

    @transaction.atomic
    def handle(self, *args, **opts):
        dry = opts.get('dry_run', False)
        updated = 0

        # Alle OfferDetails iterieren
        for d in OfferDetail.objects.select_related('offer').all():
            # Flags, ob wir was ändern
            changed = False

            # Titel: bevorzugt vorhandenes title, sonst name, sonst 'Paket'
            if not d.title or not d.title.strip():
                fallback_title = d.name.strip() if (d.name and d.name.strip()) else 'Paket'
                d.title = fallback_title
                changed = True

            # offer_type: bevorzugt vorhandenes, sonst name.lower() oder 'basic'
            if not d.offer_type or not str(d.offer_type).strip():
                name_lower = (d.name or '').strip().lower()
                d.offer_type = name_lower if name_lower else 'basic'
                changed = True

            # delivery_time_in_days: bevorzugt vorhandenes, sonst altes delivery_time, sonst 0
            if not d.delivery_time_in_days:
                d.delivery_time_in_days = d.delivery_time or 0
                changed = True

            # revisions: Standard 0 falls None
            if d.revisions is None:
                d.revisions = 0
                changed = True

            # features: Standard [] falls None
            if d.features is None:
                d.features = []
                changed = True

            if changed:
                updated += 1
                if not dry:
                    d.save()

        # Ergebnis-Ausgabe
        if dry:
            self.stdout.write(self.style.WARNING(f'[DRY RUN] Würden {updated} OfferDetail(s) aktualisieren.'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Aktualisiert: {updated} OfferDetail(s).'))