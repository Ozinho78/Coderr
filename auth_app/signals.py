from django.contrib.auth.models import User  # Sender des Signals (User wird erstellt)
from django.db.models.signals import post_save  # Signal nach dem Speichern
from django.dispatch import receiver  # dekoriert die Handler-Funktion
from auth_app.models import Profile  # unser Profilmodell

@receiver(post_save, sender=User)  # registriert Handler für User.post_save
def create_profile_for_user(sender, instance, created, **kwargs):
    # wird aufgerufen, wenn ein User gespeichert wurde
    if not created:
        return  # nur beim erstmaligen Anlegen reagieren

    # existiert bereits ein Profil? (z. B. falls anderswo angelegt)
    if hasattr(instance, 'profile'):
        return  # nichts tun, Profil ist schon da

    # neues Profil anlegen; 'type' kannst du hier mit Default setzen
    Profile.objects.create(
        user=instance,  # verknüpft mit dem neuen User
        type='customer'  # sinnvoller Default; falls Business per Admin, dort später ändern
    )
