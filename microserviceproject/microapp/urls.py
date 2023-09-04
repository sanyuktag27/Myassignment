
from django.urls import path , include
from .views import *
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'account', AccountUpdateViewsSet, basename='user')

urlpatterns = [
    path('register/', register_user,name='register'),
    path('password_reset/',password_reset_mode,name='password_reset_request'),
    path('send-otp/',send_otp,name='send_otp'),
    path('verify-otp/', verify_otp, name= 'verify_otp'),
    path('', include(router.urls)),
]
