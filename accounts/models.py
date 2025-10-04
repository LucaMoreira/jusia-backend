from django.db import models
from django.contrib.auth.models import AbstractUser
#from django.utils import timezone
from .managers import CustomUserManager

# Options
# SUBSCRIPTION_STATUS_OPTIONS = (
#    (0, 'incomplete'), 
#    (1, 'incomplete_expired'), 
#    (2, 'trialing, active'), 
#    (3, 'past_due'), 
#    (4, 'canceled'), 
#    (5, 'unpaid'),
#    (6, 'paused'),
#)

# Models
class CustomUser(AbstractUser):
    username = models.CharField(
        max_length=150,
        unique=False,
        blank=True,
        null=True,
        help_text="Nome do usuário, não precisa ser único."
    )
    email = models.EmailField(
        unique=True,
        blank=False,
        null=False,
    )
    is_tester = models.BooleanField(default=False)
    
    objects = CustomUserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email or self.username or str(self.id)


#class Subscription(models.Model):
#    id                     = models.AutoField(primary_key=True)
#    user                   = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='subscriptions')
#    status                 = models.CharField(choices=SUBSCRIPTION_STATUS_OPTIONS, max_length=200)
#    stripe_subscription_id = models.CharField(max_length=200)
#    stripe_custumer_id     = models.CharField(max_length=200)
#    created_at             = models.DateTimeField(default=timezone.now)
#    updated_at             = models.DateTimeField(default=timezone.now)