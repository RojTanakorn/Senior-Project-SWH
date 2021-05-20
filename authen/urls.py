from django.urls import path
from . import views

urlpatterns = [
    path('token/', views.UserLogin.as_view()),
    path('hardware-ticket/', views.VerifyHardwareAndGetTicket.as_view()),
    path('get_user_image/', views.GetUserImage.as_view()),
]