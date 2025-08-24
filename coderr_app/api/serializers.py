from rest_framework import serializers  # DRF-Serializer-Basis
from django.contrib.auth import get_user_model  # kompatibel auch für CustomUser
from auth_app.models import Profile  # unser Profilmodell (aus auth_app)
import os  # für Dateinamen von file

User = get_user_model()  # Referenz auf das Usermodell

class ProfileDetailSerializer(serializers.ModelSerializer):
    # Felder aus dem User zusammensetzen
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # User-ID schreibgeschützt
    username = serializers.SerializerMethodField()  # Username aus user
    email = serializers.SerializerMethodField()  # Email aus user

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

    def get_email(self, obj):
        # E-Mail aus verknüpftem User oder ''
        return obj.user.email if getattr(obj, 'user', None) and obj.user.email else ''

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
        # 'user' kann wegen source='user.first_name' im validated_data liegen
        user_data = validated_data.pop('user', {}) if 'user' in validated_data else {}

        # Profilfelder selektiv übernehmen
        for field in ['location', 'tel', 'description', 'working_hours', 'file']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Userfelder (first_name/last_name) übernehmen
        if user_data:
            if 'first_name' in user_data:
                instance.user.first_name = user_data['first_name'] or ''
            if 'last_name' in user_data:
                instance.user.last_name = user_data['last_name'] or ''
            instance.user.save()  # User speichern

        instance.save()  # Profil speichern
        return instance  # aktualisiertes Objekt zurückgeben
