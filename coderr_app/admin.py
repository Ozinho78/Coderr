from django.contrib import admin
from django.db.models import Min
from django.utils.html import format_html
from coderr_app.models import Offer, OfferDetail, Order, Review


class OfferDetailInline(admin.TabularInline):
    """Provides inline table for OfferDetail"""
    model = OfferDetail
    extra = 0
    fields = ('name', 'price', 'delivery_time')
    readonly_fields = ()
    show_change_link = True

@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    """Configures presentation of offer list and details"""
    list_display = (
        'id',
        'creator_username',
        'title',
        'get_min_price',
        'get_min_delivery_time',
        'updated_at',
        'created_at',
    )
    ordering = ('-updated_at',)
    list_select_related = ('user',)
    search_fields = (
        'title',
        'description',
        'user__username',
        'user__first_name',
        'user__last_name',
    )
    list_filter = (
        'created_at',
        'updated_at',
    )
    inlines = [OfferDetailInline]
    readonly_fields = (
        'created_at',
        'updated_at',
        'min_price',
        'min_delivery_time',
        'creator_link',
        'user_username',
        'user_first_name',
        'user_last_name',
    )
    fieldsets = (
        ('Angebot', {
            'fields': ('user', 'title', 'image', 'description')
        }),
        ('Aggregierte Werte', {
            'fields': ('min_price', 'min_delivery_time'),
            'classes': ('collapse',),
        }),
        ('Creator', {
            'fields': ('creator_link', 'user_username', 'user_first_name', 'user_last_name'),
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
        }),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.select_related('user')
        qs = qs.annotate(
            _min_price=Min('details__price'),
            _min_delivery_time=Min('details__delivery_time'),
        )
        return qs

    def creator_username(self, obj):
        return obj.user.username if obj.user_id else '-'
    creator_username.short_description = 'Creator'
    creator_username.admin_order_field = 'user__username'

    def get_min_price(self, obj):
        return obj._min_price
    get_min_price.short_description = 'min_price'
    get_min_price.admin_order_field = '_min_price'

    def get_min_delivery_time(self, obj):
        return obj._min_delivery_time
    get_min_delivery_time.short_description = 'min_delivery_time'
    get_min_delivery_time.admin_order_field = '_min_delivery_time'

    def min_price(self, obj):
        return getattr(obj, '_min_price', None)
    min_price.short_description = 'min_price'

    def min_delivery_time(self, obj):
        return getattr(obj, '_min_delivery_time', None)
    min_delivery_time.short_description = 'min_delivery_time'

    def creator_link(self, obj):
        if not obj.user_id:
            return '-'
        return format_html(
            '<a href="/admin/auth/user/{}/change/">{}</a>',
            obj.user_id,
            obj.user.username
        )
    creator_link.short_description = 'Creator (Link)'

    def user_username(self, obj):
        return obj.user.username if obj.user_id else ''
    user_username.short_description = 'username'

    def user_first_name(self, obj):
        return obj.user.first_name if obj.user_id else ''
    user_first_name.short_description = 'first_name'

    def user_last_name(self, obj):
        return obj.user.last_name if obj.user_id else ''
    user_last_name.short_description = 'last_name'


@admin.register(OfferDetail)
class OfferDetailAdmin(admin.ModelAdmin):
    """Provides separate Admin for OfferDetail"""
    list_display = ('id', 'offer', 'name', 'price', 'delivery_time')
    list_select_related = ('offer', 'offer__user')
    search_fields = (
        'name',
        'offer__title',
        'offer__user__username',
    )
    list_filter = ('delivery_time',)
    ordering = ('offer_id', 'id')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """Provides Admin columns for Orders"""
    list_display = ('id', 'title', 'customer_user', 'business_user', 'status', 'created_at')
    list_filter = ('status', 'offer_type', 'created_at')
    search_fields = ('title', 'customer_user__username', 'business_user__username')
    
    
@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    """Provides Admin columns for Reviews"""
    list_display = (
        'id',
        'business_username',
        'reviewer_username',
        'rating',
        'updated_at',
        'created_at',
    )
    ordering = ('-updated_at',)
    list_select_related = ('business_user', 'reviewer')
    search_fields = (
        'description',                
        'business_user__username', 
        'reviewer__username',       
        'business_user__first_name',
        'business_user__last_name', 
        'reviewer__first_name',     
        'reviewer__last_name',      
    )
    list_filter = ('rating', 'created_at', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'business_link', 'reviewer_link')
    fieldsets = (
        ('Beziehung', {
            'fields': ('business_user', 'reviewer', 'business_link', 'reviewer_link')
        }),
        ('Bewertung', {
            'fields': ('rating', 'description')
        }),
        ('System', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def business_username(self, obj):
        return obj.business_user.username if obj.business_user_id else '-'
    business_username.short_description = 'Business'
    business_username.admin_order_field = 'business_user__username'

    def reviewer_username(self, obj):
        return obj.reviewer.username if obj.reviewer_id else '-'
    reviewer_username.short_description = 'Reviewer'
    reviewer_username.admin_order_field = 'reviewer__username'

    def business_link(self, obj):
        if not obj.business_user_id:
            return '-'
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>',
                           obj.business_user_id, obj.business_user.username)
    business_link.short_description = 'Business (Link)'

    def reviewer_link(self, obj):
        if not obj.reviewer_id:
            return '-'
        return format_html('<a href="/admin/auth/user/{}/change/">{}</a>',
                           obj.reviewer_id, obj.reviewer.username)
    reviewer_link.short_description = 'Reviewer (Link)'