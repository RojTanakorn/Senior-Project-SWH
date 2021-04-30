import datetime
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from rest_framework.authentication import TokenAuthentication
from rest_framework import exceptions
from django.contrib.auth.models import User
from modes.processes import commons
from db.models import HardwareData, UserData
import hashlib
import os
from django.core.cache import cache
from django.http.response import HttpResponse
from PIL import Image
from django.conf import settings


''' Class for authenticating username and password '''
class ObtainExpiringAuthToken(ObtainAuthToken):
    def post(self, request, *args, **kwargs):

        # Get serializer of request data
        serializer = self.serializer_class(data=request.data, context={'request': request})

        # If username and password is correct
        if serializer.is_valid(raise_exception=True):

            # Get user ID
            user = serializer.validated_data['user']

            # Initialize was_created (status shows token was created or not) and token
            was_created = True
            token = None

            # Try to get token object (if token was created for specific user)
            try:
                token = Token.objects.get(user=user)

            # Except when token has not been created
            except Token.DoesNotExist:
                was_created = False

                # Create token to user, convert created time, and get token object
                token = Create_token(user)

            # Get now local datetime
            now_local_datetime = commons.Get_now_local_datetime()

            # If token was created and token has expired (after 10 hours)
            if was_created and token.created < now_local_datetime - datetime.timedelta(hours=10):

                # Delete existing token, create a new one and store i
                token.delete()
                token = Create_token(user)

            # Return token, employee ID, and username
            return Response({
                'token': token.key,
                'user_id': user.pk,
                'name': user.first_name + ' ' + user.last_name,
                'is_superuser': user.is_superuser
            })


''' Function for creating token to specific user and returning token object '''
def Create_token(user):
    Token.objects.create(user=user)
    Token.objects.filter(user=user).update(created=commons.Get_now_local_datetime())
    token = Token.objects.get(user=user)

    return token


''' Class for authenticating expiring token '''
class ExpiringTokenAuthentication(TokenAuthentication):
    def authenticate_credentials(self, key):

        # Try to get token and raise the exception when token does not exist
        try:
            token = Token.objects.get(key=key)
        except Token.DoesNotExist:
            raise exceptions.AuthenticationFailed('Invalid token')

        # If user's token is inactive
        if not token.user.is_active:
            raise exceptions.AuthenticationFailed('User inactive or deleted')

        # If token has expired (after 10 hours)
        if token.created < commons.Get_now_local_datetime() - datetime.timedelta(hours=10):
            raise exceptions.AuthenticationFailed('Token has expired')

        return (token.user, token)


''' Class for checking hardware ID and token, and return ticket if verified '''
class HardwareAndTicketAuthentication(APIView):

    # Define authentication class as ExpiringTokenAuthentication, and permission class only authenticated client
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    # POST method process
    def post(self, request, format=None):
        
        # Try to get gardware object from sent hardware ID
        try:
            hardware = HardwareData.objects.get(hardwareid=request.data['hardware_id'])

        # Raise the exception when client does not send hardware ID
        except KeyError:
            raise exceptions.ParseError('Hardware ID is missing')

        # Raise the exception when sent hardware ID does not exist
        except HardwareData.DoesNotExist:
            raise exceptions.ParseError('Hardware ID does not exist')
        
        # Initialize is_ready status and ticket returned to client
        is_ready = False
        unhashed_ticket = None

        user_object = UserData.objects.filter(hardwareid=hardware.hardwareid).first()

        # If hardware is active and it is not binded to any employees (available for usage)
        if user_object is None:
            
            # Set is_ready to TRUE
            is_ready = True

            # Generate unhashed ticket for sending to client --> using MD5
            unhashed_ticket = hashlib.md5(
                (
                    request.META['REMOTE_ADDR'] +
                    str(commons.Get_now_local_datetime().timestamp())
                ).encode() + os.urandom(8)
            ).hexdigest()

            # Generate hashed ticket from unhashed for storing into CACHE (with TIMEOUT) --> using SHA256
            hashed_ticket = commons.Get_hashed_ticket(unhashed_ticket)

            # Store hashed ticket into CACHE
            cache.set(request.META['REMOTE_ADDR'], {'user_id': request.user.id, 'hashed_ticket': hashed_ticket})
        
        # Return response
        return Response({
            'hardware_id': hardware.hardwareid,
            'is_ready': is_ready,
            'ticket': unhashed_ticket
        })


''' Class for providing user image '''
class GetUserImage(APIView):
    
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):

        user = UserData.objects.filter(userid=request.user.id).values().first()
        response = HttpResponse(content_type="image/jpeg")

        user_image_path = str(user['userimagepath'] or '')

        try:
            img = Image.open(settings.BASE_DIR + '/' + user_image_path)
        except:
            img = Image.open(settings.BASE_DIR + '/user_images/user_default.jpg')

        img.save(response, "JPEG")
        return response