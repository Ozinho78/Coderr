from django.urls import path
from coderr_app.api.views import (
    ProfileDetailView,
    BusinessProfileListView,
    CustomerProfileListView,
)

urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),   # /api/profile/<pk>/
    path('profiles/business/', BusinessProfileListView.as_view(), name='profiles-business'),  # /api/profiles/business/
    path('profiles/customer/', CustomerProfileListView.as_view(), name='profiles-customer'),  # /api/profiles/customer/
]