from django.urls import path
from .views import *

urlpatterns = [
    path('subscription/', create_subscription),
    path('subscription/info/', get_subscription),
    path('validate-payment/', validate_stripe_payment),
    path('deletesubscription/', delete_subscription),
]