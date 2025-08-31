"""Provides all urls for main app"""
from django.urls import path
from coderr_app.api.views import (
    ProfileDetailView,
    BusinessProfileListView,
    CustomerProfileListView,
    OfferListCreateView,
    OfferRetrieveView,
    OfferDetailRetrieveView,
    OrderListView,
    OrderListCreateView,
    OrderStatusUpdateView,
    OrderInProgressCountView,
    CompletedOrderCountView,
    ReviewListView,
    ReviewDetailView,
    BaseInfoView,
)


urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),
    path('profiles/business/', BusinessProfileListView.as_view(), name='profiles-business'),
    path('profiles/customer/', CustomerProfileListView.as_view(), name='profiles-customer'),
    path('offers/', OfferListCreateView.as_view(), name='offers-list-create'),
    path('offers/<int:pk>/', OfferRetrieveView.as_view(), name='offers-detail'),
    path('offerdetails/<int:pk>/', OfferDetailRetrieveView.as_view(), name='offerdetails-detail'),
    path('orders/', OrderListCreateView.as_view(), name='orders-list-create'),
    path('orders/<int:pk>/', OrderStatusUpdateView.as_view(), name='orders-status-update'),
    path('order-count/<int:business_user_id>/', OrderInProgressCountView.as_view(), name='orders-in-progress-count'),
    path('completed-order-count/<int:business_user_id>/', CompletedOrderCountView.as_view(), name='orders-completed-count'),
    path('reviews/', ReviewListView.as_view(), name='reviews-list'),
    path('reviews/<int:pk>/', ReviewDetailView.as_view(), name='reviews-detail'),
    path('base-info/', BaseInfoView.as_view(), name='base-info'),
]