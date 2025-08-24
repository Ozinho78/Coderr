from django.contrib.auth.models import User
from django.db import models

class Profile(models.Model):
    TYPE_CHOICES = (("customer", "Customer"), ("business", "Business"))
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return f"{self.user.username} ({self.type})"