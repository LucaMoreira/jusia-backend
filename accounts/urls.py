from django.urls import path
from .views import *

urlpatterns = [
    #* Public Routes
    path('check_auth/', check_auth),
    path('create_user/', create_user),
    path('login/', login_user),
    path('contact/', contact),
    path('recoverpassword/', forgot_password),
    path('refresh/', refresh_token),
    
    #* Token Verification
    path('validate-password-token/', validadte_password_token),
    
    #* login required
    path('delete_user/', delete_user),
    path('update_profile/', update_profile),
    path('changeemail/', update_email),
    path('changepassword/', update_password),
    path('logout/', logout_user),
    path('get_user/', get_user),
    
    #* Admin routes (superuser only)
    path('admin/users/', list_users),
    path('admin/users/<int:user_id>/', update_user),
    path('admin/users/<int:user_id>/delete/', delete_user_admin),
    
    #* Unitiated | Inactive User
    path('validate-payment/', validate_stripe_payment),
    
    #* Active User
    path('deletesubscription/', delete_subscription),    
]