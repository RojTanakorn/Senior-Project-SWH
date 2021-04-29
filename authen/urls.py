from django.urls import path
from . import views

urlpatterns = [
    path('token/', views.ObtainExpiringAuthToken.as_view()),
    path('hardware-ticket/', views.HardwareAndTicketAuthentication.as_view()),
]