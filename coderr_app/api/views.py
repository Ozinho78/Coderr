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
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework import status
from core.utils.permissions import IsOwnerOrReadOnly, IsBusinessUser, IsCustomerUser
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
    """Retrieves or updates the authenticated user's profile identified by user-id, rejects access if the requesting user is not the owner."""
    serializer_class = ProfileDetailSerializer
    permission_classes = [IsAuthenticated]
    queryset = Profile.objects.select_related('user').all()
    lookup_field = 'user_id'
    lookup_url_kwarg = 'pk'
    
    def retrieve(self, request, *args, **kwargs):
        profile = self.get_object()
        if request.user.id != profile.user_id:
            raise PermissionDenied('Forbidden: not the owner of this profile.')
        serializer = self.get_serializer(profile)
        return Response(serializer.data)
    
    def perform_update(self, serializer):         
        profile = self.get_object()               
        if self.request.user != profile.user:     
            raise PermissionDenied('Forbidden: not the owner of this profile.')
        serializer.save()                             


class BusinessProfileListView(ListAPIView):                      
    """List business profiles with optional filtering, read-only endpoint just for viewing"""
    serializer_class = ProfileListSerializer                     
    permission_classes = [IsAuthenticated]                       
    queryset = Profile.objects.select_related('user').filter(type='business')


class CustomerProfileListView(ListAPIView):                   
    """'List customer profiles with optional filtering, read-only endpoint for administration"""
    serializer_class = ProfileListSerializer                  
    permission_classes = [IsAuthenticated]                    
    queryset = Profile.objects.select_related('user').filter(type='customer')
    
    
class OfferListCreateView(ListCreateAPIView):
    """Lists all offers or creates a new one as a business user, applies validation and ownership on creation"""
    parser_classes = (JSONParser, MultiPartParser, FormParser)
    pagination_class = OfferPageNumberPagination

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsBusinessUser()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OfferCreateSerializer
        return OfferListSerializer

    def get_queryset(self):
        qs = (
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
    

class OfferRetrieveView(RetrieveAPIView):
    """'Returns a single offer by ID, read-only access for viewing offer basics"""
    permission_classes = [IsAuthenticated]
    serializer_class = OfferRetrieveSerializer

    def get_queryset(self):                   
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
        

class OfferDetailRetrieveView(RetrieveAPIView):        
    """Returns an offer with its details"""
    permission_classes = [IsAuthenticated]             
    serializer_class = OfferDetailRetrieveSerializer   
    queryset = OfferDetail.objects.all()               
    
    
class OfferRetrieveView(RetrieveUpdateDestroyAPIView):
    """Returns a single offer by ID, read-only access for viewing offer basic info"""
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]
    serializer_class = OfferRetrieveSerializer

    def get_queryset(self):                        
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

    def get_serializer_class(self):                        
        if self.request.method in ('PATCH', 'PUT'):
            return OfferUpdateSerializer                   
        return OfferRetrieveSerializer                     

    def patch(self, request, *args, **kwargs):             
        offer = self.get_object()                          
        serializer = self.get_serializer(offer, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        out = OfferPatchResponseSerializer(offer, context={'request': request})
        return Response(out.data, status=status.HTTP_200_OK)
    
    
class OrderListView(ListAPIView):
    """Lists orders visible to the authenticated user"""
    permission_classes = [IsAuthenticated]
    serializer_class = OrderListSerializer

    def get_queryset(self):
        user = self.request.user

        qs = (
            Order.objects
            .filter(Q(customer_user=user) | Q(business_user=user))
            .order_by('-created_at')
        )
        return qs
    

class OrderListCreateView(ListCreateAPIView):
    """Lists orders or creates a new order for the current customer"""
    permission_classes = [IsAuthenticated]
    parser_classes = (JSONParser,)        

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return OrderCreateInputSerializer
        return OrderListSerializer

    def get_queryset(self):
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
            profile = Profile.objects.get(user=request.user)
        except Profile.DoesNotExist:
            return Response({'detail': 'Kein Profil für den Benutzer gefunden.'}, status=status.HTTP_403_FORBIDDEN)

        if profile.type != 'customer':                      
            return Response({'detail': 'Nur Kunden dürfen Bestellungen erstellen.'}, status=status.HTTP_403_FORBIDDEN)

        try:
            detail = OfferDetail.objects.select_related('offer', 'offer__user').get(pk=offer_detail_id)
        except OfferDetail.DoesNotExist:
            return Response({'detail': 'OfferDetail nicht gefunden.'}, status=status.HTTP_404_NOT_FOUND)

        business_user = detail.offer.user
        customer_user = request.user
        if business_user_id := getattr(business_user, 'id', None):
            if business_user_id == customer_user.id:
                return Response({'detail': 'Eigene Angebote können nicht bestellt werden.'}, status=status.HTTP_403_FORBIDDEN)

        order = Order.objects.create(
            customer_user=customer_user,
            business_user=business_user,
            title=detail.title or detail.name or 'Bestellung',
            revisions=detail.revisions or 0,                  
            delivery_time_in_days=detail.delivery_time_in_days or detail.delivery_time or 0,
            price=detail.price,                      
            features=detail.features or [],          
            offer_type=detail.offer_type or (detail.name or '').lower() or 'basic',
        )
        out = OrderListSerializer(order)
        return Response(out.data, status=status.HTTP_201_CREATED)
    
    
class OrderStatusUpdateView(RetrieveUpdateDestroyAPIView):
    """Updates the status of an order by ID, restricted to the business owner of the order or staff member"""
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    lookup_field = 'pk'
    parser_classes = (JSONParser,)        

    def get_serializer_class(self):
        return OrderStatusPatchSerializer if self.request.method in ('PATCH', 'PUT') else OrderListSerializer

    def update(self, request, *args, **kwargs):
        if request.method == 'PUT':
            return Response({'detail': 'Nur PATCH ist erlaubt.'}, status=status.HTTP_400_BAD_REQUEST)

        order = self.get_object()

        profile = Profile.objects.filter(user=request.user).first()
        if not profile or profile.type != 'business':
            return Response({'detail': 'Nur Business-User dürfen den Status ändern.'}, status=status.HTTP_403_FORBIDDEN)

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
    """Returns the number of in-progress orders for a given business-user-id"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id):
        try:
            user = User.objects.get(pk=business_user_id)
        except User.DoesNotExist:
            return Response({'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'}, status=status.HTTP_404_NOT_FOUND)

        profile = Profile.objects.filter(user=user).first()
        if not profile or profile.type != 'business':
            return Response({'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'}, status=status.HTTP_404_NOT_FOUND)

        count = Order.objects.filter(business_user_id=business_user_id, status='in_progress').count()

        return Response({'order_count': count}, status=status.HTTP_200_OK)
    
    
class CompletedOrderCountView(APIView):
    """Returns the number of completed orders for a given business-user-id"""
    permission_classes = [IsAuthenticated]

    def get(self, request, business_user_id):
        try:
            user = User.objects.get(pk=business_user_id)
        except User.DoesNotExist:
            return Response(
                {'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'},
                status=status.HTTP_404_NOT_FOUND
            )

        profile = Profile.objects.filter(user=user).first()
        if not profile or profile.type != 'business':
            return Response(
                {'detail': 'Kein Geschäftsnutzer mit dieser ID gefunden.'},
                status=status.HTTP_404_NOT_FOUND
            )

        count = Order.objects.filter(
            business_user_id=business_user_id,
            status='completed'
        ).count()

        return Response({'completed_order_count': count}, status=status.HTTP_200_OK)
    
    
class ReviewListView(ListCreateAPIView):
    """Lists reviews or creates a new review as a customer"""
    permission_classes = [IsAuthenticated]
    pagination_class = None        

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsAuthenticated(), IsCustomerUser()]
        return [IsAuthenticated()]

    def get_serializer_class(self):
        return ReviewCreateSerializer if self.request.method == 'POST' else ReviewListSerializer

    def get_queryset(self):
        qs = Review.objects.all().order_by('-updated_at')
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
        profile = Profile.objects.filter(user=request.user).first()
        if not profile or profile.type != 'customer':
            return Response({'detail': 'Nur Kunden dürfen Bewertungen erstellen.'}, status=status.HTTP_401_UNAUTHORIZED)

        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        review = serializer.save()

        out = ReviewListSerializer(review)
        return Response(out.data, status=status.HTTP_201_CREATED)    


class ReviewDetailView(RetrieveUpdateDestroyAPIView):
    """Retrieves, updates, or deletes a single review by ID"""
    permission_classes = [IsAuthenticated]
    queryset = Review.objects.all()
    lookup_field = 'pk'

    def get_serializer_class(self):
        return ReviewUpdateSerializer if self.request.method in ('PATCH', 'PUT') else ReviewListSerializer

    def update(self, request, *args, **kwargs):
        review = self.get_object()
        if review.reviewer_id != request.user.id:
            return Response({'detail': 'Forbidden: nicht der Ersteller dieser Bewertung.'}, status=status.HTTP_403_FORBIDDEN)

        if request.method == 'PUT':
            return Response({'detail': 'Nur PATCH ist erlaubt.'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(review, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        out = ReviewListSerializer(review)
        return Response(out.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        review = self.get_object()
        if review.reviewer_id != request.user.id:
            return Response({'detail': 'Forbidden: nicht der Ersteller dieser Bewertung.'}, status=status.HTTP_403_FORBIDDEN)

        self.perform_destroy(review)
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class BaseInfoView(APIView):
    """Returns platform summary (reviews, average rating, business count, offer count) for the dashboard."""
    permission_classes = [AllowAny]

    def get(self, request):
        try:
            agg = Review.objects.aggregate(
                review_count=Count('id'),
                avg_rating=Avg('rating'),
            )
            review_count = agg['review_count'] or 0
            avg_raw = agg['avg_rating'] or 0       
            average_rating = round(float(avg_raw), 1) if review_count > 0 else 0.0
            business_profile_count = Profile.objects.filter(type='business').count()
            offer_count = Offer.objects.count()
            data = {
                'review_count': review_count,
                'average_rating': average_rating,
                'business_profile_count': business_profile_count,
                'offer_count': offer_count,
            }
            return Response(data, status=status.HTTP_200_OK)
        except Exception:
            return Response({'detail': 'Interner Serverfehler.'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)