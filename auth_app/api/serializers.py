from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework import serializers
from rest_framework.exceptions import ValidationError as DRFValidationError
from auth_app.models import Profile
from core.utils.validators import (
    validate_email_format,
    validate_email_unique,
    validate_password_strength,
)



class RegistrationSerializer(serializers.Serializer):
    """Serializes registration data"""
    username = serializers.CharField(max_length=50)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    repeated_password = serializers.CharField(write_only=True, min_length=8)
    type = serializers.ChoiceField(choices=Profile.TYPE_CHOICES)

    # username check, matching with iexact (i=insensitive) to avoid multiple usernames with upper/lower chars
    def validate_username(self, v):
        if User.objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError("Username ist bereits vergeben.")
        return v

    # checks unique email address
    def validate_email(self, v):
        try:
            validate_email_format(v)
            validate_email_unique(v)
            if User.objects.filter(email__iexact=v).exists():
                raise serializers.ValidationError("E-Mail-Adresse wird bereits verwendet.")
        except DRFValidationError as e:
            # e.detail can be dict/list/string
            if isinstance(e.detail, dict):
                msg = e.detail.get("email") or e.detail.get("E-Mail") or "Ungültige E-Mail-Adresse."
            else:
                msg = str(e.detail)
            raise serializers.ValidationError(msg)
        return v

    # validates password strength
    def validate_password(self, v):
        try:
            validate_password_strength(v)
        except DRFValidationError as e:
            if isinstance(e.detail, dict):
                msg = e.detail.get("password") or "Ungültiges Passwort."
            else:
                msg = str(e.detail)
            raise serializers.ValidationError(msg)
        return v

    # checks equal passwords
    def validate(self, attrs):
        if attrs["password"] != attrs["repeated_password"]:
            raise serializers.ValidationError({"repeated_password": "Passwörter stimmen nicht überein."})
        return attrs

    def create(self, validated_data):
        pwd = validated_data.pop('password')                 # Passwort entnehmen
        validated_data.pop('repeated_password')              # Wiederholung entfernen
        desired_type = validated_data['type']                # gewünschter Profil-Typ merken

        # User anlegen (triggert post_save → Signal kann bereits ein Profil erzeugen)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=pwd,
        )

        # Profil sicherstellen, ohne Unique-Fehler zu riskieren:
        profile, _ = Profile.objects.get_or_create(user=user)

        # Typ auf gewünschten Wert setzen (alle anderen Felder bleiben leer)
        if profile.type != desired_type:
            profile.type = desired_type
            profile.save(update_fields=['type'])

        return user
    

class LoginSerializer(serializers.Serializer):
    """Serializes login data"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username")
        password = attrs.get("password")
        if not username or not password:
            raise serializers.ValidationError("Ungültige Anfragedaten.")
        user = authenticate(username=username, password=password)
        if not user:
            # absichtlich generisch (kein Leak, ob User existiert)
            raise serializers.ValidationError("Ungültige Anmeldedaten.")
        if not user.is_active:
            raise serializers.ValidationError("Konto ist deaktiviert.")
        attrs["user"] = user
        return attrs