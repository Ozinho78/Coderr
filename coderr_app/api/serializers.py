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
        
        
# PrimaryKeyRelatedField(read_only=True) sorgt dafür, dass IDs (nicht verschachtelte Objekte) ausgegeben werden – exakt wie in deiner Response-Vorgabe.
# fields decken 1:1 die geforderten Felder ab.
class OrderListSerializer(serializers.ModelSerializer):
    # Wir wollen reine IDs zurückgeben (passt zur Vorgabe)
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
        
        
# --- NEW: Eingabe-Serializer nur für POST /api/orders/ -----------------------
# Wir wollen nur die ID entgegennehmen. Alles andere holen wir aus dem OfferDetail/Offer/User.
# (Deine bestehende Ausgabe-Struktur für Orders behalten wir mit OrderListSerializer bei. Siehe Datei: OrderListSerializer existiert bereits und enthält genau die von dir gewünschte Feldauswahl.
class OrderCreateInputSerializer(serializers.Serializer):
    # akzeptiert genau ein Feld im Body: offer_detail_id
    offer_detail_id = serializers.IntegerField(required=True, min_value=1)  # Pflichtfeld, ganze Zahl >= 1
    

# Dein Order-Modell enthält die Status-Choices, daran validieren wir.
# Extra-Schutz: es wird wirklich nur status akzeptiert.    
# class OrderStatusPatchSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Order
#         fields = ('status',)  # nur dieses Feld patchbar

#     def validate_status(self, value):
#         # Erlaubte Werte direkt aus dem Modell (Choices: pending, in_progress, delivered, completed, cancelled)
#         valid = {choice[0] for choice in Order._meta.get_field('status').choices}  # siehe Modell-Choices :contentReference[oaicite:1]{index=1}
#         if value not in valid:
#             raise serializers.ValidationError('Ungültiger Status.')
#         return value

#     def validate(self, attrs):
#         # Sicherheit: nur 'status' zulassen – falls jemand mehr schickt, brettern wir 400 raus
#         if set(attrs.keys()) != {'status'}:
#             raise serializers.ValidationError('Nur das Feld "status" darf aktualisiert werden.')
#         return attrs


# ChoiceField(..., error_messages={'invalid_choice': 'Ungültiger Status.'}) sorgt dafür, dass dein Test-Assert den deutschen Text findet.
# Über self.initial_data sehen wir auch Felder, die der Serializer nicht kennt (z. B. price) und können sauber 400 werfen – genau das erwartet dein Test.
# Diese Änderung lässt die View unverändert funktionieren, denn sie benutzt ohnehin OrderStatusPatchSerializer(order, data=..., partial=True)
class OrderStatusPatchSerializer(serializers.Serializer):
    # ChoiceField mit deutscher Fehlermeldung beim invalid_choice
    status = serializers.ChoiceField(
        choices=Order._meta.get_field('status').choices,
        error_messages={'invalid_choice': 'Ungültiger Status.'}
    )

    def validate(self, attrs):
        # nur 'status' erlauben – alle anderen Keys führen zu 400 (non_field_errors)
        allowed = {'status'}
        extras = set(getattr(self, 'initial_data', {}).keys()) - allowed
        if extras:
            # landet im Test unter res.json()['non_field_errors'][0]
            raise serializers.ValidationError('Nur das Feld "status" darf aktualisiert werden.')
        return attrs
    
    def update(self, instance, validated_data):
    # einzig erlaubtes Feld setzen
        instance.status = validated_data['status']
        # updated_at wird dank auto_now aktualisiert
        instance.save(update_fields=['status', 'updated_at'])
        return instance
    
    
class ReviewListSerializer(serializers.ModelSerializer):
    # Wir geben nur IDs aus (kein Nested-Objekt → wie in deiner Vorgabe)
    business_user = serializers.PrimaryKeyRelatedField(read_only=True)  # int
    reviewer = serializers.PrimaryKeyRelatedField(read_only=True)       # int

    class Meta:
        model = Review
        fields = ('id', 'business_user', 'reviewer', 'rating', 'description', 'created_at', 'updated_at')

    # Sicherheits-/Daten-Validierung (falls du später POST zulässt; fürs GET unschädlich)
    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating muss zwischen 1 und 5 liegen.')
        return value

    def validate(self, attrs):
        # Schutz gegen Selbstbewertung (falls später POST kommt)
        business = attrs.get('business_user') or getattr(self.instance, 'business_user', None)
        reviewer = attrs.get('reviewer') or getattr(self.instance, 'reviewer', None)
        if business and reviewer and getattr(business, 'id', None) == getattr(reviewer, 'id', None):
            raise serializers.ValidationError({'non_field_errors': ['Reviewer darf sich nicht selbst bewerten.']})
        return attrs
    
    
class ReviewCreateSerializer(serializers.ModelSerializer):
    # Input: business_user als ID, rating 1..5, description optional
    business_user = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=True)

    class Meta:
        model = Review
        fields = ('id', 'business_user', 'rating', 'description')  # reviewer/ts kommen serverseitig

    def validate_rating(self, value):
        # Range 1..5 sicherstellen
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating muss zwischen 1 und 5 liegen.')
        return value

    def validate(self, attrs):
        # Aktueller User (als Reviewer)
        request = self.context.get('request')
        reviewer = getattr(request, 'user', None)
        business_user = attrs.get('business_user')

        # muss eingeloggt sein
        if not reviewer or not reviewer.is_authenticated:
            # DRF kümmert sich i.d.R. um 401 via Permission, aber hier als Fallback
            raise serializers.ValidationError({'detail': 'Authentication required.'})

        # Reviewer-Profil muss 'customer' sein
        r_profile = Profile.objects.filter(user=reviewer).first()
        if not r_profile or r_profile.type != 'customer':
            # laut Vorgabe: nur Kunden dürfen erstellen → 401/403; wir geben 403 zurück
            raise serializers.ValidationError({'detail': 'Nur Kunden dürfen Bewertungen erstellen.'})

        # Business muss existieren und ein Business-Profil haben
        b_profile = Profile.objects.filter(user=business_user).first()
        if not b_profile or b_profile.type != 'business':
            raise serializers.ValidationError({'business_user': 'Kein gültiger Business-Benutzer.'})

        # keine Selbstbewertung
        if reviewer.id == business_user.id:
            raise serializers.ValidationError({'non_field_errors': ['Eigene Profile dürfen nicht bewertet werden.']})

        # Einmal pro (reviewer,business_user)
        if Review.objects.filter(business_user=business_user, reviewer=reviewer).exists():
            # laut Vorgabe: 400 möglich, wenn bereits bewertet
            raise serializers.ValidationError({'non_field_errors': ['Es existiert bereits eine Bewertung für dieses Geschäftsprofil.']})

        return attrs

    def create(self, validated_data):
        # reviewer aus request übernehmen
        reviewer = self.context['request'].user
        return Review.objects.create(reviewer=reviewer, **validated_data)


class ReviewUpdateSerializer(serializers.ModelSerializer):
    # Nur diese Felder dürfen verändert werden
    class Meta:
        model = Review
        fields = ('rating', 'description')          # business_user/reviewer bleiben unverändert
        extra_kwargs = {
            'description': {'required': False, 'allow_blank': True},
        }

    def validate(self, attrs):
        # Nur die erlaubten Keys akzeptieren → alles andere 400
        allowed = {'rating', 'description'}
        extras = set(getattr(self, 'initial_data', {}).keys()) - allowed
        if extras:
            raise serializers.ValidationError('Nur die Felder "rating" und "description" dürfen aktualisiert werden.')
        return attrs

    def validate_rating(self, value):
        if value < 1 or value > 5:
            raise serializers.ValidationError('Rating muss zwischen 1 und 5 liegen.')
        return value
    
