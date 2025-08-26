from django.contrib import admin                              # Admin-Framework importieren
from django.contrib.auth.models import User                   # User-Modell
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin  # Standard-UserAdmin-Basisklasse
from .models import Profile                                   # dein Profilmodell (Customer/Business)  # :contentReference[oaicite:0]{index=0}


class ProfileInline(admin.StackedInline):
    model = Profile                                           # zeigt das Profil inline beim User
    can_delete = False                                        # Inline nicht separat löschbar
    verbose_name_plural = 'Profile'                           # schöner Titel


class UserAdmin(BaseUserAdmin):
    inlines = (ProfileInline,)                                # Profil im User-Detail anzeigen
    # zusätzliche Spalten: Profil-Typ, Vorname, Nachname, Vollname mit Fallbacks
    list_display = BaseUserAdmin.list_display + ('get_profile_type', 'get_fullname_fallback')
    list_select_related = ('profile',)                        # effizient: Profil via JOIN laden
    list_filter = BaseUserAdmin.list_filter + ('profile__type',)  # Filter Customer/Business im User-Admin

    def get_profile_type(self, obj):
        # liest den Profiltyp (customer/business), falls Profil existiert
        return getattr(obj.profile, 'type', '-')
    get_profile_type.short_description = 'Profil-Typ'         # Spaltentitel

    def get_fullname_fallback(self, obj):
        # Komfortspalte: zeigt "Vorname Nachname", fällt auf Username zurück
        fn = (obj.first_name or '').strip()
        ln = (obj.last_name or '').strip()
        full = f'{fn} {ln}'.strip()
        return full if full else obj.username
    get_fullname_fallback.short_description = 'Voller Name'      # Spaltentitel

# Standard-Registrierung ersetzen durch unsere erweiterte
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # sinnvolle Übersicht im Profil-Admin
    list_display = ('user', 'type', 'location', 'tel')
    search_fields = ('user__username', 'user__email', 'location')
    list_filter = ('type',)
