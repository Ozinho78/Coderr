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
)


urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),   # /api/profile/<pk>/
    path('profiles/business/', BusinessProfileListView.as_view(), name='profiles-business'),  # /api/profiles/business/
    path('profiles/customer/', CustomerProfileListView.as_view(), name='profiles-customer'),  # /api/profiles/customer/
    path('offers/', OfferListCreateView.as_view(), name='offers-list-create'),  # GET /api/offers/
    path('offers/<int:pk>/', OfferRetrieveView.as_view(), name='offers-detail'), # GET /api/offers/<pk>/
    path('offerdetails/<int:pk>/', OfferDetailRetrieveView.as_view(), name='offerdetails-detail'),
    # path('orders/', OrderListView.as_view(), name='orders-list'),  # GET /api/orders/
    path('orders/', OrderListCreateView.as_view(), name='orders-list-create'),  # <<< CHANGE (GET + POST)
    path('orders/<int:pk>/', OrderStatusUpdateView.as_view(), name='orders-status-update'),
    path('order-count/<int:business_user_id>/', OrderInProgressCountView.as_view(), name='orders-in-progress-count'),
]


# Was passiert beim Löschen von Offers (http://127.0.0.1:8000/api/offers/66/)?
# 204 No Content: DRF’s DestroyModelMixin (in RetrieveUpdateDestroyAPIView) antwortet standardkonform ohne Body.
# 401: Kein Token → IsAuthenticated.
# 403: Eingeloggt, aber nicht der Ersteller → IsOwnerOrReadOnly. (Du importierst diese Permission bereits in der Datei.)
# 404: Unbekannte ID → handled automatisch.
# 500: Unerwartet → dein globaler Handler.
# Cascade: Durch dein Modell werden zugehörige OfferDetail-Einträge automatisch mitgelöscht (ForeignKey(..., on_delete=models.CASCADE, related_name='details')).