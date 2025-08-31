from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import Profile


class ProfileInline(admin.StackedInline):
    """Shows user inline profile"""
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


class UserAdmin(BaseUserAdmin):
    """Shows user profile"""
    inlines = (ProfileInline,)
    list_display = BaseUserAdmin.list_display + ('get_profile_type', 'get_fullname_fallback')
    list_select_related = ('profile',)
    list_filter = BaseUserAdmin.list_filter + ('profile__type',)

    def get_profile_type(self, obj):
        return getattr(obj.profile, 'type', '-')
    get_profile_type.short_description = 'Profil-Typ'

    def get_fullname_fallback(self, obj):
        fn = (obj.first_name or '').strip()
        ln = (obj.last_name or '').strip()
        full = f'{fn} {ln}'.strip()
        return full if full else obj.username
    get_fullname_fallback.short_description = 'Voller Name'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    """Shows user profile with useful fields"""
    list_display = ('user', 'type', 'location', 'tel')
    search_fields = ('user__username', 'user__email', 'location')
    list_filter = ('type',)
