from rest_framework import serializers  # DRF-Serializer-Basis
from django.contrib.auth import get_user_model  # kompatibel auch für CustomUser
from auth_app.models import Profile  # unser Profilmodell (aus auth_app)
import os  # für Dateinamen von file
from coderr_app.models import Offer, OfferDetail  # unsere neuen Modelle

User = get_user_model()  # Referenz auf das Usermodell

class ProfileDetailSerializer(serializers.ModelSerializer):
    # Felder aus dem User zusammensetzen
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # User-ID schreibgeschützt
    username = serializers.SerializerMethodField()  # Username aus user

    # >>> NEU: email schreibbar machen (kommt aus user.email)
    email = serializers.EmailField(source='user.email', required=False)  # PATCH erlaubt

    # first_name/last_name kommen aus user.*, sind PATCH-bar
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)  # mapping auf user
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)   # mapping auf user

    # file als einfacher Dateiname (wie im Beispiel)
    file = serializers.SerializerMethodField()  # gibt basename oder '' zurück

    class Meta:
        model = Profile  # Basis ist das Profil
        # Felder laut Vorgabe (User+Profil kombiniert)
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file',
            'location', 'tel', 'description', 'working_hours',
            'type', 'email', 'created_at',
        )
        # Profilfelder sind optional beim PATCH
        extra_kwargs = {
            'location': {'required': False, 'allow_blank': True},
            'tel': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'working_hours': {'required': False, 'allow_blank': True},
        }

    # ---------- Getter aus User ----------
    def get_username(self, obj):
        # Username aus verknüpftem User oder ''
        return obj.user.username if getattr(obj, 'user', None) and obj.user.username else ''

    # ---------- file (nur Dateiname) ----------
    def get_file(self, obj):
        # Wenn kein Bild gesetzt ist -> ''
        if not obj.file:
            return ''
        # Bei File/ImageField .name -> basename
        try:
            return os.path.basename(obj.file.name)
        except Exception:
            # falls doch Stringfeld
            return str(obj.file) or ''

    # ---------- Null-zu-Leerstring ----------
    def to_representation(self, instance):
        # Standard-Serialisierung abrufen
        data = super().to_representation(instance)
        # diese Felder dürfen nie null in der Response sein
        must_not_be_null = ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']
        for key in must_not_be_null:
            # None → ''
            if data.get(key) is None:
                data[key] = ''
        return data

    # ---------- PATCH: User- + Profilfelder speichern ----------
    def update(self, instance, validated_data):
        # 'user' kann wegen source='user.first_name' / 'user.email' im validated_data liegen
        user_data = validated_data.pop('user', {}) if 'user' in validated_data else {}

        # Profilfelder selektiv übernehmen
        for field in ['location', 'tel', 'description', 'working_hours', 'file']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Userfelder (first_name/last_name/email) übernehmen
        if user_data:
            if 'first_name' in user_data:
                instance.user.first_name = user_data['first_name'] or ''
            if 'last_name' in user_data:
                instance.user.last_name = user_data['last_name'] or ''
            if 'email' in user_data:
                instance.user.email = user_data['email']  # EmailField validiert bereits
            instance.user.save()  # User speichern

        instance.save()  # Profil speichern
        return instance  # aktualisiertes Objekt zurückgeben


class ProfileListSerializer(serializers.ModelSerializer):   # List-Ansicht: reduzierte Felder
    user = serializers.PrimaryKeyRelatedField(read_only=True)          # zeigt die User-ID
    username = serializers.SerializerMethodField()                     # aus user.username
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)  # nie null im Response
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)    # nie null im Response
    file = serializers.SerializerMethodField()                          # nur Dateiname, kein URL

    class Meta:
        model = Profile
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file',
            'location', 'tel', 'description', 'working_hours',
            'type',
        )                                                               # genau die Felder aus der Vorgabe

        # Alle optionalen Textfelder beim PATCH irrelevant – hier nur GET, aber so sind sie definiert
        extra_kwargs = {
            'location': {'required': False, 'allow_blank': True},
            'tel': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'working_hours': {'required': False, 'allow_blank': True},
        }

    def get_username(self, obj):
        return obj.user.username if getattr(obj, 'user', None) else ''  # '' falls kein User gesetzt (Sicherheitsnetz)

    def get_file(self, obj):
        if not obj.file:
            return ''                                                   # kein Bild → leerer String
        try:
            return os.path.basename(obj.file.name)                      # nur der Dateiname
        except Exception:
            return str(obj.file) or ''                                  # Fallback

    def to_representation(self, instance):
        data = super().to_representation(instance)                       # Standardrepräsentation
        # Diese Felder dürfen im Response NICHT null sein → zu '' wandeln
        for key in ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']:
            if data.get(key) is None:
                data[key] = ''
        return data
    
    
class OfferDetailMiniSerializer(serializers.ModelSerializer):
    # schlanke Darstellung für die Offer-Liste (id + url)
    url = serializers.SerializerMethodField()  # baut eine relative URL wie '/offerdetails/1/'

    class Meta:
        model = OfferDetail  # Basis
        fields = ('id', 'url')  # nur id + url

    def get_url(self, obj):
        # einfache relative URL wie im Beispiel gefordert
        return f'/offerdetails/{obj.pk}/'  # Hinweis: kein DRF reverse, exakt wie Beispiel

class OfferListSerializer(serializers.ModelSerializer):
    # Detail-IDs + URLs
    details = OfferDetailMiniSerializer(many=True, read_only=True)  # nutzt related_name='details'

    # Aggregierte Felder (per Queryset-Annotation geliefert)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)  # minimaler Preis
    min_delivery_time = serializers.IntegerField(read_only=True)  # minimaler Tagewert

    # Nutzerinfo kompakt
    user_details = serializers.SerializerMethodField()  # liefert first_name/last_name/username

    class Meta:
        model = Offer  # Basis ist Offer
        fields = (
            'id', 'user', 'title', 'image', 'description',
            'created_at', 'updated_at',
            'details',
            'min_price', 'min_delivery_time',
            'user_details',
        )  # exakt gemäß Response

    def get_user_details(self, obj):
        # liest Daten aus obj.user; leere Strings, falls nicht belegt
        u = getattr(obj, 'user', None)
        return {
            'first_name': (u.first_name or '') if u else '',
            'last_name': (u.last_name or '') if u else '',
            'username': (u.username or '') if u else '',
        }
        
        
# ------------------------------------------------------------
# <<< NEW: Serializer für ein einzelnes Detail im POST-Body
# ------------------------------------------------------------
class OfferDetailCreateSerializer(serializers.ModelSerializer):  # <<< NEW
    class Meta:
        model = OfferDetail
        fields = (
            'id',                      # Antwort enthält die erzeugte ID
            'title',                   # Titel des Pakets (Basic/Standard/Premium)
            'revisions',               # Anzahl der Revisionen
            'delivery_time_in_days',   # Lieferzeit in Tagen
            'price',                   # Preis
            'features',                # Liste von Strings
            'offer_type',              # 'basic' | 'standard' | 'premium'
        )

    def validate_features(self, value):  # kurze Typprüfung  # <<< NEW
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise serializers.ValidationError('features muss eine Liste aus Strings sein.')
        return value

    def validate(self, attrs):  # Werte-Checks  # <<< NEW
        if attrs.get('price') is None or float(attrs['price']) < 0:
            raise serializers.ValidationError({'price': 'Preis muss >= 0 sein.'})
        if attrs.get('delivery_time_in_days') in (None, ''):
            raise serializers.ValidationError({'delivery_time_in_days': 'Pflichtfeld.'})
        if attrs.get('offer_type') not in ('basic', 'standard', 'premium'):
            raise serializers.ValidationError({'offer_type': 'Ungültig (basic|standard|premium).'})
        return attrs


# ------------------------------------------------------------
# <<< NEW: Serializer für das gesamte Offer (inkl. 3 Details)
# ------------------------------------------------------------
class OfferCreateSerializer(serializers.ModelSerializer):  # <<< NEW
    details = OfferDetailCreateSerializer(many=True)  # genau 3 Details erwartet

    class Meta:
        model = Offer
        fields = ('id', 'title', 'image', 'description', 'details')

    def validate_details(self, value):  # genau 3 und je 1x basic/standard/premium  # <<< NEW
        if not isinstance(value, list) or len(value) != 3:
            raise serializers.ValidationError('Ein Offer muss genau 3 Details enthalten.')
        types = [d.get('offer_type') for d in value]
        if set(types) != {'basic', 'standard', 'premium'}:
            raise serializers.ValidationError('Die 3 Details müssen basic, standard und premium enthalten (jeweils einmal).')
        return value

    def create(self, validated_data):  # Offer + Details in einem Rutsch  # <<< NEW
        request = self.context.get('request')  # User aus Request
        user = getattr(request, 'user', None)
        details_data = validated_data.pop('details')  # Details abtrennen

        # Offer erstellen (Creator = eingeloggter User)
        offer = Offer.objects.create(user=user, **validated_data)

        # 3 Detail-Objekte vorbereiten
        objs = []
        for d in details_data:
            # <<< CHANGE: wir spiegeln delivery_time_in_days -> delivery_time (Legacy-Feld)
            dt_days = d.get('delivery_time_in_days')
            objs.append(OfferDetail(
                offer=offer,
                title=d.get('title'),
                revisions=d.get('revisions', 0),
                delivery_time_in_days=dt_days,
                delivery_time=dt_days,                # <<< NEW: wichtig für NOT NULL-Schema
                price=d.get('price'),
                features=d.get('features', []),
                offer_type=d.get('offer_type'),
            ))
        # effizient speichern
        OfferDetail.objects.bulk_create(objs)
        # aktualisieren (IDs/Relationen)
        offer.refresh_from_db()
        return offer
    
  
# In deiner Liste (OfferListSerializer) nutzt du bewusst relative Detail-URLs (/offerdetails/<id>/). Für den Detail-Endpoint verlangt die Spezifikation absolute URLs. Darum trenne ich das sauber in OfferDetailMiniAbsSerializer und OfferRetrieveSerializer, ohne das Listen-Verhalten zu ändern.  
# ------------------------------------------------------------
# <<< NEW: Mini-Serializer mit ABSOLUTER URL (für GET /offers/{id}/)
# ------------------------------------------------------------
class OfferDetailMiniAbsSerializer(serializers.ModelSerializer):          # kompaktes Detailobjekt (id + absolute URL)
    url = serializers.SerializerMethodField()                             # URL wird dynamisch aus request gebaut

    class Meta:
        model = OfferDetail                                              # Quelle: OfferDetail-Modell
        fields = ('id', 'url')                                           # nur id + url (wie Anforderung)

    def get_url(self, obj):                                              # baut 'http://127.0.0.1:8000/api/offerdetails/<id>/'
        request = self.context.get('request')                            # request ist nötig für absolute URL
        path = f'/api/offerdetails/{obj.pk}/'                            # API-Pfad gemäß Frontend-Konstanten (config.js)
        return request.build_absolute_uri(path) if request else path     # fallback: relative URL, falls kein request vorhanden


# ------------------------------------------------------------
# <<< NEW: Serializer für EIN Angebot (GET /offers/{id}/)
# ------------------------------------------------------------
class OfferRetrieveSerializer(serializers.ModelSerializer):               # Ausgabeformat für Detail-Endpunkt
    details = OfferDetailMiniAbsSerializer(many=True, read_only=True)     # nutzt related_name='details' (siehe models)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)   # kommt per Annotation
    min_delivery_time = serializers.IntegerField(read_only=True)          # kommt per Annotation

    class Meta:
        model = Offer                                                    # Basis ist Offer
        fields = (
            'id', 'user', 'title', 'image', 'description',              # Felder 1:1 wie in der Anforderung
            'created_at', 'updated_at',
            'details', 'min_price', 'min_delivery_time',
        )


# ------------------------------------------------------------
# <<< NEW: Serializer für GET /api/offerdetails/{id}/
# ------------------------------------------------------------
# Dein OfferDetail-Modell enthält diese Felder bereits: title, revisions, delivery_time_in_days, price, features, offer_type. Siehe dein Modell:
class OfferDetailRetrieveSerializer(serializers.ModelSerializer):         # Einzel-Detail-Ausgabe
    # Alle Felder sind read_only, da es ein GET-Endpoint ist
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)  # Zahl, kein String

    class Meta:
        model = OfferDetail                                               # Quelle ist unser Detailmodell
        fields = (
            'id',                         # ID des Angebotsdetails
            'title',                      # Titel (z. B. "Basic Design")
            'revisions',                  # Anzahl der Revisionen
            'delivery_time_in_days',      # Lieferzeit in Tagen (neues Feld)
            'price',                      # Preis
            'features',                   # Liste von Features (Strings)
            'offer_type',                 # 'basic' | 'standard' | 'premium'
        )
        
