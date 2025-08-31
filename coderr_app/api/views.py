from django.shortcuts import get_object_or_404  # 404-Helfer
from django.db.models import Min, Q, Case, When, F, IntegerField  # Aggregation + Suche
from rest_framework.generics import (
    ListAPIView, 
    RetrieveUpdateAPIView, 
    RetrieveAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly  # Auth-Pflicht
from rest_framework.exceptions import ValidationError  # für 400-Fehler
from rest_framework.response import Response  # HTTP-Antwort
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework import status
from core.utils.permissions import IsOwnerOrReadOnly, IsBusinessUser
from auth_app.models import Profile
from coderr_app.api.serializers import ProfileDetailSerializer, ProfileListSerializer
from coderr_app.models import Offer, OfferDetail, Order
from coderr_app.api.serializers import (
    OfferListSerializer, 
    OfferCreateSerializer, 
    OfferRetrieveSerializer, 
    OfferDetailRetrieveSerializer, 
    OfferUpdateSerializer, 
    OfferPatchResponseSerializer, 
    OrderListSerializer)
from coderr_app.api.pagination import OfferPageNumberPagination



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
    
    
# ------------------------------------------------------------
# <<< CHANGE: neue kombinierte View-Klasse für LIST + CREATE
# ------------------------------------------------------------
class OfferListCreateView(ListCreateAPIView):  # <<< CHANGE (statt OfferListView/ListAPIView)
    parser_classes = (JSONParser, MultiPartParser, FormParser)  # <<< NEW: JSON + FormData (Bild)
    pagination_class = OfferPageNumberPagination  # wie gehabt

    def get_permissions(self):  # <<< NEW: abhängig von Methode
        if self.request.method == 'POST':
            # nur eingeloggte Business-User dürfen erstellen
            return [IsAuthenticated(), IsBusinessUser()]
        return [AllowAny()]  # Liste ist öffentlich

    def get_serializer_class(self):  # <<< NEW: GET vs. POST
        if self.request.method == 'POST':
            return OfferCreateSerializer
        return OfferListSerializer

    def get_queryset(self):
        # Basis-Query (User joinen, Details vorladen)
        qs = (
            Offer.objects
            .select_related('user')
            .prefetch_related('details')
            .annotate(
                # <<< CHANGE: min_delivery_time auf neues Feld mit Fallback
                min_delivery_time=Min(
                    Case(
                        When(details__delivery_time_in_days__isnull=False, then=F('details__delivery_time_in_days')),
                        default=F('details__delivery_time'),
                        output_field=IntegerField(),
                    )
                ),
                min_price=Min('details__price'),
            )
        )

        # Filter/Sortierung nur für GET anwenden
        if self.request.method == 'GET':
            params = self.request.query_params

            creator_id = params.get('creator_id')
            if creator_id:
                if not str(creator_id).isdigit():
                    raise ValidationError({'creator_id': 'Muss eine ganze Zahl sein.'})
                qs = qs.filter(user_id=int(creator_id))

            min_price = params.get('min_price')
            if min_price:
                try:
                    min_price_val = float(min_price)
                except ValueError:
                    raise ValidationError({'min_price': 'Muss eine Zahl sein.'})
                qs = qs.filter(min_price__gte=min_price_val)

            max_delivery_time = params.get('max_delivery_time')
            if max_delivery_time:
                if not str(max_delivery_time).isdigit():
                    raise ValidationError({'max_delivery_time': 'Muss eine ganze Zahl (Tage) sein.'})
                qs = qs.filter(min_delivery_time__lte=int(max_delivery_time))

            search = params.get('search')
            if search:
                qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

            ordering = params.get('ordering')
            if ordering:
                allowed = {'updated_at', '-updated_at', 'min_price', '-min_price'}
                if ordering not in allowed:
                    raise ValidationError({'ordering': 'Ungültig: updated_at, -updated_at, min_price, -min_price'})
                qs = qs.order_by(ordering)
            else:
                qs = qs.order_by('-updated_at')

        return qs
    


# 404 bei unbekannter ID macht DRF automatisch (RetrieveAPIView).
# 500 fängt dein globaler Exception-Handler ab (in Settings konfiguriert) — du hast dort einen Custom-Handler vorgesehen (in deinen Settings ist ein Custom-Pfad hinterlegt; das allgemeine Prinzip kommt aus deiner exceptions.py Vorlage ).
class OfferRetrieveView(RetrieveAPIView):                                  # <<< NEW: GET /api/offers/<pk>/
    permission_classes = [IsAuthenticated]                                 # 401, wenn nicht eingeloggt (Anforderung)
    serializer_class = OfferRetrieveSerializer                             # benutzt absoluten URL-Serializer

    def get_queryset(self):                                                # Query inkl. Annotationen wie in Liste
        return (
            Offer.objects
            .select_related('user')                                        # effizienter JOIN auf user
            .prefetch_related('details')                                   # Details vorladen
            .annotate(
                min_delivery_time=Min(                                     # minimaler Tagewert (neues oder legacy Feld)
                    Case(
                        When(details__delivery_time_in_days__isnull=False, then=F('details__delivery_time_in_days')),
                        default=F('details__delivery_time'),
                        output_field=IntegerField(),
                    )
                ),
                min_price=Min('details__price'),                           # minimaler Preis über alle Details
            )
        )
        

# ------------------------------------------------------------
# <<< NEW: GET /api/offerdetails/<pk>/  (auth-pflichtig)
# ------------------------------------------------------------
# Der GET-Endpoint soll (wie zuvor) details als id+absolute URL liefern → OfferRetrieveSerializer.
# Der PATCH-Response soll volle Detailobjekte zurückgeben → OfferPatchResponseSerializer.
# Owner-Check über deine Permission IsOwnerOrReadOnly (objektbezogen: obj.user_id == request.user.id) .
# 401/403/404/500 verhalten sich damit exakt wie gefordert; 500 deckt dein globaler Handler ab (Settings + exceptions) .
class OfferDetailRetrieveView(RetrieveAPIView):                     # Einzelnes Angebotsdetail abrufen
    permission_classes = [IsAuthenticated]                          # 401 falls nicht eingeloggt (Vorgabe)
    serializer_class = OfferDetailRetrieveSerializer                # Ausgabeformat laut Spezifikation
    queryset = OfferDetail.objects.all()                            # 404 bei unbekannter ID handled DRF automatisch
    
    
# ------------------------------------------------------------
# <<< CHANGE: OfferRetrieveView → RetrieveUpdateAPIView (GET + PATCH)
# ------------------------------------------------------------
# 404 bei unbekannter ID macht DRF automatisch (Retrieve/DestroyAPIView).
# 500 fängt dein globaler Exception-Handler ab (in Settings konfiguriert).
class OfferRetrieveView(RetrieveUpdateDestroyAPIView):  # <<< CHANGE: jetzt auch PATCH + DELETE
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]  # CHANGE: Owner-Gate für Write/DELETE, 401: nicht eingeloggt, 403: nicht der Owner (nur Ersteller darf löschen/ändern)
    serializer_class = OfferRetrieveSerializer  # GET nutzt weiterhin die Detailausgabe (mit absoluten URLs)

    # get_queryset() bleibt unverändert (Annotationen, Prefetch, etc.)
    def get_queryset(self):                                             # wie gehabt inkl. Annotationen/Vorladen
        return (
            Offer.objects
            .select_related('user')
            .prefetch_related('details')
            .annotate(
                min_delivery_time=Min(
                    Case(
                        When(details__delivery_time_in_days__isnull=False, then=F('details__delivery_time_in_days')),
                        default=F('details__delivery_time'),
                        output_field=IntegerField(),
                    )
                ),
                min_price=Min('details__price'),
            )
        )

    def get_serializer_class(self):                                     # GET vs. PATCH
        if self.request.method in ('PATCH', 'PUT'):
            return OfferUpdateSerializer                                # Eingabe-Serializer
        return OfferRetrieveSerializer                                   # GET-Serializer (id + absolute URLs)

    def patch(self, request, *args, **kwargs):                          # eigene PATCH-Logik mit Output-Serializer
        offer = self.get_object()                                       # löst 404 + Permissions (IsOwnerOrReadOnly) aus
        # Eingabe validieren (partial=True)
        serializer = self.get_serializer(offer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()                                               # ruft OfferUpdateSerializer.update()

        # Response: vollständiges Offer inkl. voller Details (nicht die URL-Variante)
        out = OfferPatchResponseSerializer(offer, context={'request': request})
        return Response(out.data, status=status.HTTP_200_OK)
    
    
# --- NEU: GET /api/orders/ ----------------------------------------------------
# permission_classes = [IsAuthenticated] → exakt deine Anforderung „Benutzer muss authentifiziert sein“ (sonst 401).
# get_queryset() filtert streng: nur Orders, wo request.user Kunde oder Business ist.
# order_by('-created_at') sortiert sinnvoll.
# 500-Fehler werden (wie bei deinen anderen Views) von deinem globalen Handler aufgefangen.
class OrderListView(ListAPIView):
    # Nur eingeloggte Nutzer → 401 wenn nicht authentifiziert
    permission_classes = [IsAuthenticated]
    # Serializer bestimmt das Antwortformat
    serializer_class = OrderListSerializer

    def get_queryset(self):
        # aktueller User aus dem Request
        user = self.request.user

        # Filter: Bestellungen, an denen der User beteiligt ist (als Kunde ODER als Business)
        qs = (
            Order.objects
            .filter(Q(customer_user=user) | Q(business_user=user))
            .order_by('-created_at')   # neueste zuerst (komfortabel für die Liste)
        )

        # .distinct() wäre nur nötig, falls Joins Duplikate erzeugen – hier nicht, also weggelassen
        return qs