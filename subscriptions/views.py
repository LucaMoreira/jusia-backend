from re import DEBUG
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from accounts.decorators import get_auth
from accounts.models import CustomUser
from .utils import Stripe, stripe
from .models import Subscription

stripe_api = Stripe()

HEADERS: dict = {
    "Access-Control-Allow-Origin": settings.FRONTEND_URL,
    "Access-Control-Allow-Methods": "POST, PUT, PATCH, GET, DELETE, OPTIONS",
    "Access-Control-Allow-Headers": "Origin, X-Api-Key, X-Requested-With, Content-Type, Accept, Authorization"
    }
SUCCESS: int = status.HTTP_200_OK
ERROR: int = status.HTTP_400_BAD_REQUEST

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    data = request.data
    try:
        # Check if this is a plan change
        is_plan_change = data.get('is_plan_change', 'false').lower() == 'true'
        
        # Build success URL with plan change parameter if needed
        success_url = settings.FRONTEND_URL + '/success?session_id={CHECKOUT_SESSION_ID}'
        if is_plan_change:
            success_url += '&change_plan=true'
        
        checkout_session = stripe.checkout.Session.create(
            line_items = [
                {
                'price' : data['price_id'],
                'quantity' : 1
                }
            ],
            mode = 'subscription', 
            success_url = success_url,
            cancel_url  = settings.FRONTEND_URL + '/failure'       
        )
        return Response({'url': checkout_session.url}, status=SUCCESS, headers=HEADERS)
    except Exception as e:
        if (settings.DEBUG): print("Error: ", e)
        return Response(status=ERROR, headers=HEADERS)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_subscription(request):
    try:
        user = request.user
        subscription = Subscription.objects.get(user=user, status__name='active')
        
        # Get basic subscription data from database
        data = {
            'id': subscription.id,
            'plan_name': subscription.plan.name,
            'plan_price': float(subscription.plan.price),
            'currency': subscription.plan.currency,
            'status': subscription.status.name,
            'stripe_subscription_id': subscription.stripe_subscription_id,
            'created_at': subscription.created_at.isoformat(),
            'current_period_start': None,  # Will be populated from Stripe if needed
            'current_period_end': None,    # Will be populated from Stripe if needed
            'cancel_at_period_end': False, # Will be populated from Stripe if needed
            'canceled_at': None,           # Will be populated from Stripe if needed
        }
        
        # Try to get additional data from Stripe if available
        try:
            stripe_sub = stripe.Subscription.retrieve(subscription.stripe_subscription_id)
            
            # Update with Stripe data if available
            if hasattr(stripe_sub, 'current_period_start') and stripe_sub.current_period_start:
                data['current_period_start'] = int(stripe_sub.current_period_start)
            if hasattr(stripe_sub, 'current_period_end') and stripe_sub.current_period_end:
                data['current_period_end'] = int(stripe_sub.current_period_end)
            if hasattr(stripe_sub, 'cancel_at_period_end'):
                data['cancel_at_period_end'] = bool(stripe_sub.cancel_at_period_end)
            if hasattr(stripe_sub, 'canceled_at') and stripe_sub.canceled_at:
                data['canceled_at'] = int(stripe_sub.canceled_at)
                
        except Exception as stripe_error:
            if settings.DEBUG:
                print(f"Stripe API error (non-critical): {stripe_error}")
            # Continue with basic data from database
        
        return Response(data, status=SUCCESS, headers=HEADERS)
    except Subscription.DoesNotExist:
        return Response(data={'message': 'No active subscription found.'}, status=status.HTTP_404_NOT_FOUND, headers=HEADERS)
    except Exception as e:
        if (settings.DEBUG): 
            print("Error: ", e)
            import traceback
            traceback.print_exc()
        return Response(data={'error': str(e)}, status=ERROR, headers=HEADERS)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_subscription(request):
    try:
        user = request.user
        subscription = Subscription.objects.get(user=user, status__name='active')
        subscription.cancel()
        return Response(status=SUCCESS, headers=HEADERS)
    except Subscription.DoesNotExist:
        return Response(data={'message': 'Active subscription not found.'}, status=status.HTTP_404_NOT_FOUND, headers=HEADERS)
    except Exception as e:
        if (settings.DEBUG): print("Error: ", e)
        return Response(status=ERROR, headers=HEADERS)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def validate_stripe_payment(request):
    try:
        # Get session_id from different possible sources
        session_id = (request.data.get('session_id') or 
                     request.data.get('id') or 
                     request.data.get('sessionId'))
        
        if not session_id:
            raise Exception("Session ID not provided")
            
        session = stripe.checkout.Session.retrieve(session_id)

        if not session: 
            raise Exception("Session not found")

        stripe_subscription_id = session.subscription
        user = request.user
        
        # Check if this is a plan change (user already has an active subscription)
        is_plan_change = request.data.get('is_plan_change', 'false').lower() == 'true'
        old_subscription = None
        
        # Only proceed with plan change if user actually has an active subscription
        if is_plan_change:
            try:
                old_subscription = Subscription.objects.get(user=user, status__name='active')
                print(f"Plan change detected. Old subscription: {old_subscription.id}")
            except Subscription.DoesNotExist:
                print("Plan change requested but no active subscription found - treating as new subscription")
                is_plan_change = False  # Treat as new subscription, not a plan change
        
        # Try to get existing subscription or create new one
        try:
            subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
            # If subscription exists, just activate it
            subscription.activate()
        except Subscription.DoesNotExist:
            # Create new subscription
            from .models import Plan, SubscriptionStatus
            
            # Get the plan from the session
            line_items = stripe.checkout.Session.list_line_items(session_id)
            if not line_items.data:
                raise Exception("No line items found in session")
            
            price_id = line_items.data[0].price.id
            
            # Find or create plan
            plan, created = Plan.objects.get_or_create(
                stripe_price_id=price_id,
                defaults={
                    'name': f'Plan {price_id}',
                    'price': line_items.data[0].amount_total / 100,  # Convert from cents
                    'currency': line_items.data[0].currency,
                }
            )
            
            # Get or create active status
            status, created = SubscriptionStatus.objects.get_or_create(
                name='active',
                defaults={'name': 'active'}
            )
            
            # Create subscription with get_or_create to handle duplicates
            subscription, created = Subscription.objects.get_or_create(
                stripe_subscription_id=stripe_subscription_id,
                defaults={
                    'user': user,
                    'plan': plan,
                    'status': status,
                    'stripe_customer_id': session.customer,
                }
            )
            
            if created:
                subscription.activate()
            else:
                # Subscription already exists, just activate it
                subscription.activate()

        # If this was a plan change and we have an old subscription, cancel it
        # Only cancel if:
        # 1. It's actually a plan change (is_plan_change = True)
        # 2. We found an old subscription
        # 3. The old subscription is different from the new one
        # 4. The old subscription is still active
        if (is_plan_change and 
            old_subscription and 
            old_subscription.id != subscription.id and
            old_subscription.status.name == 'active'):
            try:
                print(f"Canceling old subscription: {old_subscription.id}")
                old_subscription.cancel()
                print(f"Old subscription {old_subscription.id} canceled successfully")
            except Exception as cancel_error:
                print(f"Error canceling old subscription: {cancel_error}")
                # Don't fail the whole operation if we can't cancel the old subscription
                # The user will have two subscriptions but can manage them manually
        elif is_plan_change and not old_subscription:
            print("Plan change requested but no old subscription found - this is actually a new subscription")
        elif is_plan_change and old_subscription and old_subscription.id == subscription.id:
            print("Plan change requested but old and new subscriptions are the same - no cancellation needed")
        elif is_plan_change and old_subscription and old_subscription.status.name != 'active':
            print(f"Old subscription {old_subscription.id} is not active (status: {old_subscription.status.name}) - no cancellation needed")

        return Response(data={'message': 'Success'}, status=SUCCESS, headers=HEADERS)

    except Exception as e:
        if (settings.DEBUG): print("Error: ", e)
        return Response(data={'message': 'Error'}, status=ERROR, headers=HEADERS)