from django.contrib.auth.models import User  # Django-Usermodell importieren
from django.db import models  # Django-ORM-Basisklasse importieren
from django.utils import timezone  # liefert "jetzt" in TZ-aware

class Profile(models.Model):
    # mögliche Profil-Typen
    TYPE_CHOICES = (('customer', 'Customer'), ('business', 'Business'))

    # 1:1-Verknüpfung zum User, bei User-Löschung auch Profil löschen
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    # 'customer' oder 'business'
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    # OPTIONAL-Felder (dürfen in der DB leer sein, API macht daraus '' bei GET)
    file = models.ImageField(upload_to='profiles/', blank=True, null=True)        # Profilbild (Datei)
    location = models.CharField(max_length=255, blank=True, null=True)            # Ort/Stadt
    tel = models.CharField(max_length=50, blank=True, null=True)                  # Telefonnummer
    description = models.TextField(blank=True, null=True)                         # Beschreibung
    working_hours = models.CharField(max_length=100, blank=True, null=True)       # Arbeitszeiten

    # Erstellzeitpunkt des Profils
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # hilfreiche String-Repräsentation im Admin
        return f'{self.user.username} ({self.type})'


# from django.contrib.auth.models import User
# from django.db import models

# class Profile(models.Model):
#     TYPE_CHOICES = (("customer", "Customer"), ("business", "Business"))
#     user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
#     type = models.CharField(max_length=20, choices=TYPE_CHOICES)

#     def __str__(self):
#         return f"{self.user.username} ({self.type})"