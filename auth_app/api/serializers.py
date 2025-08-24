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
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    repeated_password = serializers.CharField(write_only=True, min_length=8)
    type = serializers.ChoiceField(choices=Profile.TYPE_CHOICES)

    # Username-Check wie gehabt
    def validate_username(self, v):
        if User.objects.filter(username__iexact=v).exists():
            raise serializers.ValidationError("Username ist bereits vergeben.")
        return v

    # E-Mail: Format + (case-insensitive) Unique über deine Validatoren
    def validate_email(self, v):
        try:
            validate_email_format(v)
            # dein Helper prüft aktuell case-sensitive; wir gehen zusätzlich sicher:
            validate_email_unique(v)
            if User.objects.filter(email__iexact=v).exists():
                # Falls dein Helper "E-Mail" als Key liefert, normalisieren wir hier:
                raise serializers.ValidationError("E-Mail-Adresse wird bereits verwendet.")
        except DRFValidationError as e:
            # e.detail kann dict/list/string sein – wir mappen auf Feldfehler "email"
            if isinstance(e.detail, dict):
                msg = e.detail.get("email") or e.detail.get("E-Mail") or "Ungültige E-Mail-Adresse."
            else:
                msg = str(e.detail)
            raise serializers.ValidationError(msg)
        return v

    # Passwortstärke über deinen Helper (läuft als Field-Validator für "password")
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

    # Cross-field: Passwortgleichheit
    def validate(self, attrs):
        if attrs["password"] != attrs["repeated_password"]:
            raise serializers.ValidationError({"repeated_password": "Passwörter stimmen nicht überein."})
        return attrs

    def create(self, validated_data):
        pwd = validated_data.pop("password")
        validated_data.pop("repeated_password")
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=pwd,
        )
        Profile.objects.create(user=user, type=validated_data["type"])
        return user


class LoginSerializer(serializers.Serializer):
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