from django.db.models import Q
from rest_framework.exceptions import APIException
from rest_framework import status
from coderr_app.models import Order, OfferDetail
from auth_app.models import Profile


def build_order_queryset(request):
    """Builds the queryset for orders of current user (customer or business)"""
    user = request.user
    return (
        Order.objects
        .filter(Q(customer_user=user) | Q(business_user=user))
        .order_by('-created_at')
    )


def create_order_from_offer_detail(request, validated_data):
    """Creates order from offer-detail id with all checks and errors"""
    offer_detail_id = validated_data['offer_detail_id']
    profile = Profile.objects.filter(user=request.user).first()
    if not profile:
        raise _api_error('Kein Profil für den Benutzer gefunden.', status.HTTP_403_FORBIDDEN)
    if profile.type != 'customer':
        raise _api_error('Nur Kunden dürfen Bestellungen erstellen.', status.HTTP_403_FORBIDDEN)

    detail = OfferDetail.objects.select_related('offer', 'offer__user').filter(pk=offer_detail_id).first()
    if not detail:
        raise _api_error('OfferDetail nicht gefunden.', status.HTTP_404_NOT_FOUND)

    business_user = detail.offer.user
    customer_user = request.user

    if getattr(business_user, 'id', None) == customer_user.id:
        raise _api_error('Eigene Angebote können nicht bestellt werden.', status.HTTP_403_FORBIDDEN)

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
    return order


def _api_error(message, status_code):
    """Small helper, generates DRF compatible exceptions with same JSON body"""
    exc = APIException(detail={'detail': message})
    exc.status_code = status_code
    raise exc

