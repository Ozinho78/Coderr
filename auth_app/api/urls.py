from django.urls import path
from auth_app.api.views import RegistrationView


urlpatterns = [
    path('registration/', RegistrationView.as_view(), name='registration'),
]


