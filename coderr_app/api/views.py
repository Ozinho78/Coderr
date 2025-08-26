from django.shortcuts import get_object_or_404  # 404-Helfer
from rest_framework.generics import ListAPIView, RetrieveUpdateAPIView  # DRF-Generic für Listen, GET+PATCH
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly  # Auth-Pflicht
from rest_framework.response import Response  # HTTP-Antwort
from rest_framework import status  # Statuscodes
from core.utils.permissions import IsOwnerOrReadOnly
from auth_app.models import Profile  # Profilmodell importieren
from coderr_app.api.serializers import ProfileDetailSerializer
from .serializers import ProfileListSerializer


class ProfileDetailView(RetrieveUpdateAPIView):
    # Serializer konfigurieren, definiert Serializer
    serializer_class = ProfileDetailSerializer
    # nur eingeloggte User dürfen zugreifen
    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]   # Read: offen, Write: auth + owner
    # Queryset, inkl. user für effiziente JOINs
    queryset = Profile.objects.select_related('user').all()
    # {pk} aus der URL
    # lookup_field = 'pk' # URL-Param: /api/profile/<pk>/
    # WICHTIG: {pk} aus der URL soll auf profile.user_id matchen:
    lookup_field = 'user_id'        # Feld am Modell (implizit vorhanden durch FK)
    lookup_url_kwarg = 'pk'         # Name des URL-Params bleibt {pk}
    
    # Hinweis: Wir überschreiben KEINE Methoden.
    # DRF ruft bei PATCH intern get_object() → check_object_permissions() auf.
    # IsAuthenticatedOrReadOnly blockt Unauth-Write (→ 401),
    # IsOwnerOrReadOnly blockt Fremd-Write (→ 403).

    # def get(self, request, *args, **kwargs):
    #     # GET liefert Profildetails
    #     try:
    #         # Profil anhand pk finden (404 bei Nichtfinden)
    #         profile = get_object_or_404(self.get_queryset(), pk=kwargs.get(self.lookup_field))
    #         # serialisieren
    #         serializer = self.get_serializer(profile)
    #         # 200 OK mit Daten
    #         return Response(serializer.data, status=status.HTTP_200_OK)
    #     except Exception:
    #         # Unerwarteter Fehler → 500
    #         return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def perform_update(self, serializer):                          # wird bei PATCH/PUT vor .save() aufgerufen
        profile = self.get_object()                                # holt das Zielprofil (404 falls nicht da)
        if self.request.user != profile.user:                      # Owner-Check: nur eigener Datensatz
            raise PermissionDenied('Forbidden: not the owner of this profile.')  # -> 403
        serializer.save()                                          # speichert Profil + User-Felder

    # def patch(self, request, *args, **kwargs):
    #     try:
    #         profile = get_object_or_404(self.get_queryset(), pk=kwargs.get(self.lookup_field))  # 404 wenn nicht da

    #         # >>> NEU: Eigentümer-Check – nur der Owner darf ändern
    #         if request.user != profile.user:
    #             return Response({'detail': 'Forbidden: not the owner of this profile.'}, status=status.HTTP_403_FORBIDDEN)

    #         serializer = self.get_serializer(profile, data=request.data, partial=True)  # partial=True für PATCH
    #         serializer.is_valid(raise_exception=True)  # 400 bei Validierungsfehlern (DRF macht das automatisch)
    #         serializer.save()  # speichert Profil + Userfelder (first/last/email)
    #         return Response(serializer.data, status=status.HTTP_200_OK)  # 200 inkl. gewünschter Struktur
    #     except Exception:
    #         return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)  # 500 Fallback


class BusinessProfileListView(ListAPIView):                         # GET /api/profiles/business/
    serializer_class = ProfileListSerializer                        # Ausgabeformat
    permission_classes = [IsAuthenticated]                          # 401 wenn nicht eingeloggt
    queryset = Profile.objects.select_related('user').filter(type='business')  # nur Business-Profile, effizient mit JOIN


class CustomerProfileListView(ListAPIView):                         # GET /api/profiles/customer/
    serializer_class = ProfileListSerializer                        # selbes Ausgabeformat
    permission_classes = [IsAuthenticated]                          # 401 wenn nicht eingeloggt
    queryset = Profile.objects.select_related('user').filter(type='customer')  # nur Customer-Profile