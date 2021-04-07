from django.urls import path
from . import views

urlpatterns = [
    path('location_transfer/', views.Location_transfer_management),
]