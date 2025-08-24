from rest_framework import serializers
from django.contrib.auth import get_user_model
from auth_app.models import Profile
import os

User = get_user_model()

class ProfileDetailSerializer(serializers.ModelSerializer):
    # SerializerMethodField, um Werte aus dem User-Modell einzubinden
    username = serializers.SerializerMethodField()  # liest username aus User
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)  # mappt auf user.first_name
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)  # mappt auf user.last_name
    email = serializers.SerializerMethodField()  # liest email aus User
    user = serializers.PrimaryKeyRelatedField(read_only=True)  # gibt die User-ID zurück, schreibgeschützt
    created_at = serializers.DateTimeField(read_only=True)  # wird nur gelesen
    type = serializers.CharField(read_only=True)  # Typ darf nicht per PATCH geändert werden
    file = serializers.SerializerMethodField()  # wir geben nur den Dateinamen (wie im Beispiel) zurück

    class Meta:
        model = Profile  # Basis ist das Profile-Modell
        # Felder laut Vorgabe + gewünschte User-Felder
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file',
            'location', 'tel', 'description', 'working_hours',
            'type', 'email', 'created_at',
        )
        # Diese Felder dürfen per PATCH geändert werden (User-Namen + Profilfelder, aber kein type/email/username/created_at)
        extra_kwargs = {
            'location': {'required': False, 'allow_blank': True},
            'tel': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'working_hours': {'required': False, 'allow_blank': True},
        }

    # ---------- Getter für User-bezogene Felder ----------

    def get_username(self, obj):
        # gibt den Username aus dem verknüpften User zurück
        return obj.user.username if obj.user and obj.user.username else ''

    def get_email(self, obj):
        # gibt die E-Mail aus dem verknüpften User zurück
        return obj.user.email if obj.user and obj.user.email else ''

    def get_file(self, obj):
        # Erwartung laut Beispiel: nur Dateiname (nicht URL); bei None -> ''
        if not obj.file:
            return ''
        # Wenn 'file' ein FileField/ImageField ist, hat es .name (Pfad) -> basename
        try:
            return os.path.basename(obj.file.name)
        except Exception:
            # falls 'file' ein Stringfeld ist
            return str(obj.file) or ''

    # ---------- Null-zu-'' in der Response für bestimmte Felder ----------

    def to_representation(self, instance):
        # holt die Standard-Repräsentation
        data = super().to_representation(instance)
        # Felder, die niemals null sein dürfen (-> leere Strings)
        must_not_be_null = ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']
        for key in must_not_be_null:
            # falls Key fehlt oder None ist -> ''
            if data.get(key) is None:
                data[key] = ''
            # falls es sich bei first/last_name um verschachtelte Quellen handelt, sicherstellen, dass String rauskommt
            if data.get(key) is False:  # edge case: falsy, aber nicht None
                data[key] = ''
        return data

    # ---------- Update-Logik für PATCH (User + Profile) ----------

    def update(self, instance, validated_data):
        # 'validated_data' kann 'user' enthalten (wegen source='user.first_name')
        user_data = validated_data.pop('user', {}) if 'user' in validated_data else {}

        # Profilfelder aktualisieren (nur die, die im PATCH gesendet wurden)
        for field in ['location', 'tel', 'description', 'working_hours', 'file']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        # Userfelder aktualisieren (first_name/last_name)
        if user_data:
            if 'first_name' in user_data:
                instance.user.first_name = user_data['first_name'] or ''
            if 'last_name' in user_data:
                instance.user.last_name = user_data['last_name'] or ''
            instance.user.save()  # speichert Änderungen am User

        instance.save()  # speichert Änderungen am Profile
        return instance  # gibt aktualisiertes Objekt zurück