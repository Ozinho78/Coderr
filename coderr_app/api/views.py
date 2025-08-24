from rest_framework.generics import RetrieveUpdateAPIView  # DRF-Generic für GET+PATCH
from rest_framework.permissions import IsAuthenticated  # Auth-Pflicht
from rest_framework.response import Response  # HTTP-Antwort
from rest_framework import status  # Statuscodes
from django.shortcuts import get_object_or_404  # 404-Helfer
from auth_app.models import Profile  # Profilmodell importieren
from .serializers import ProfileDetailSerializer  # Serializer von oben

class ProfileDetailView(RetrieveUpdateAPIView):
    # Serializer konfigurieren
    serializer_class = ProfileDetailSerializer
    # nur eingeloggte User dürfen zugreifen
    permission_classes = [IsAuthenticated]
    # Queryset, inkl. user für effiziente JOINs
    queryset = Profile.objects.select_related('user').all()
    # {pk} aus der URL
    lookup_field = 'pk'

    def get(self, request, *args, **kwargs):
        # GET liefert Profildetails
        try:
            # Profil anhand pk finden (404 bei Nichtfinden)
            profile = get_object_or_404(self.get_queryset(), pk=kwargs.get(self.lookup_field))
            # serialisieren
            serializer = self.get_serializer(profile)
            # 200 OK mit Daten
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            # Unerwarteter Fehler → 500
            return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, *args, **kwargs):
        # PATCH erlaubt partielles Update
        try:
            # Zielprofil laden
            profile = get_object_or_404(self.get_queryset(), pk=kwargs.get(self.lookup_field))
            # Serializer mit partial=True
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            # validieren (wirft 400 bei Fehlern)
            serializer.is_valid(raise_exception=True)
            # speichern (inkl. User-Felder)
            serializer.save()
            # aktualisierte Daten zurück
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception:
            # Fallback 500 (ValidationError handled DRF-üblich mit 400)
            return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
