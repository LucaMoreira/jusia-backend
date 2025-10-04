from django.db import models
from django.utils import timezone
from accounts.models import CustomUser
from .utils import Stripe
import traceback

stripe_service = Stripe()

class SubscriptionStatus(models.Model):
    name = models.CharField(max_length=50, unique=True)

    class Meta:
        verbose_name_plural = "Subscription Statuses"

    def __str__(self):
        return self.name

class Plan(models.Model):
    name = models.CharField(max_length=100, unique=True)
    stripe_price_id = models.CharField(max_length=200, unique=True, help_text="Stripe Price ID for this plan")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='usd')
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Subscription(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name='subscriptions')
    status = models.ForeignKey(SubscriptionStatus, on_delete=models.DO_NOTHING)
    stripe_subscription_id = models.CharField(max_length=200, unique=True, help_text="Stripe Subscription ID")
    stripe_customer_id = models.CharField(max_length=200, help_text="Stripe Customer ID")
    start_date = models.DateTimeField(default=timezone.now)
    current_period_start = models.DateTimeField(blank=True, null=True)
    current_period_end = models.DateTimeField(blank=True, null=True)
    cancel_at_period_end = models.BooleanField(default=False)
    canceled_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email}'s {self.plan.name} subscription ({self.status.name})"

    def activate(self):
        """
        Activates the subscription both in your database and with Stripe.
        This method assumes the subscription is being created or re-activated.
        """
        try:
            if not self.stripe_customer_id:
                print(f"User {self.user.email} does not have a Stripe Customer ID. Creating one...")
                stripe_customer = stripe_service.create_customer(email=self.user.email)
                self.stripe_customer_id = stripe_customer.id
                print(f"Stripe Customer ID {self.stripe_customer_id} created and saved for user {self.user.email}.")

            if not self.stripe_subscription_id:
                stripe_sub = stripe_service.create_subscription(
                    custumer_id=self.stripe_customer_id,
                    price_id=self.plan.stripe_price_id
                )
                self.stripe_subscription_id = stripe_sub.id
                self.start_date = timezone.datetime.fromtimestamp(stripe_sub.start_date, tz=timezone.utc)
                self.current_period_start = timezone.datetime.fromtimestamp(stripe_sub.current_period_start, tz=timezone.utc)
                self.current_period_end = timezone.datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)
            else:
                stripe_sub = stripe_service.get_subscription(self.stripe_subscription_id)
                self.start_date = timezone.make_aware(timezone.datetime.fromtimestamp(stripe_sub['items']['data'][0].created))
                self.current_period_start = timezone.make_aware(timezone.datetime.fromtimestamp(stripe_sub['items']['data'][0].current_period_start))
                self.current_period_end = timezone.make_aware(timezone.datetime.fromtimestamp(stripe_sub['items']['data'][0].current_period_end))

            self.status = SubscriptionStatus.objects.get(name='active')
            self.cancel_at_period_end = False
            self.canceled_at = None
            self.save()
            print(f"Subscription {self.id} activated for {self.user.email} with Stripe ID: {self.stripe_subscription_id}")
            return True
        except Exception as e:
            print(f"Error activating subscription {self.id}: {traceback.print_exc()}")
            return False

    def cancel(self, at_period_end=True):
        """
        Cancels the subscription in Stripe and updates the database record.
        """
        if not self.stripe_subscription_id:
            print(f"Subscription {self.id} has no Stripe ID, cannot cancel in Stripe.")
            return False

        try:
            stripe_service.cancel_subscription(self.stripe_subscription_id, at_period_end)
            self.cancel_at_period_end = at_period_end
            self.canceled_at = timezone.now() if not at_period_end else None
            self.status = SubscriptionStatus.objects.get(name='canceled') # Assuming 'canceled' status exists
            self.save()
            print(f"Subscription {self.id} cancelled for {self.user.email} in Stripe.")
            return True
        except Exception as e:
            print(f"Error cancelling subscription {self.id}: {e}")
            return False

    def renew(self):
        """
        Renews the subscription. This usually happens automatically via webhooks,
        but this method could be for manual renewal or reconciliation.
        """
        if not self.stripe_subscription_id:
            print(f"Subscription {self.id} has no Stripe ID, cannot renew in Stripe via API directly.")
            return False

        try:
            stripe_sub = stripe_service.get_subscription(self.stripe_subscription_id)

            # Handle current_period_start and current_period_end safely
            if hasattr(stripe_sub, 'current_period_start') and stripe_sub.current_period_start:
                self.current_period_start = timezone.datetime.fromtimestamp(stripe_sub.current_period_start, tz=timezone.utc)
            if hasattr(stripe_sub, 'current_period_end') and stripe_sub.current_period_end:
                self.current_period_end = timezone.datetime.fromtimestamp(stripe_sub.current_period_end, tz=timezone.utc)
            # Map Stripe status to our status
            status_mapping = {
                'active': 'active',
                'canceled': 'canceled',
                'incomplete': 'incomplete',
                'incomplete_expired': 'incomplete_expired',
                'past_due': 'past_due',
                'trialing': 'trialing',
                'unpaid': 'unpaid'
            }
            stripe_status = stripe_sub.status
            our_status = status_mapping.get(stripe_status, 'inactive')
            self.status = SubscriptionStatus.objects.get(name=our_status)
            self.cancel_at_period_end = stripe_sub.cancel_at_period_end
            self.canceled_at = timezone.datetime.fromtimestamp(stripe_sub.canceled_at, tz=timezone.utc) if stripe_sub.canceled_at else None
            self.save()
            print(f"Subscription {self.id} renewed and updated from Stripe for {self.user.email}.")
            return True
        except Exception as e:
            print(f"Error renewing subscription {self.id}: {e}")
            return False
