"""Provides the two views for registration and authentication"""
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from auth_app.api.serializers import RegistrationSerializer, LoginSerializer


class RegistrationView(APIView):
    """Handles user registration and returns token and basic user info"""
    authentication_classes = []
    permission_classes = []

    @transaction.atomic
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.username,
                "email": user.email,
                "user_id": user.id,
            },
            status=status.HTTP_201_CREATED,
        )
            
            
class LoginView(APIView):
    """Authenticates a user and returns a token with basic user info"""
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": serializer.errors if isinstance(serializer.errors, dict) else str(serializer.errors)},
                            status=status.HTTP_400_BAD_REQUEST)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "username": user.username,
                "email": user.email,
                "user_id": user.id,
            },
            status=status.HTTP_200_OK,
        )