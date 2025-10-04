# subscriptions/utils.py
import stripe
from django.conf import settings

STRIPE_TEST_CUSTUMER_ID = 'cus_OxovKMESijhJLa'
stripe.api_key          = settings.STRIPE_PRIVATE_KEY


class Stripe():
    def list_prices(self, limit:int=0):
        return stripe.Price.list() if limit == 0 else stripe.Price.list(limit=limit)


    def create_subscription(self, custumer_id, price_id, session_id):
        return stripe.Subscription.create(
            customer=custumer_id,
            items=[{'price': price_id}],
            metadata={'checkout_session_id': session_id}
        )


    def get_subscription(self, id:str):
        return stripe.Subscription.retrieve(id)


    def subscription_exists(self, id:str) -> bool:
        try:
            stripe.Subscription.retrieve(id)
            return True
        except:
            return False


    def create_customer(self, email: str = None):
        """
        Creates a new Stripe customer.
        Optionally takes an email for better customer record keeping in Stripe.
        """
        customer_params = {}
        if email:
            customer_params['email'] = email
        return stripe.Customer.create(**customer_params)


    def get_user(self, custumer_id):
        return stripe.Customer.retrieve(custumer_id)


    def get_product(self, id:str):
        return stripe.Product.retrieve(id)

    def cancel_subscription(self, subscription_id: str, at_period_end: bool = True):
        """
        Cancels a Stripe subscription.
        If at_period_end is True, the subscription will remain active until the end of the current billing period.
        If False, the subscription is canceled immediately.
        """
        return stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=at_period_end
        )