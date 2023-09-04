from django.shortcuts import render
from rest_framework import generics,status,viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view
from .models import CustomUser
from .serializers import UserSerializer,PasswordResetSerializer,AccountUpdatesSerializer
from django.core.mail import send_mail
from django.conf import settings
import random
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django_otp.plugins.otp_totp.models import TOTPDevice
from twilio.rest import Client
import phonenumbers
from .models import CustomUser
from django.utils import timezone
from phonenumbers import NumberParseException

from rest_framework.views import APIView
from django.utils.crypto import get_random_string
from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated

@api_view(['POST'])
def register_user(request):
    if request.method == 'POST':
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            otp = ''.join(random.choices('0123456789',k=6))

            subject = 'Email Verification OTP'
            message = f'Your OTP for email verification is: {otp}'
            from_email = settings.EMAIL_HOST_USER
            recipient_list = [user.email]

            send_mail(subject,message,from_email,recipient_list,fail_silently=False)
            print(serializer)

            return Response({'message':'User register successfully. check your email for OTP verification'},status=status.HTTP_201_CREATED)
        return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)

from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes

@api_view(['POST'])
def password_reset_mode(request):
    serializer = PasswordResetSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            user = None
        if user:
            token = urlsafe_base64_encode(force_bytes(user.pk))

            reset_link = f"http://yourdomain.com/reset-password/{token}/"
            send_mail(
                "Password Reset Request",
                f"Click the following link to reset your password: {reset_link}",
                "from@example.com",
                [email],
                fail_silently=False,
            )
            return Response({'message':'Password reset email sent successfully.'},status=status.HTTP_200_OK)
        else:
            return Response({'error':'User not found.'},status=status.HTTP_404_NOT_FOUND)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


CustomUser = get_user_model()

@csrf_exempt
def send_otp(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        if not phone_number:
            return JsonResponse({'message':'phone number is required.'},status=400)
        try:
            parsed_phone_number = phone_number.parse(phone_number, None)
            if not phonenumbers.is_valid_number(parsed_phone_number):
                return JsonResponse({'message':'Invalid phone number.'},status=400)
        except NumberParseException:
            return JsonResponse({'message': 'Invalid phone number format.'},status=400)

        user, created = CustomUser.objects.get_or_create(phone_number=phone_number)
        otp = get_random_string(length=6, allowed_chars='0123456789')
        user.otp = otp
        user.otp_valid_until = timezone.now() + timezone.timedelta(minutes=5)
        user.save()

        # use twilio to send the otp via sms
        client = Client(settings.TWILIO_ACCOUNT_STD, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f'Your OTP is: {otp}',
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number
        )


        # send otp via twilio sms

        client = Client(settings.TWILIO_ACCOUNT_STD, settings.TWILIO_AUTH_TOKEN)
        message = client.messages.create(
            body=f'Your OTP is: {otp}',
            from_=settings.TWILIO_PHONE_NUMBER,
            to=phone_number,
        )

        return JsonResponse({'message': 'OTP sent successfully'},status=200)
    return JsonResponse({'error':'Invalid request method'},status=405)


@csrf_exempt
def verify_otp(request):
    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        otp = request.POST.get('otp')
        if not phone_number or not otp:
            return JsonResponse({'message': 'phone number and OTP are required.'}, status=400)
        
        user = get_object_or_404(CustomUser, phone_number=phone_number)
        if user.otp != otp:
            return JsonResponse({'message': 'Invalid OTP.'}, status=400)
        
        if timezone.now() > user.otp_valid_until:
            return JsonResponse({'message': 'OTP has expired.'}, status=400)
        
        user.otp = None
        user.otp_valid_until = None
        user.save()

        #Authenticate the user 
        authenticated_user = authenticate(request, username=username, password=user.password)
        login(request, authenticated_user)

        return JsonResponse({'message':'otp verification successfully'},status=200)
        





class AccountUpdateViewsSet(viewsets.ModelViewSet):
    serializer_class = AccountUpdatesSerializer
    #permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CustomUser.objects.filter(id=self.request.user.id)
    
    def update(self, request, *args, **kwargs):
        isinstance = self.get_objects()
        serializer = self.get_serializer(isinstance, data=request.data, partial=True)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        else:
            return Response(serializer. errors, status=status.HTTP_400_BAD_REQUEST)