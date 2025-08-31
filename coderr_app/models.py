from django.db import models  # ORM-Basisklasse
from django.contrib.auth import get_user_model  # kompatibel mit Custom-User
from django.utils import timezone  # falls später benötigt (hier nicht zwingend)

User = get_user_model()  # Referenz auf aktives User-Modell

class Offer(models.Model):
    # Ersteller des Angebots (Business-Account), bei User-Löschung auch Angebot löschen
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')  # FK → User

    # Basisdaten des Angebots
    title = models.CharField(max_length=255)  # kurzer Titel
    image = models.ImageField(upload_to='offers/', blank=True, null=True)  # optionales Bild
    description = models.TextField(blank=True)  # längere Beschreibung, darf leer sein

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)  # beim Erstellen gesetzt
    updated_at = models.DateTimeField(auto_now=True)  # bei jeder Änderung aktualisiert

    def __str__(self):
        # lesbare Darstellung im Admin/Shell
        return f'Offer #{self.pk} by {self.user_id}: {self.title[:30]}'


class OfferDetail(models.Model):
    # vorhandene Felder (beibehalten für Kompatibilität)
    # Detail-Variante (z. B. Paket/Option) gehört zu einem Offer
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='details')  # FK → Offer
    # Preis und Lieferzeit (in Tagen)
    price = models.DecimalField(max_digits=10, decimal_places=2)                         # Preis (besteht schon)
    delivery_time = models.PositiveIntegerField(help_text='Lieferzeit in Tagen')         # ALT: legacy-Feld
    # optional: Name/Bezeichnung dieser Option (Basic/Standard/Pro) – nicht zwingend für den Endpoint
    name = models.CharField(max_length=120, blank=True)                                  # ALT: evtl. Paketname

    # NEU: Felder laut POST-Spezifikation
    title = models.CharField(max_length=255, blank=True, null=True)                      # Titel der Detail-Stufe
    revisions = models.PositiveIntegerField(default=0)                                    # Anzahl Revisionen
    delivery_time_in_days = models.PositiveIntegerField(blank=True, null=True)           # neue Lieferzeit (Tage)
    features = models.JSONField(default=list, blank=True, null=True)                     # Liste von Features
    offer_type = models.CharField(                                                       # basic/standard/premium
        max_length=20,
        choices=(('basic', 'Basic'), ('standard', 'Standard'), ('premium', 'Premium')),
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            # je Offer jeden offer_type höchstens einmal (nur wenn offer_type gesetzt ist)
            models.UniqueConstraint(
                fields=['offer', 'offer_type'],
                name='unique_offer_offer_type',
                condition=~models.Q(offer_type__isnull=True),
            ),
        ]

    def __str__(self):
        # lesbare Darstellung
        return f'OfferDetail #{self.pk} of Offer #{self.offer_id} (price={self.price}, days={self.delivery_time})'




# class Order(models.Model): definiert die DB-Tabelle.
# Zwei ForeignKey zeigen auf dein User-Modell: Kunde und Business.
# Die Felder title, revisions, delivery_time_in_days, price, features, offer_type spiegeln exakt die Struktur aus deiner Vorgabe.
# status hat sinnvolle Choices, Default ist 'in_progress' (wie im Beispiel).
# created_at / updated_at pflegen sich automatisch.
# __str__ hilft beim Debuggen.
# Falls du später eine Referenz zur konkreten Offer/OfferDetail-ID brauchst, kannst du optional offer = models.ForeignKey(Offer, ...) oder offer_detail = models.ForeignKey(OfferDetail, ...) ergänzen. Für GET /api/orders/ ist das nicht nötig.
class Order(models.Model):
    # Referenzen auf die beteiligten User
    customer_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_orders')  # Kunde (löscht Kunde -> löscht Bestellung)
    business_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_orders')  # Dienstleister (löscht Business -> löscht Bestellung)

    # Angebots-Metadaten (werden beim Kauf "eingefroren")
    title = models.CharField(max_length=255)                                 # Titel der gebuchten Option
    revisions = models.PositiveIntegerField(default=0)                        # zugesicherte Revisionen
    delivery_time_in_days = models.PositiveIntegerField()                     # Lieferzeit in Tagen
    price = models.DecimalField(max_digits=10, decimal_places=2)              # Preis zum Kaufzeitpunkt
    features = models.JSONField(default=list, blank=True, null=True)          # Feature-Liste (Strings)
    offer_type = models.CharField(                                           # Pakettyp gemäß Vorgabe
        max_length=20,
        choices=(('basic', 'Basic'), ('standard', 'Standard'), ('premium', 'Premium'))
    )

    # Status der Bestellung
    status = models.CharField(                                               # einfacher State-String
        max_length=30,
        choices=(
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('delivered', 'Delivered'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ),
        default='in_progress',
    )

    # Zeitstempel
    created_at = models.DateTimeField(auto_now_add=True)                      # beim Erstellen gesetzt
    updated_at = models.DateTimeField(auto_now=True)                          # bei jeder Änderung gesetzt

    def __str__(self):
        # lesbare Repräsentation im Admin/Shell
        return f'Order #{self.pk} ({self.title}) c={self.customer_user_id} b={self.business_user_id}'
    
    
# --- Reviews: Customer bewertet Business --------------------------------------
class Review(models.Model):
    # Wer wird bewertet? → Business-User (FK auf User)
    business_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')  # Business, der bewertet wird
    # Wer bewertet? → Reviewer (FK auf User)
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='written_reviews')        # Customer, der bewertet
    # 1..5 Sterne
    rating = models.PositiveSmallIntegerField()                                                         # int 1..5, validieren im Serializer
    # Freitext
    description = models.TextField(blank=True)                                                          # optionaler Text
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)                                                # gesetzt beim Erstellen
    updated_at = models.DateTimeField(auto_now=True)                                                    # bei jeder Änderung

    class Meta:
        indexes = [
            models.Index(fields=['business_user']),                                                     # schneller filtern nach Business
            models.Index(fields=['reviewer']),                                                          # schneller filtern nach Reviewer
            models.Index(fields=['updated_at']),                                                        # schneller sortieren
            models.Index(fields=['rating']),                                                            # schneller sortieren
        ]

    def __str__(self):
        return f'Review #{self.pk} b={self.business_user_id} r={self.reviewer_id} rating={self.rating}'