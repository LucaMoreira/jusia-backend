from django.urls import path
from .views import (
    get_user_notifications,
    get_unread_count,
    mark_as_read,
    mark_all_as_read,
    list_all_notifications,
    create_notification,
    update_notification,
    delete_notification,
)

urlpatterns = [
    # Rotas do usuário
    path('user/', get_user_notifications, name='user_notifications'),
    path('user/unread-count/', get_unread_count, name='unread_count'),
    path('user/mark-read/<int:notification_id>/', mark_as_read, name='mark_as_read'),
    path('user/mark-all-read/', mark_all_as_read, name='mark_all_read'),
    
    # Rotas de administração (superuser)
    path('admin/', list_all_notifications, name='list_all_notifications'),
    path('admin/create/', create_notification, name='create_notification'),
    path('admin/<int:notification_id>/', update_notification, name='update_notification'),
    path('admin/<int:notification_id>/delete/', delete_notification, name='delete_notification'),
]
