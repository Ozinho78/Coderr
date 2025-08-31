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
    OrderListSerializer,
    OrderCreateInputSerializer,
    OrderStatusPatchSerializer
)
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
    

  
# OrderListSerializer existiert und liefert genau die Felder, die du im Response-Format sehen willst (IDs, Titel, Preis, Features, offer_type, Status & Timestamps).
# Order-Modell enthält exakt diese Spalten und Default-Status (in_progress), die beim Create gesetzt werden.
# OfferDetail besitzt alle benötigten Felder (title, revisions, delivery_time_in_days, price, features, offer_type) und den Link zum Offer, damit wir offer.user als business_user verwenden können. (Siehe deine Modelle/Dumps – neuere Details haben diese Felder bereits; ältere haben ggf. nur name/delivery_time, die ich sauber abfange.)
class OrderListCreateView(ListCreateAPIView):
    # GET & POST auf demselben Pfad
    permission_classes = [IsAuthenticated]        # 401 falls nicht eingeloggt
    parser_classes = (JSONParser,)                # wir erwarten JSON im Body für POST

    def get_serializer_class(self):
        # GET → Liste mit OrderListSerializer; POST validiert erst mit dem Input-Serializer
        if self.request.method == 'POST':
            return OrderCreateInputSerializer
        return OrderListSerializer

    def get_queryset(self):
        # liefert nur Orders zurück, an denen der eingeloggte User beteiligt ist (Kunde ODER Business)
        user = self.request.user
        return (
            Order.objects
            .filter(Q(customer_user=user) | Q(business_user=user))
            .order_by('-created_at')
        )

    def create(self, request, *args, **kwargs):
        # 1) Eingabe prüfen (nur offer_detail_id erlaubt)
        in_serializer = self.get_serializer(data=request.data)   # nutzt OrderCreateInputSerializer
        in_serializer.is_valid(raise_exception=True)             # 400 bei Fehlern
        offer_detail_id = in_serializer.validated_data['offer_detail_id']  # geprüfte ID

        # 2) Typ-Prüfung: nur 'customer' darf bestellen (403 sonst)
        try:
            profile = Profile.objects.get(user=request.user)     # Profil zum eingeloggten User holen
        except Profile.DoesNotExist:
            return Response({'detail': 'Kein Profil für den Benutzer gefunden.'}, status=status.HTTP_403_FORBIDDEN)

        if profile.type != 'customer':                           # nur Kunden dürfen Orders erstellen
            return Response({'detail': 'Nur Kunden dürfen Bestellungen erstellen.'}, status=status.HTTP_403_FORBIDDEN)

        # 3) OfferDetail laden (404, wenn nicht vorhanden)
        try:
            detail = OfferDetail.objects.select_related('offer', 'offer__user').get(pk=offer_detail_id)
        except OfferDetail.DoesNotExist:
            return Response({'detail': 'OfferDetail nicht gefunden.'}, status=status.HTTP_404_NOT_FOUND)

        # 4) Business = Ersteller des Offers (offer.user)
        business_user = detail.offer.user                        # Dienstleister
        customer_user = request.user                             # aktueller Kunde

        # Optional: Kunde darf nicht sein eigenes Offer bestellen (falls gewünscht)
        if business_user_id := getattr(business_user, 'id', None):
            if business_user_id == customer_user.id:
                return Response({'detail': 'Eigene Angebote können nicht bestellt werden.'}, status=status.HTTP_403_FORBIDDEN)

        # 5) Felder aus OfferDetail in Order "einfrieren" (Titel/Preis/Features/…)
        #    Deine Order-DB erwartet genau diese Felder (siehe Modell). :contentReference[oaicite:1]{index=1}
        order = Order.objects.create(
            customer_user=customer_user,                         # FK Kunde
            business_user=business_user,                         # FK Dienstleister
            title=detail.title or detail.name or 'Bestellung',   # Fallback, falls title leer ist
            revisions=detail.revisions or 0,                     # Anzahl Revisionen
            delivery_time_in_days=detail.delivery_time_in_days or detail.delivery_time or 0,  # Tage
            price=detail.price,                                  # Decimal aus OfferDetail
            features=detail.features or [],                      # Liste (JSONField)
            offer_type=detail.offer_type or (detail.name or '').lower() or 'basic',  # best guess bei alten Datensätzen
            # status bleibt Default 'in_progress'
        )

        # 6) Ausgabe im geforderten Format (nutzt bereits existierenden List-Serializer)
        out = OrderListSerializer(order)                         # gleiche Struktur wie GET-Liste
        return Response(out.data, status=status.HTTP_201_CREATED)
    
    
# Auth + Typ: IsAuthenticated + IsBusinessUser (du hast die Permission schon verdrahtet).
# Owner-Check: order.business_user_id == request.user.id – nur der Dienstleister der Order darf updaten.
# Antwort: voller Datensatz via OrderListSerializer, genau wie bei GET /api/orders/.
# updated_at kommt automatisch aus auto_now.
class OrderStatusUpdateView(RetrieveUpdateAPIView):
    # GET (optional) + PATCH auf /api/orders/<pk>/
    queryset = Order.objects.all()                     # Basis-Query
    permission_classes = [IsAuthenticated, IsBusinessUser]  # 401/403 wenn kein Business-User
    lookup_field = 'pk'                                # URL-Parameter 'id' → pk

    def get_serializer_class(self):
        # Für PATCH: Eingabe-Serializer (nur 'status'); Für GET: Ausgabe-Serializer
        return OrderStatusPatchSerializer if self.request.method in ('PATCH', 'PUT') else OrderListSerializer

    def update(self, request, *args, **kwargs):
        # Wir unterstützen nur PATCH (partiell); PUT blocken wir bewusst
        if request.method == 'PUT':
            return Response({'detail': 'Nur PATCH ist erlaubt.'}, status=status.HTTP_400_BAD_REQUEST)

        # Ziel-Order laden (404 auto bei Nichtfinden)
        order = self.get_object()

        # Objektberechtigung: nur der zugehörige Business-Owner dieser Bestellung darf den Status ändern
        if order.business_user_id != request.user.id:
            return Response({'detail': 'Nur der Business-Owner dieser Bestellung darf den Status ändern.'}, status=status.HTTP_403_FORBIDDEN)

        # Eingabe validieren (nur 'status' erlaubt)
        serializer = OrderStatusPatchSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        # Speichern löst auto_now bei updated_at aus (siehe Modell) :contentReference[oaicite:5]{index=5}
        serializer.save()

        # Ausgabe: komplette Order im bekannten Format
        out = OrderListSerializer(order)
        return Response(out.data, status=status.HTTP_200_OK)