from django.urls import path
from coderr_app.api.views import (
    ProfileDetailView,
    BusinessProfileListView,
    CustomerProfileListView,
    OfferListCreateView,
    OfferRetrieveView,
    OfferDetailRetrieveView
)


urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),   # /api/profile/<pk>/
    path('profiles/business/', BusinessProfileListView.as_view(), name='profiles-business'),  # /api/profiles/business/
    path('profiles/customer/', CustomerProfileListView.as_view(), name='profiles-customer'),  # /api/profiles/customer/
    path('offers/', OfferListCreateView.as_view(), name='offers-list-create'),  # GET /api/offers/
    path('offers/<int:pk>/', OfferRetrieveView.as_view(), name='offers-detail'), # GET /api/offers/<pk>/
    path('offerdetails/<int:pk>/', OfferDetailRetrieveView.as_view(), name='offerdetails-detail'),
]