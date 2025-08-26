from rest_framework import serializers  # DRF-Serializer-Basis
from django.contrib.auth import get_user_model  # kompatibel auch für CustomUser
from auth_app.models import Profile  # unser Profilmodell (aus auth_app)
import os  # für Dateinamen von file

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
    
    
