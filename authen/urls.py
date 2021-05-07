from django.urls import path
from . import views

urlpatterns = [
    path('token/', views.ObtainExpiringAuthToken.as_view()),
    path('hardware-ticket/', views.UserTokenAuthentication.as_view()),
    path('get_user_image/', views.GetUserImage.as_view()),
]