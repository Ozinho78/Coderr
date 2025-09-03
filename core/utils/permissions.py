from rest_framework.permissions import SAFE_METHODS, BasePermission
from auth_app.models import Profile

class IsOwnerOrReadOnly(BasePermission):
    """Checks owner permission"""
    message = 'Forbidden: not the owner of this profile.'

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:              
            return True
        return getattr(obj, 'user_id', None) == getattr(request.user, 'id', None)


class IsBusinessUser(BasePermission):
    """Checks if user is business user"""
    message = 'Forbidden: only business users can create offers.'

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return Profile.objects.filter(user=request.user, type='business').exists()
    
    
class IsCustomerUser(BasePermission):
    message = 'Nur Kunden dürfen Bewertungen erstellen.'

    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        profile = Profile.objects.filter(user=request.user).first()
        return bool(profile and (profile.type or '').lower() == 'customer')