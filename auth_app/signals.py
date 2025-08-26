from django.contrib.auth.models import User                         # User ist der Sender des Signals
from django.db.models.signals import post_save                      # feuert nach dem Speichern
from django.dispatch import receiver                                # dekoriert die Handler-Funktion
from auth_app.models import Profile                                 # dein Profilmodell                 # :contentReference[oaicite:3]{index=3}

# Faker für fallback-Namen
try:
    from faker import Faker
except ImportError:
    Faker = None                                                    # falls nicht installiert, skip Fakes

def _guess_names_from_identity(username: str, email: str):
    """
    Versucht, Vor-/Nachnamen aus E-Mail/Username zu erraten:
    - local part der E-Mail splitten (., _, -)
    - alles alphanumerisch machen, 'familie' o. ä. ignorieren
    - Title-Case zurückgeben
    """
    import re
    local = (email or '').split('@')[0]
    candidates = [username or '', local]
    # Split an ., _, -, Zahlen entfernen
    parts = []
    for c in candidates:
        tokens = re.split(r'[._\-]+', c)
        for t in tokens:
            t = re.sub(r'\d+', '', t)                               # Zahlen streichen
            t = re.sub(r'[^A-Za-zÀ-ÿ]', '', t)                      # Sonderzeichen raus (Umlaute erlaubt)
            if t and t.lower() not in {'user', 'kunde', 'familie', 'customer', 'business'}:
                parts.append(t)
    # Heuristik: erstes Teil = Vorname, letztes Teil = Nachname
    first = parts[0].title() if parts else ''
    last = parts[-1].title() if len(parts) > 1 else ''
    return first, last

def _faker_by_email(email: str):
    """
    Wählt eine passende Faker-Locale anhand der Domain (einfacher Heuristik).
    """
    if not Faker:
        return None
    e = email.lower() if email else ''
    if any(d in e for d in ['.de', 't-online.de', 'web.de', 'gmx.de', 'outlook.de']):
        return Faker('de_DE')
    if any(d in e for d in ['.es', 'yahoo.es', 'hotmail.es', 'outlook.es']):
        return Faker('es_ES')
    return Faker('en_GB')

@receiver(post_save, sender=User)                                   # Handler für User.post_save
def create_profile_for_user(sender, instance, created, **kwargs):
    # nur beim erstmaligen Anlegen reagieren
    if not created:
        return

    # Profil sicherstellen (wie bisher): Default customer
    if not hasattr(instance, 'profile'):
        Profile.objects.create(user=instance, type='customer')      # Default-Typ setzen                 # :contentReference[oaicite:4]{index=4}

    # --- NEU: fehlende Namen freundlich füllen (einmalig) ---
    fn = (instance.first_name or '').strip()
    ln = (instance.last_name or '').strip()
    if not fn or not ln:
        # 1) Versuch: aus E-Mail/Username ableiten
        guess_fn, guess_ln = _guess_names_from_identity(instance.username or '', instance.email or '')
        # 2) Fallback: Faker (Locale anhand Domain)
        if (not guess_fn or not guess_ln) and Faker:
            f = _faker_by_email(instance.email)
            if f:
                if not guess_fn:
                    guess_fn = f.first_name()
                if not guess_ln:
                    guess_ln = f.last_name()
        # final setzen, wenn etwas bestimmt werden konnte
        changed = False
        if not fn and guess_fn:
            instance.first_name = guess_fn
            changed = True
        if not ln and guess_ln:
            instance.last_name = guess_ln
            changed = True
        if changed:
            instance.save(update_fields=['first_name', 'last_name'])
