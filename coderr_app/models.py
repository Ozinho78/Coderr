from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class Offer(models.Model):
    """Defines model for Offer"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='offers')
    title = models.CharField(max_length=255)
    image = models.ImageField(upload_to='offers/', blank=True, null=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Offer #{self.pk} by {self.user_id}: {self.title[:30]}'


class OfferDetail(models.Model):
    """Defines model for OfferDetail"""
    offer = models.ForeignKey(Offer, on_delete=models.CASCADE, related_name='details')
    price = models.DecimalField(max_digits=10, decimal_places=2)                      
    delivery_time = models.PositiveIntegerField(help_text='Lieferzeit in Tagen')      
    name = models.CharField(max_length=120, blank=True)                               
    title = models.CharField(max_length=255, blank=True, null=True)           
    revisions = models.PositiveIntegerField(default=0)                        
    delivery_time_in_days = models.PositiveIntegerField(blank=True, null=True)
    features = models.JSONField(default=list, blank=True, null=True)          
    offer_type = models.CharField(                                            
        max_length=20,
        choices=(('basic', 'Basic'), ('standard', 'Standard'), ('premium', 'Premium')),
        blank=True,
        null=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['offer', 'offer_type'],
                name='unique_offer_offer_type',
                condition=~models.Q(offer_type__isnull=True),
            ),
        ]

    def __str__(self):
        return f'OfferDetail #{self.pk} of Offer #{self.offer_id} (price={self.price}, days={self.delivery_time})'


class Order(models.Model):
    """Defines model for Order"""
    customer_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_orders')
    business_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='business_orders')
    title = models.CharField(max_length=255)                
    revisions = models.PositiveIntegerField(default=0)      
    delivery_time_in_days = models.PositiveIntegerField()   
    price = models.DecimalField(max_digits=10, decimal_places=2)
    features = models.JSONField(default=list, blank=True, null=True)
    offer_type = models.CharField(                                  
        max_length=20,
        choices=(('basic', 'Basic'), ('standard', 'Standard'), ('premium', 'Premium'))
    )
    status = models.CharField(
        max_length=30,
        choices=(
            ('pending', 'Pending'),
            ('in_progress', 'In Progress'),
            ('delivered', 'Delivered'),
            ('completed', 'Completed'),
            ('cancelled', 'Cancelled'),
        ),
        default='in_progress',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Order #{self.pk} ({self.title}) c={self.customer_user_id} b={self.business_user_id}'
    

class Review(models.Model):
    """Defines model for Review"""
    business_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_reviews')
    reviewer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='written_reviews')
    rating = models.PositiveSmallIntegerField()
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['business_user']),                                                    
            models.Index(fields=['reviewer']),                                                         
            models.Index(fields=['updated_at']),                                                       
            models.Index(fields=['rating']),                                                           
        ]

    def __str__(self):
        return f'Review #{self.pk} b={self.business_user_id} r={self.reviewer_id} rating={self.rating}'