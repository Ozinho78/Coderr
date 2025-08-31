from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db.models import Min, Q, Case, When, F, IntegerField, Avg, Count
from rest_framework.views import APIView
from rest_framework.generics import (
    ListAPIView, 
    RetrieveUpdateAPIView, 
    RetrieveAPIView,
    ListCreateAPIView,
    RetrieveUpdateDestroyAPIView,
)
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework import status
from core.utils.permissions import IsOwnerOrReadOnly, IsBusinessUser
from auth_app.models import Profile
from coderr_app.api.serializers import ProfileDetailSerializer, ProfileListSerializer, ReviewListSerializer
from coderr_app.models import Offer, OfferDetail, Order, Review
from coderr_app.api.serializers import (
    OfferListSerializer, 
    OfferCreateSerializer, 
    OfferRetrieveSerializer, 
    OfferDetailRetrieveSerializer, 
    OfferUpdateSerializer, 
    OfferPatchResponseSerializer, 
    OrderListSerializer,
    OrderCreateInputSerializer,
    OrderStatusPatchSerializer,
    ReviewCreateSerializer,
    ReviewUpdateSerializer,
)
from coderr_app.api.pagination import OfferPageNumberPagination, ReviewPageNumberPagination



class ProfileDetailView(RetrieveUpdateAPIView):

    serializer_class = ProfileDetailSerializer

    permission_classes = [IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]   # Read: offen, Write: auth + owner

    queryset = Profile.objects.select_related('user').all()
    lookup_field = 'user_id'        # Feld am Modell (implizit vorhanden durch FK)
    lookup_url_kwarg = 'pk'         # Name des URL-Params bleibt {pk}
    


    def perform_update(self, serializer):                          # wird bei PATCH/PUT vor .save() aufgerufen
        profile = self.get_object()                                # holt das Zielprofil (404 falls nicht da)
        if self.request.user != profile.user:                      # Owner-Check: nur eigener Datensatz
            raise PermissionDenied('Forbidden: not the owner of this profile.')  # -> 403
        serializer.save()                                          # speichert Profil + User-Felder



class BusinessProfileListView(ListAPIView):                         # GET /api/profiles/business/
    serializer_class = ProfileListSerializer                        # Ausgabeformat
    permission_classes = [IsAuthenticated]                          # 401 wenn nicht eingeloggt
    queryset = Profile.objects.select_related('user').filter(type='business')  # nur Business-Profile, effizient mit JOIN


class CustomerProfileListView(ListAPIView):                         # GET /api/profiles/customer/
    serializer_class = ProfileListSerializer                        # selbes Ausgabeformat
    permission_classes = [IsAuthenticated]                          # 401 wenn nicht eingeloggt
    queryset = Profile.objects.select_related('user').filter(type='customer')  # nur Customer-Profile
    
    
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
        

class OfferDetailRetrieveView(RetrieveAPIView):                     # Einzelnes Angebotsdetail abrufen
    permission_classes = [IsAuthenticated]                          # 401 falls nicht eingeloggt (Vorgabe)
    serializer_class = OfferDetailRetrieveSerializer                # Ausgabeformat laut Spezifikation
    queryset = OfferDetail.objects.all()                            # 404 bei unbekannter ID handled DRF automatisch
    
    
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
    
    
class OrderListView(ListAPIView):
    # Nur eingeloggte Nutzer → 401 wenn nicht authentifiziert
    permission_classes = [IsAuthenticated]
    # Serializer bestimmt das Antwortformat
    serializer_class = OrderListSerializer

    def get_queryset(self):
        user = self.request.user

        qs = (
            Order.objects
            .filter(Q(customer_user=user) | Q(business_user=user))
            .order_by('-created_at')   # neueste zuerst (komfortabel für die Liste)
        )
        return qs
    

  
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
        in_serializer = self.get_serializer(data=request.data)
        in_serializer.is_valid(raise_exception=True)          
        offer_detail_id = in_serializer.validated_data['offer_detail_id']
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

        business_user = detail.offer.user                        # Dienstleister
        customer_user = request.user                             # aktueller Kunde
        if business_user_id := getattr(business_user, 'id', None):
            if business_user_id == customer_user.id:
                return Response({'detail': 'Eigene Angebote können nicht bestellt werden.'}, status=status.HTTP_403_FORBIDDEN)

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
    
    
class OrderStatusUpdateView(RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()               # Basis-Query
    permission_classes = [IsAuthenticated]       # Auth-Pflicht (401 sonst)
    lookup_field = 'pk'
    parser_classes = (JSONParser,)               # JSON-Body parsen

    def get_serializer_class(self):
        # PATCH/PUT → Eingabe-Serializer (nur 'status'); GET → Vollausgabe
        return OrderStatusPatchSerializer if self.request.method in ('PATCH', 'PUT') else OrderListSerializer

    def update(self, request, *args, **kwargs):
        # PUT bewusst blocken – nur PATCH erlaubt
        if request.method == 'PUT':
            return Response({'detail': 'Nur PATCH ist erlaubt.'}, status=status.HTTP_400_BAD_REQUEST)

        # 1) Order laden (404 automatisch bei Nichtfinden)
        order = self.get_object()

        # 2) Typ-Check: nur Business-User dürfen Status ändern
        profile = Profile.objects.filter(user=request.user).first()
        if not profile or profile.type != 'business':
            return Response({'detail': 'Nur Business-User dürfen den Status ändern.'}, status=status.HTTP_403_FORBIDDEN)

        # 3) Ownership: nur der Business-Owner der Order darf updaten
        if order.business_user_id != request.user.id:
            return Response({'detail': 'Forbidden: nicht der Besitzer dieser Bestellung.'}, status=status.HTTP_403_FORBIDDEN)

        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        serializer = self.get_serializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        out = OrderListSerializer(order)
        return Response(out.data, status=status.HTTP_200_OK)

    def delete(self, request, *args, **kwargs):
        if not request.user.is_staff:
            return Response({'detail': 'Nur Staff-Benutzer dürfen Bestellungen löschen.'}, status=status.HTTP_403_FORBIDDEN)
        obj = self.get_object()
        self.perform_destroy(obj)
        return Response(status=status.HTTP_204_NO_CONTENT)
    

class OrderInProgressCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id):
        try:
            user = User.objects.get(pk=business_user_id)       # User mit der ID laden
        except User.DoesNotExist:
            # Vorgabe: 404, wenn kein Geschäftsnutzer mit dieser ID existiert
            return Response({'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'}, status=status.HTTP_404_NOT_FOUND)

        # 2) Ist es wirklich ein Business-Profil?
        profile = Profile.objects.filter(user=user).first()     # Profil holen (falls vorhanden)
        if not profile or profile.type != 'business':
            # Kein Business-User → wie „nicht gefunden“ behandeln
            return Response({'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'}, status=status.HTTP_404_NOT_FOUND)

        # 3) Anzahl laufender Bestellungen zählen (Status = in_progress)
        count = Order.objects.filter(business_user_id=business_user_id, status='in_progress').count()

        # 4) Erfolgreiche Antwort
        return Response({'order_count': count}, status=status.HTTP_200_OK)
    
    
class CompletedOrderCountView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id):
        # 1) Existiert der User?
        try:
            user = User.objects.get(pk=business_user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 2) Ist es ein Business-Profil?
        profile = Profile.objects.filter(user=user).first()
        if not profile or profile.type != 'business':
            return Response(
                {'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3) Anzahl abgeschlossener Bestellungen zählen
        count = Order.objects.filter(
            business_user_id=business_user_id,
            status='completed'
        ).count()

        # 4) Erfolgreiche Antwort
        return Response({'completed_order_count': count}, status=status.HTTP_200_OK)
    
    
class ReviewListView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]     # 401 wenn nicht eingeloggt
    pagination_class = None                    # flache Liste, nicht paginiert

    def get_serializer_class(self):
        # GET → List-Serializer, POST → Create-Serializer
        return ReviewCreateSerializer if self.request.method == 'POST' else ReviewListSerializer

    def get_queryset(self):
        # Standard: neueste zuerst
        qs = Review.objects.all().order_by('-updated_at')

        # Filter/Ordering wie zuvor
        params = self.request.query_params

        business_user_id = params.get('business_user_id')
        if business_user_id:
            if not str(business_user_id).isdigit():
                raise ValidationError({'business_user_id': 'Muss eine ganze Zahl sein.'})
            qs = qs.filter(business_user_id=int(business_user_id))

        reviewer_id = params.get('reviewer_id')
        if reviewer_id:
            if not str(reviewer_id).isdigit():
                raise ValidationError({'reviewer_id': 'Muss eine ganze Zahl sein.'})
            qs = qs.filter(reviewer_id=int(reviewer_id))

        ordering = params.get('ordering')
        if ordering:
            if ordering not in {'updated_at', 'rating'}:
                raise ValidationError({'ordering': 'Ungültig: updated_at oder rating'})
            qs = qs.order_by(ordering)
        return qs

    def create(self, request, *args, **kwargs):
        # Nur Kunden dürfen erstellen (explizit prüfen, damit wir saubere Meldung/403 liefern)
        profile = Profile.objects.filter(user=request.user).first()
        if not profile or profile.type != 'customer':
            return Response({'detail': 'Nur Kunden dürfen Bewertungen erstellen.'}, status=status.HTTP_401_UNAUTHORIZED)

        # Validierung + Erzeugung
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()  # create() setzt reviewer

        # Ausgabe im Leseformat (inkl. reviewer/business_user IDs + Timestamps)
        out = ReviewListSerializer(review)
        return Response(out.data, status=status.HTTP_201_CREATED)    

    
    
class ReviewDetailView(RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]     # 401 für alle Write/Read ohne Login
    queryset = Review.objects.all()            # 404 handled DRF
    lookup_field = 'pk'

    def get_serializer_class(self):
        # PATCH → Update-Serializer (nur rating/description), GET → List-Serializer
        return ReviewUpdateSerializer if self.request.method in ('PATCH', 'PUT') else ReviewListSerializer

    def update(self, request, *args, **kwargs):
        # Nur Ersteller darf bearbeiten
        review = self.get_object()
        if review.reviewer_id != request.user.id:
            return Response({'detail': 'Forbidden: nicht der Ersteller dieser Bewertung.'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'PUT':
            return Response({'detail': 'Nur PATCH ist erlaubt.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()  # speichert rating/description; updated_at aktualisiert sich automatisch

        # Antwort im Leseformat inkl. IDs/Timestamps
        out = ReviewListSerializer(review)
        return Response(out.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        # Nur Ersteller darf löschen
        review = self.get_object()
        if review.reviewer_id != request.user.id:
            return Response({'detail': 'Forbidden: nicht der Ersteller dieser Bewertung.'}, status=status.HTTP_403_FORBIDDEN)

        self.perform_destroy(review)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class BaseInfoView(APIView):
    permission_classes = [AllowAny]  # öffentlich: keine Auth-Pflicht

    def get(self, request):
        try:
            # --- Reviews zählen + Durchschnitt berechnen ---
            agg = Review.objects.aggregate(
                review_count=Count('id'),   # Anzahl Bewertungen
                avg_rating=Avg('rating'),   # Durchschnittsrating (kann None sein)
            )
            review_count = agg['review_count'] or 0            # None→0 absichern
            avg_raw = agg['avg_rating'] or 0                   # None→0 absichern
            average_rating = round(float(avg_raw), 1) if review_count > 0 else 0.0  # eine Dezimalstelle

            # --- Anzahl Business-Profile ---
            business_profile_count = Profile.objects.filter(type='business').count()

            # --- Anzahl Offers ---
            offer_count = Offer.objects.count()

            # --- Response nach Vorgabe ---
            data = {
                'review_count': review_count,
                'average_rating': average_rating,
                'business_profile_count': business_profile_count,
                'offer_count': offer_count,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            # Fallback laut Vorgabe
            return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)