from rest_framework import serializers
from django.contrib.auth import get_user_model
from auth_app.models import Profile
import os
from coderr_app.models import Offer, OfferDetail, Order, Review

User = get_user_model()

class ProfileDetailSerializer(serializers.ModelSerializer):
    """Serializes profile detail data"""
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    username = serializers.SerializerMethodField()
    email = serializers.EmailField(source='user.email', required=False)
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)
    file = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file',
            'location', 'tel', 'description', 'working_hours',
            'type', 'email', 'created_at',
        )
        extra_kwargs = {
            'location': {'required': False, 'allow_blank': True},
            'tel': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'working_hours': {'required': False, 'allow_blank': True},
        }

    def get_username(self, obj):
        return obj.user.username if getattr(obj, 'user', None) and obj.user.username else ''

    def get_file(self, obj):
        if not obj.file:
            return ''
        try:
            return os.path.basename(obj.file.name)
        except Exception:
            return str(obj.file) or ''

    def to_representation(self, instance):

        data = super().to_representation(instance)
        must_not_be_null = ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']
        for key in must_not_be_null:
            if data.get(key) is None:
                data[key] = ''
        return data

    def update(self, instance, validated_data):
        user_data = validated_data.pop('user', {}) if 'user' in validated_data else {}

        for field in ['location', 'tel', 'description', 'working_hours', 'file']:
            if field in validated_data:
                setattr(instance, field, validated_data[field])

        if user_data:
            if 'first_name' in user_data:
                instance.user.first_name = user_data['first_name'] or ''
            if 'last_name' in user_data:
                instance.user.last_name = user_data['last_name'] or ''
            if 'email' in user_data:
                instance.user.email = user_data['email']
            instance.user.save()

        instance.save()
        return instance


class ProfileListSerializer(serializers.ModelSerializer):
    """Serializes profile list data"""
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    username = serializers.SerializerMethodField()           
    first_name = serializers.CharField(source='user.first_name', required=False, allow_blank=True)
    last_name = serializers.CharField(source='user.last_name', required=False, allow_blank=True)  
    file = serializers.SerializerMethodField()               

    class Meta:
        model = Profile
        fields = (
            'user', 'username', 'first_name', 'last_name', 'file',
            'location', 'tel', 'description', 'working_hours',
            'type',
        )
        extra_kwargs = {
            'location': {'required': False, 'allow_blank': True},
            'tel': {'required': False, 'allow_blank': True},
            'description': {'required': False, 'allow_blank': True},
            'working_hours': {'required': False, 'allow_blank': True},
        }

    def get_username(self, obj):
        return obj.user.username if getattr(obj, 'user', None) else ''

    def get_file(self, obj):
        if not obj.file:
            return ''                                                 
        try:
            return os.path.basename(obj.file.name)                    
        except Exception:
            return str(obj.file) or ''                                

    def to_representation(self, instance):
        data = super().to_representation(instance)                    
        for key in ['first_name', 'last_name', 'location', 'tel', 'description', 'working_hours']:
            if data.get(key) is None:
                data[key] = ''
        return data
    
    
class OfferDetailMiniSerializer(serializers.ModelSerializer):
    """Serializes basic offer detail data"""
    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail
        fields = ('id', 'url')

    def get_url(self, obj):
        return f'/offerdetails/{obj.pk}/'


class OfferListSerializer(serializers.ModelSerializer):
    """Serializes offer list data"""
    details = OfferDetailMiniSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = Offer
        fields = (
            'id', 'user', 'title', 'image', 'description',
            'created_at', 'updated_at',
            'details',
            'min_price', 'min_delivery_time',
            'user_details',
        )

    def get_user_details(self, obj):
        u = getattr(obj, 'user', None)
        return {
            'first_name': (u.first_name or '') if u else '',
            'last_name': (u.last_name or '') if u else '',
            'username': (u.username or '') if u else '',
        }
        

class OfferDetailCreateSerializer(serializers.ModelSerializer):
    """Serializes offer detail data for creation"""
    class Meta:
        model = OfferDetail
        fields = (
            'id',  
            'title',
            'revisions',
            'delivery_time_in_days', 
            'price',                 
            'features',              
            'offer_type',            
        )

    def validate_features(self, value):
        if value is None:
            return []
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise serializers.ValidationError('features muss eine Liste aus Strings sein.')
        return value

    def validate(self, attrs):
        if attrs.get('price') is None or float(attrs['price']) < 0:
            raise serializers.ValidationError({'price': 'Preis muss >= 0 sein.'})
        if attrs.get('delivery_time_in_days') in (None, ''):
            raise serializers.ValidationError({'delivery_time_in_days': 'Pflichtfeld.'})
        if attrs.get('offer_type') not in ('basic', 'standard', 'premium'):
            raise serializers.ValidationError({'offer_type': 'Ungültig (basic|standard|premium).'})
        return attrs


class OfferCreateSerializer(serializers.ModelSerializer):
    """Serializes offer data for creation"""
    details = OfferDetailCreateSerializer(many=True)

    class Meta:
        model = Offer
        fields = ('id', 'title', 'image', 'description', 'details')

    def validate_details(self, value):
        if not isinstance(value, list) or len(value) != 3:
            raise serializers.ValidationError('Ein Offer muss genau 3 Details enthalten.')
        types = [d.get('offer_type') for d in value]
        if set(types) != {'basic', 'standard', 'premium'}:
            raise serializers.ValidationError('Die 3 Details müssen basic, standard und premium enthalten (jeweils einmal).')
        return value

    def create(self, validated_data):
        request = self.context.get('request')
        user = getattr(request, 'user', None)
        details_data = validated_data.pop('details')
        offer = Offer.objects.create(user=user, **validated_data)
        objs = []
        for d in details_data:
            dt_days = d.get('delivery_time_in_days')
            objs.append(OfferDetail(
                offer=offer,
                title=d.get('title'),
                revisions=d.get('revisions', 0),
                delivery_time_in_days=dt_days,
                delivery_time=dt_days,          
                price=d.get('price'),
                features=d.get('features', []),
                offer_type=d.get('offer_type'),
            ))
        OfferDetail.objects.bulk_create(objs)
        offer.refresh_from_db()
        return offer
    
  
class OfferDetailMiniAbsSerializer(serializers.ModelSerializer):
    """Serializes basic offer detail data"""
    url = serializers.SerializerMethodField()

    class Meta:
        model = OfferDetail              
        fields = ('id', 'url')           

    def get_url(self, obj):              
        request = self.context.get('request')
        path = f'/api/offerdetails/{obj.pk}/'
        return request.build_absolute_uri(path) if request else path


class OfferRetrieveSerializer(serializers.ModelSerializer):           
    """Serializes offer data for retrieving"""
    details = OfferDetailMiniAbsSerializer(many=True, read_only=True)
    min_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    min_delivery_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = Offer                                            
        fields = (
            'id', 'user', 'title', 'image', 'description',
            'created_at', 'updated_at',
            'details', 'min_price', 'min_delivery_time',
        )


class OfferDetailRetrieveSerializer(serializers.ModelSerializer):
    """Serializes offer detail data for retrieving"""
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OfferDetail                                        
        fields = (
            'id',                    
            'title',                 
            'revisions',             
            'delivery_time_in_days',
            'price',                
            'features',             
            'offer_type',           
        )
        

class OfferDetailFullSerializer(serializers.ModelSerializer):
    """Serializes complete offer detail data"""
    price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = OfferDetail
        fields = (
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        )


class OfferDetailUpdateSerializer(serializers.ModelSerializer):
    """Serializes offer detail data for updating"""
    offer_type = serializers.ChoiceField(choices=('basic', 'standard', 'premium'), required=True)
    id = serializers.IntegerField(required=False)

    class Meta:
        model = OfferDetail
        fields = (
            'id',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
        )
        extra_kwargs = {
            'title': {'required': False, 'allow_blank': True},
            'revisions': {'required': False},
            'delivery_time_in_days': {'required': False},
            'price': {'required': False},
            'features': {'required': False},
        }

    def validate_features(self, value):
        if value is None:
            return None
        if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
            raise serializers.ValidationError('features muss eine Liste aus Strings sein.')
        return value


class OfferUpdateSerializer(serializers.ModelSerializer):
    """Serializes offer data for updating"""
    details = OfferDetailUpdateSerializer(many=True, required=False)

    class Meta:
        model = Offer
        fields = ('title', 'image', 'description', 'details')
        extra_kwargs = {
            'title': {'required': False, 'allow_blank': True},
            'image': {'required': False},
            'description': {'required': False, 'allow_blank': True},
        }

    def update(self, instance, validated_data):
        details_data = validated_data.pop('details', None)
        for f in ('title', 'image', 'description'):
            if f in validated_data:
                setattr(instance, f, validated_data[f])
        instance.save()

        if details_data:
            existing_by_type = {d.offer_type: d for d in instance.details.all()}
            allowed_types = {'basic', 'standard', 'premium'}

            for item in details_data:
                offer_type = item.get('offer_type')
                if offer_type not in allowed_types:
                    raise serializers.ValidationError({'details': f'offer_type ungültig: {offer_type}'})

                detail = existing_by_type.get(offer_type)
                if not detail:
                    raise serializers.ValidationError({'details': f'Kein Detail für offer_type="{offer_type}" vorhanden.'})

                if 'id' in item and item['id'] is not None and item['id'] != detail.id:
                    raise serializers.ValidationError({'details': f'ID {item["id"]} passt nicht zum offer_type="{offer_type}" (erwartet {detail.id}).'})

                for f in ('title', 'revisions', 'delivery_time_in_days', 'price', 'features'):
                    if f in item:
                        setattr(detail, f, item[f])

                if 'delivery_time_in_days' in item and item['delivery_time_in_days'] is not None:
                    detail.delivery_time = item['delivery_time_in_days']

                detail.save()

        return instance


class OfferPatchResponseSerializer(serializers.ModelSerializer):
    """Serializes offer data for patching"""
    details = OfferDetailFullSerializer(many=True, read_only=True)

    class Meta:
        model = Offer
        fields = (
            'id',
            'title',
            'image',
            'description',
            'details',
        )
        
        
class OrderListSerializer(serializers.ModelSerializer):
    """Serializes order list data"""
    customer_user = serializers.PrimaryKeyRelatedField(read_only=True)
    business_user = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Order
        fields = (
            'id',
            'customer_user',
            'business_user',
            'title',
            'revisions',
            'delivery_time_in_days',
            'price',
            'features',
            'offer_type',
            'status',
            'created_at',
            'updated_at',
        )
        
        
class OrderCreateInputSerializer(serializers.Serializer):
    """Serializes order detail id"""
    offer_detail_id = serializers.IntegerField(required=True, min_value=1)
    

class OrderStatusPatchSerializer(serializers.Serializer):
    """Serializes order status data"""
    status = serializers.ChoiceField(
        choices=Order._meta.get_field('status').choices,
        error_messages={'invalid_choice': 'Ungültiger Status.'}
    )

    def validate(self, attrs):
        allowed = {'status'}
        extras = set(getattr(self, 'initial_data', {}).keys()) - allowed
        if extras:
            raise serializers.ValidationError('Nur das Feld "status" darf aktualisiert werden.')
        return attrs
    
    def update(self, instance, validated_data):
        instance.status = validated_data['status']
        instance.save(update_fields=['status', 'updated_at'])
        return instance
    

class ReviewListSerializer(serializers.ModelSerializer):
    """Serializes review list data"""
    business_user = serializers.PrimaryKeyRelatedField(read_only=True)
    reviewer = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Review
        fields = ('id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at')

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating muss zwischen 1 und 5 liegen.')
        return value

    def validate(self, attrs):
        business = attrs.get('business_user') or getattr(self.instance, 'business_user', None)
        reviewer = attrs.get('reviewer') or getattr(self.instance, 'reviewer', None)
        if business and reviewer and getattr(business, 'id', None) == getattr(reviewer, 'id', None):
            raise serializers.ValidationError({'non_field_errors': ['Reviewer darf sich nicht selbst bewerten.']})
        return attrs
    
    
class ReviewCreateSerializer(serializers.ModelSerializer):
    """Serializes review create data"""
    business_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)

    class Meta:
        model = Review
        fields = ('id', 'business_user', 'rating', 'description')

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating muss zwischen 1 und 5 liegen.')
        return value

    def validate(self, attrs):
        request = self.context.get('request')
        reviewer = getattr(request, 'user', None)
        business_user = attrs.get('business_user')

        if not reviewer or not reviewer.is_authenticated:
            raise serializers.ValidationError({'detail': 'Authentication required.'})

        r_profile = Profile.objects.filter(user=reviewer).first()
        if not r_profile or r_profile.type != 'customer':
            raise serializers.ValidationError({'detail': 'Nur Kunden dürfen Bewertungen erstellen.'})

        b_profile = Profile.objects.filter(user=business_user).first()
        if not b_profile or b_profile.type != 'business':
            raise serializers.ValidationError({'business_user': 'Kein gültiger Business-Benutzer.'})

        if reviewer.id == business_user.id:
            raise serializers.ValidationError({'non_field_errors': ['Eigene Profile dürfen nicht bewertet werden.']})

        if Review.objects.filter(business_user=business_user, reviewer=reviewer).exists():
            raise serializers.ValidationError({'non_field_errors': ['Es existiert bereits eine Bewertung für dieses Geschäftsprofil.']})

        return attrs

    def create(self, validated_data):
        reviewer = self.context['request'].user
        return Review.objects.create(reviewer=reviewer, **validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    """Serializes review update data"""
    class Meta:
        model = Review
        fields = ('rating', 'description')
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        allowed = {'rating', 'description'}
        extras = set(getattr(self, 'initial_data', {}).keys()) - allowed
        if extras:
            raise serializers.ValidationError('Nur die Felder "rating" und "description" dürfen aktualisiert werden.')
        return attrs

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating muss zwischen 1 und 5 liegen.')
        return value
