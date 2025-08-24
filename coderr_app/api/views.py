from rest_framework.generics import RetrieveUpdateAPIView  # GenericView für GET + PATCH
from rest_framework.permissions import IsAuthenticated  # Auth-Pflicht
from rest_framework.response import Response  # für eventuelle Custom-Responses
from rest_framework import status  # HTTP-Statuscodes
from django.shortcuts import get_object_or_404  # 404-Helfer
from auth_app.models import Profile
from coderr_app.api.serializers import ProfileDetailSerializer  # der oben definierte Serializer


class ProfileDetailView(RetrieveUpdateAPIView):
    # setzt den Serializer für Ein-/Ausgabe
    serializer_class = ProfileDetailSerializer
    # Permission: nur authentifizierte Nutzer dürfen zugreifen
    permission_classes = [IsAuthenticated]
    # wir verwenden einen Queryset, damit die GenericView das Objekt laden kann
    queryset = Profile.objects.select_related('user').all()
    # Lookup-Feld entspricht {pk} in der URL
    lookup_field = 'pk'

    def get(self, request, *args, **kwargs):
        # GET: liefert Detaildaten eines Profils
        try:
            # lädt das Profil anhand der pk (404, wenn nicht vorhanden)
            profile = get_object_or_404(self.get_queryset(), pk=kwargs.get(self.lookup_field))
            # serialisiert das Profil
            serializer = self.get_serializer(profile)
            # gibt 200 OK + Daten zurück
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            # Fängt unerwartete Fehler ab -> 500
            return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def patch(self, request, *args, **kwargs):
        # PATCH: partielles Update (Bearbeiten der Profildaten)
        try:
            # lädt das Zielprofil (404 bei Nichtfinden)
            profile = get_object_or_404(self.get_queryset(), pk=kwargs.get(self.lookup_field))
            # partielles Update erlauben
            serializer = self.get_serializer(profile, data=request.data, partial=True)
            # validiert die Eingabe
            serializer.is_valid(raise_exception=True)
            # speichert Änderungen (inkl. User-Feldern via update())
            serializer.save()
            # gibt die aktualisierten Daten mit 200 zurück
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as exc:
            # Wenn der Fehler ein Validierungsfehler ist, überlässt .is_valid() das DRF-Handling (400)
            # Hier allgemeiner Fallback -> 500
            return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)