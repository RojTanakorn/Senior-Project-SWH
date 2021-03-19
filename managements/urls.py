from django.urls import path
from . import views

urlpatterns = [
    path('orders/', views.Order_receiving_management),
]