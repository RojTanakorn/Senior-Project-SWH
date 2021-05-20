from django.urls import path
from . import views

urlpatterns = [
    path('orders/', views.Order_receiving_management),
    path('location_transfer/', views.Location_transfer_management.as_view()),
]