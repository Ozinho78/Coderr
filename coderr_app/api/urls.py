from django.urls import path
from coderr_app.api.views import ProfileDetailView

urlpatterns = [
    path('profile/<int:pk>/', ProfileDetailView.as_view(), name='profile-detail'),
]