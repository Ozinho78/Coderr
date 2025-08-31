"""Contains all authorization and authentification urls"""
from django.urls import path
from auth_app.api.views import RegistrationView, LoginView


urlpatterns = [
    path('registration/', RegistrationView.as_view(), name='registration'),
    path('login/', LoginView.as_view(), name='login'),
]