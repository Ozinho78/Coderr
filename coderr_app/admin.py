from django.contrib import admin  # Admin-Registrierung & Basisklassen
from django.db.models import Min  # Aggregat-Funktion für min()
from django.utils.html import format_html  # sichere HTML-Ausgabe (Link zum User)
from coderr_app.models import Offer, OfferDetail, Order  # unsere Modelle



class OfferDetailInline(admin.TabularInline):
    # Inline-Tabelle für OfferDetail, erscheint im Offer-Detail als "extra Bereich"
    model = OfferDetail  # referenziertes Modell
    extra = 0  # keine leeren Zusatzzeilen standardmäßig
    fields = ('name', 'price', 'delivery_time')  # sichtbare Spalten im Inline
    readonly_fields = ()  # alle Felder editierbar (kannst du anpassen)
    show_change_link = True  # Link zur Detailseite des OfferDetail anzeigen

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    # Darstellung der Offer-Liste & Detailansicht konfigurieren

    # Spalten in der Listenansicht
    list_display = (
        'id',  # Primärschlüssel
        'creator_username',  # Username des Erstellers (User)
        'title',  # Titel des Angebots
        'get_min_price',  # aggregierter Minimalpreis
        'get_min_delivery_time',  # aggregierte minimale Lieferzeit
        'updated_at',  # zuletzt aktualisiert (für Sortierung hilfreich)
        'created_at',  # erstellt am
    )

    # Spalten, über die die Liste sortiert werden kann (default)
    ordering = ('-updated_at',)  # neueste zuerst

    # Welche Relationen gleich mitgeladen werden (Performance)
    list_select_related = ('user',)  # user direkt joinen

    # Suchfelder oben in der Liste
    search_fields = (
        'title',  # Suche im Titel
        'description',  # Suche in der Beschreibung
        'user__username',  # Suche im Username des Creators
        'user__first_name',  # Vorname des Creators
        'user__last_name',  # Nachname des Creators
    )

    # Filter rechts in der Seitenleiste
    list_filter = (
        'created_at',  # nach Erstellungsdatum filtern
        'updated_at',  # nach Änderungsdatum filtern
    )

    # Inline-Bereich für OfferDetails einbinden
    inlines = [OfferDetailInline]  # zeigt OfferDetail als "extra Bereich" an

    # Felder, die im Detail readonly sein sollen
    readonly_fields = (
        'created_at',  # Timestamps nicht editierbar
        'updated_at',
        'min_price',  # aggregierte Werte nur lesbar
        'min_delivery_time',
        'creator_link',  # schöner Link zum User im Admin
        'user_username',  # Creator-Infos als readonly Kopie
        'user_first_name',
        'user_last_name',
    )

    # Gruppiere Felder in Abschnitte (fieldsets)
    fieldsets = (
        ('Angebot', {  # Hauptdaten des Offers
            'fields': ('user', 'title', 'image', 'description')
        }),
        ('Aggregierte Werte', {  # eigener Bereich für min-Werte
            'fields': ('min_price', 'min_delivery_time'),
            'classes': ('collapse',),  # einklappbar für Übersicht
        }),
        ('Creator', {  # eigener Bereich mit Creator-Infos + Link
            'fields': ('creator_link', 'user_username', 'user_first_name', 'user_last_name'),
        }),
        ('System', {  # Systemfelder (nur lesen)
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def get_queryset(self, request):
        # Queryset für die Liste/Detailansicht — mit Annotationen & Joins
        qs = super().get_queryset(request)  # Basismethode aufrufen
        qs = qs.select_related('user')  # User joinen (weniger DB-Queries)
        qs = qs.annotate(  # aggregierte Felder vorab berechnen
            _min_price=Min('details__price'),  # min Preis aus OfferDetail
            _min_delivery_time=Min('details__delivery_time'),  # min Lieferzeit
        )
        return qs  # annotiertes Queryset zurückgeben

    # ---------- Spalten/Attribute für die Liste ----------

    def creator_username(self, obj):
        # Username des zugeordneten Users anzeigen
        return obj.user.username if obj.user_id else '-'
    creator_username.short_description = 'Creator'  # Spaltenüberschrift
    creator_username.admin_order_field = 'user__username'  # sortierbar nach Username

    def get_min_price(self, obj):
        # Aggregat aus get_queryset() nutzen (fällt auf None zurück)
        return obj._min_price
    get_min_price.short_description = 'min_price'  # Spaltenname wie im API-Response
    get_min_price.admin_order_field = '_min_price'  # sortierbar nach Annotation

    def get_min_delivery_time(self, obj):
        # Aggregat aus get_queryset() nutzen
        return obj._min_delivery_time
    get_min_delivery_time.short_description = 'min_delivery_time'  # Spaltenname
    get_min_delivery_time.admin_order_field = '_min_delivery_time'  # sortierbar

    # ---------- Readonly-Felder in der Detailansicht ----------

    def min_price(self, obj):
        # selbe Annotation auch in der Detailansicht verfügbar machen
        # Hinweis: bei neuem (ungespeicherten) Objekt gibt es noch keine Details → None
        return getattr(obj, '_min_price', None)
    min_price.short_description = 'min_price'  # Label im Formular

    def min_delivery_time(self, obj):
        # minimale Lieferzeit im Formularbereich anzeigen
        return getattr(obj, '_min_delivery_time', None)
    min_delivery_time.short_description = 'min_delivery_time'

    def creator_link(self, obj):
        # klickbarer Link zum zugehörigen User im Admin
        if not obj.user_id:
            return '-'
        # Standard-URL zum User-Change im Admin (auth.User anpassen, falls Custom-App)
        return format_html(
            '<a href="/admin/auth/user/{}/change/">{}</a>',
            obj.user_id,
            obj.user.username
        )
    creator_link.short_description = 'Creator (Link)'

    # Die folgenden Felder zeigen Creator-Daten im schreibgeschützten Bereich
    def user_username(self, obj):
        return obj.user.username if obj.user_id else ''
    user_username.short_description = 'username'

    def user_first_name(self, obj):
        return obj.user.first_name if obj.user_id else ''
    user_first_name.short_description = 'first_name'

    def user_last_name(self, obj):
        return obj.user.last_name if obj.user_id else ''
    user_last_name.short_description = 'last_name'


@admin.register(OfferDetail)
class OfferDetailAdmin(admin.ModelAdmin):
    # Optional: separates Admin für OfferDetail (praktisch bei direkter Suche)
    list_display = ('id', 'offer', 'name', 'price', 'delivery_time')  # Spalten in der Liste
    list_select_related = ('offer', 'offer__user')  # Offer & User joinen
    search_fields = (
        'name',  # Name der Option
        'offer__title',  # Titel des zugehörigen Offers
        'offer__user__username',  # Creator-Username
    )
    list_filter = ('delivery_time',)  # schneller Filter auf Lieferzeit
    ordering = ('offer_id', 'id')  # stabile Sortierung


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'customer_user', 'business_user', 'status', 'created_at')
    list_filter = ('status', 'offer_type', 'created_at')
    search_fields = ('title', 'customer_user__username', 'business_user__username')