import os

from django.conf import settings
from django.conf import settings
from django.contrib.auth import logout
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.core.mail import send_mail as django_send_email
from rest_framework.request import Request
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken
import stripe

from subscriptions.models import Subscription, SubscriptionStatus

from .models import CustomUser

stripe.api_key = settings.STRIPE_PRIVATE_KEY

# Expire after 24h
TOKEN_EXPIRE = 86400

# * --- AUTHENTICATION --- *#
def is_authenticated(request: Request) -> tuple[bool, str | None]:
    """
    Check if user is authenticated.
    """
    auth_header = request.headers.get("Authorization")
    refresh_header = request.headers.get("X-Refresh-Token")
    
    print(f"is_authenticated - auth_header: {auth_header}")
    print(f"is_authenticated - refresh_header: {refresh_header}")

    if not auth_header or not auth_header.startswith("Bearer "):
        print("is_authenticated - No valid auth header")
        return False, None

    token_str = auth_header.split(" ")[1]
    print(f"is_authenticated - token_str: {token_str}")

    try:
        AccessToken(token_str)
        print("is_authenticated - Token is valid")
        return True, token_str
    except (TokenError, InvalidToken) as e:
        print(f"is_authenticated - Token error: {e}")
        if refresh_header:
            try:
                refresh_token = RefreshToken(refresh_header)
                new_access_token = str(refresh_token.access_token)
                print("is_authenticated - Refresh token is valid")
                return True, new_access_token
            except (TokenError, InvalidToken) as e2:
                print(f"is_authenticated - Refresh token error: {e2}")
                return False, None
        return False, None


def create_password_token(user):
    """
    Generate a password reset token for the given user.
    """
    generator = PasswordResetTokenGenerator()
    token = generator.make_token(user)
    return token


#* --- USER --- *#
def is_user_in_groups(username, groups):
    """
    Check if a user is in one of the given groups.
    """
    user = CustomUser.objects.get(username=username)
    
    if user.groups == None:
        return False
    
    for group in list(user.groups.all()):
        if str(group) in groups:
            return True
    
    return False


#* --- SUBSCRIPTION --- *#
def has_active_subscription(user):
    """
    Check if user has any active subscription by checking current status in database.
    """
    try:
        user_subscriptions = Subscription.objects.filter(user=user)
        
        if not user_subscriptions.exists():
            return False
        
        # Check if any subscription has active status
        active_status = SubscriptionStatus.objects.filter(name='active').first()
        if not active_status:
            return False
            
        has_active = user_subscriptions.filter(status=active_status).exists()
        
        return has_active
        
    except Exception as e:
        print(f"Error checking active subscription: {e}")
        return False


def renew_user_subscriptions(user):
    """
    Renew all user subscriptions from Stripe API.
    This should be called from webhooks or scheduled tasks, not from every auth check.
    """
    try:
        user_subscriptions = Subscription.objects.filter(user=user)
        
        if not user_subscriptions.exists():
            return False
        
        has_active = False
        
        for subscription in user_subscriptions:
            if not subscription.stripe_subscription_id:
                continue
                
            try:
                subscription.renew()
                
                if subscription.status == SubscriptionStatus.objects.get(name='active'):
                    has_active = True

            except Exception as e:
                print(f"Unexpected error updating subscription {subscription.id}: {e}")
                continue
        
        return has_active
        
    except Exception as e:
        print(f"Error renewing user subscriptions: {e}")
        return False


def file_exists(file_path):
    """
    Check if a file exists.
    """
    return True if os.path.exists(file_path) else False


def subscription_exists(id:str) -> bool:
    try:
        stripe.Subscription.retrieve(id)
        return True
    except:
        return False


def user_exists(email:str) -> bool:
    try:
        CustomUser.objects.get(email=email)
        return True
    except:
        return False


def user_with_username_exists(username) -> bool:
    try:
        CustomUser.objects.get(username=username)
        return True
    except:
        return False


def is_subscription_active(id:str) -> bool:
    try:
        subscription = stripe.Subscription.retrieve(id)
        status       = subscription['status']
    
    except Exception as e:
        return False
    
    if status == 'active':
        return True
    else:
        return False


def deactivate_user(user):
    user.status = False
    user.save()


def get_auth(request: Request) -> tuple[dict, str]:
    """
    Check user authorization.
    """

    user_is_authenticated, token = is_authenticated(request)

    if not user_is_authenticated:
        return {'auth': 'Visitor'}, "User is not authenticated"

    # Get user from token
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = CustomUser.objects.get(id=user_id)
    except (TokenError, InvalidToken, CustomUser.DoesNotExist):
        return {'auth': 'Visitor'}, "Invalid token or user not found"

    # Serializar dados do usuário
    from .serializers import UserSerializer
    user_data = UserSerializer(user).data

    # Por enquanto, sempre retornar como Client se estiver autenticado
    # TODO: Implementar verificação de subscription adequadamente
    return {'auth': 'Client', 'user': user_data}, "User is authenticated"


#* --- EMAIL --- *#
def send_email(recipient:str, subject:str, message:str) -> bool:
    """
    Send email to recipient using django host user email

    Args:
        reciever (str): email's reciever
        subject  (str): email's subject
        message  (str): email's message
    """
    try:
        django_send_email(
            subject=subject, 
            message=message, 
            from_email=settings.EMAIL_HOST_USER, 
            recipient_list=[recipient], 
            fail_silently=False
        )
        return True

    except:
        return False