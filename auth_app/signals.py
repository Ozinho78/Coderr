from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from auth_app.models import Profile


try:
    from faker import Faker # type: ignore
except ImportError:
    Faker = None

def _guess_names_from_identity(username: str, email: str):
    """Tries to determine the name with given username"""
    import re
    local = (email or '').split('@')[0]
    candidates = [username or '', local]
    # Split an ., _, -, Zahlen entfernen
    parts = []
    for c in candidates:
        tokens = re.split(r'[._\-]+', c)
        for t in tokens:
            t = re.sub(r'\d+', '', t)
            t = re.sub(r'[^A-Za-zÀ-ÿ]', '', t)
            if t and t.lower() not in {'user', 'kunde', 'familie', 'customer', 'business'}:
                parts.append(t)

    first = parts[0].title() if parts else ''
    last = parts[-1].title() if len(parts) > 1 else ''
    return first, last

def _faker_by_email(email: str):
    """Chooses a Faker-Locale looking at the domain"""
    if not Faker:
        return None
    e = email.lower() if email else ''
    if any(d in e for d in ['.de', 't-online.de', 'web.de', 'gmx.de', 'outlook.de']):
        return Faker('de_DE')
    if any(d in e for d in ['.es', 'yahoo.es', 'hotmail.es', 'outlook.es']):
        return Faker('es_ES')
    return Faker('en_GB')

@receiver(post_save, sender=User)
def create_profile_for_user(sender, instance, created, **kwargs):
    """Creates user profile"""

    if not created:
        return

    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance, type='customer')
