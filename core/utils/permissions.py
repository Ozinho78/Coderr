from rest_framework.permissions import SAFE_METHODS, BasePermission  # Basis für eigene Permissions

class IsOwnerOrReadOnly(BasePermission):                              # nur Owner darf schreibend zugreifen
    message = 'Forbidden: not the owner of this profile.'             # 403-Fehlermeldung

    def has_object_permission(self, request, view, obj):              # objektbezogene Prüfung
        if request.method in SAFE_METHODS:                            # GET/HEAD/OPTIONS → immer erlaubt
            return True
        return getattr(obj, 'user_id', None) == getattr(request.user, 'id', None)  # PATCH/PUT/DELETE nur Owner
