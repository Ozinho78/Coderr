from django.db.models import F, Q, Min, Case, When, IntegerField
from rest_framework.exceptions import ValidationError
from coderr_app.models import Offer

ALLOWED_ORDERING = {'updated_at', '-updated_at', 'min_price', '-min_price'}


def _base_offer_queryset():
    """Builds the basic queryset including annotations"""
    return (
        Offer.objects
        .select_related('user')
        .prefetch_related('details')
        .annotate(
            min_delivery_time=Min(
                Case(
                    When(
                        details__delivery_time_in_days__isnull=False,
                        then=F('details__delivery_time_in_days')
                    ),
                    default=F('details__delivery_time'),
                    output_field=IntegerField(),
                )
            ),
            min_price=Min('details__price'),
        )
    )


def _parse_int(value, field_name):
    """Parses integer, throws error if not an int"""
    if value is None or value == '':
        return None
    if not str(value).isdigit():
        raise ValidationError({field_name: 'Muss eine ganze Zahl sein.'})
    return int(value)


def _parse_float(value, field_name):
    """Parses float, throws error if not a float"""
    if value is None or value == '':
        return None
    try:
        return float(value)
    except ValueError:
        raise ValidationError({field_name: 'Muss eine Zahl sein.'})


def _validate_ordering(value):
    """Checks ordering against whitelist, returns default when empty"""
    if not value:
        return '-updated_at'
    if value not in ALLOWED_ORDERING:
        raise ValidationError({'ordering': 'Ungültig: updated_at, -updated_at, min_price, -min_price'})
    return value
  

def _apply_filters(qs, params):
    """Applies all optional filters with validation"""
    creator_id = _parse_int(params.get('creator_id'), 'creator_id')
    if creator_id is not None:
        qs = qs.filter(user_id=creator_id)

    min_price = _parse_float(params.get('min_price'), 'min_price')
    if min_price is not None:
        qs = qs.filter(min_price__gte=min_price)

    max_delivery_time = _parse_int(params.get('max_delivery_time'), 'max_delivery_time')
    if max_delivery_time is not None:
        qs = qs.filter(min_delivery_time__lte=max_delivery_time)

    search = params.get('search')
    if search:
        qs = qs.filter(Q(title__icontains=search) | Q(description__icontains=search))

    ordering = _validate_ordering(params.get('ordering'))
    return qs.order_by(ordering)


def build_offer_queryset(request):
    """Public API, builds and filters queryset depending on method"""
    qs = _base_offer_queryset()
    if request.method == 'GET':
        qs = _apply_filters(qs, request.query_params)
    return qs