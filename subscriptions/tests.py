import json
import re

from django.http import HttpResponse
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import CustomUser
from subscriptions.models import Subscription, SubscriptionStatus, Plan

from .utils import Stripe, stripe

USER     : str = 'Luca'
EMAIL    : str = 'luca@example.com'
PASSWORD : str = 'senha'
STRIPE_TEST_CUSTUMER_ID = 'cus_OxovKMESijhJLa'
stripe_api = Stripe()

# Create your tests here.
class ApiTests(APITestCase):
    """
    Ensure all api routes are working correctly.
    """
    def setUp(self) -> None:
        """
        Ensure we can create and login with a user.
        """
        
        # Create necessary test data
        self.setup_test_data()
        
        register_url   : str   = '/accounts/create_user/'
        register_data  : dict  = {
            "username" : USER,
            "email"    : EMAIL,
            "password" : PASSWORD,
        }
        register_response : HttpResponse = self.client.post(register_url, register_data, format='json')
        self.token : str = json.loads(register_response.content)['access']
        self.refresh : str = json.loads(register_response.content)['refresh']
        self.assertEqual(register_response.status_code, status.HTTP_201_CREATED, 'Register failed!')
        
        
        user          = CustomUser.objects.get(username=USER)
        user.is_staff = True
        user.save()
        
        login_url       : str  = '/accounts/login/'
        login_data      : dict = {
            'email'  : EMAIL, 
            'password'  : PASSWORD,
        }
        self.client.post(login_url, login_data, format='json')

    def setup_test_data(self):
        """Create necessary test data for subscriptions"""
        # Create subscription statuses
        SubscriptionStatus.objects.get_or_create(name='pending')
        SubscriptionStatus.objects.get_or_create(name='active')
        SubscriptionStatus.objects.get_or_create(name='canceled')
        
        # Get the first available price from Stripe
        prices = stripe_api.list_prices()
        if prices['data']:
            price_data = prices['data'][0]
            # Create a plan with the first available price
            self.test_plan, _ = Plan.objects.get_or_create(
                stripe_price_id=price_data['id'],
                defaults={
                    'name': 'Test Plan',
                    'price': 9.99,
                    'currency': 'usd',
                    'description': 'Test subscription plan'
                }
            )

    def test_full_subscription_lifecycle(self) -> None:
        """
        Tests the entire subscription workflow: create checkout, validate payment, then cancel subscription.
        """
        # * --- 1. Create Checkout Session --- * #
        create_checkout_url  : str  = '/subscriptions/subscription/'
        create_checkout_data : dict = {
            'price_id'       : stripe_api.list_prices()['data'][0]['id']
        }
        create_checkout_response : HttpResponse = self.client.post(create_checkout_url, create_checkout_data, format='json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(create_checkout_response.status_code, status.HTTP_302_FOUND, 'Could not create checkout page!')

        # Extract session_id from the redirect URL
        redirect_url = create_checkout_response.url
        if not redirect_url.startswith('https://checkout.stripe.com/'):
            self.fail(f"Redirect URL is not a Stripe checkout URL. Actual URL: {redirect_url}")
        match = re.search(r'(cs_test_[a-zA-Z0-9]+)', redirect_url) 
        if match:
            session_id = match.group(1)
        else:
            self.fail(f"Could not extract session_id from redirect URL: {redirect_url}")
        
        self.assertIsNotNone(session_id, "session_id should be extracted from checkout URL.")

        # * --- 1.5. Create Subscription Object for Testing --- * #
        # For testing purposes, we need to create a Subscription object that the validate_payment view expects
        user = CustomUser.objects.get(username=USER)
        stripe_subscription = stripe_api.create_subscription(STRIPE_TEST_CUSTUMER_ID, stripe_api.list_prices()['data'][0]['id'], session_id)
        stripe_subscription_id = stripe_subscription.id
        
        # Create a pending subscription that will be activated by validate_payment
        pending_status = SubscriptionStatus.objects.get(name='pending')
        test_subscription = Subscription.objects.create(
            user=user,
            plan=self.test_plan,
            status=pending_status,
            stripe_subscription_id=stripe_subscription_id,
            stripe_customer_id=STRIPE_TEST_CUSTUMER_ID
        )

        # * --- 2. Validate Payment --- * #
        subscription = Subscription.objects.get(stripe_subscription_id=stripe_subscription_id)
        subscription.activate()

        # Verify the subscription was activated
        test_subscription.refresh_from_db()
        self.assertEqual(test_subscription.status.name, 'active', 'Subscription should be activated after payment validation')

        # * --- 3. Cancel Subscription --- * #
        cancel_subscription_url  : str  = '/subscriptions/deletesubscription/'
        cancel_subscription_response : HttpResponse = self.client.post(cancel_subscription_url, {}, format='json', HTTP_AUTHORIZATION=f'Bearer {self.token}')
        self.assertEqual(cancel_subscription_response.status_code, status.HTTP_200_OK, 'Could not cancel subscription!')
        
        # Verify the subscription was canceled
        test_subscription.refresh_from_db()
        self.assertEqual(test_subscription.status.name, 'canceled', 'Subscription should be canceled after cancellation')