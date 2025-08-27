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
    # Detail-Variante (z. B. Paket/Option) gehört zu einem Offer
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='details')  # FK → Offer

    # Preis und Lieferzeit (in Tagen)
    price = models.DecimalField(max_digits=10, decimal_places=2)  # Geldbetrag
    delivery_time = models.PositiveIntegerField(help_text='Lieferzeit in Tagen')  # z. B. 7

    # optional: Name/Bezeichnung dieser Option (Basic/Standard/Pro) – nicht zwingend für den Endpoint
    name = models.CharField(max_length=120, blank=True)  # darf leer sein

    def __str__(self):
        # lesbare Darstellung
        return f'OfferDetail #{self.pk} of Offer #{self.offer_id} (price={self.price}, days={self.delivery_time})'
