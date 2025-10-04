from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import Notification
from .serializers import NotificationSerializer, NotificationCreateSerializer


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_user_notifications(request):
    """Obter notificações do usuário logado"""
    notifications = Notification.objects.filter(
        user=request.user,
        expires_at__gt=timezone.now()  # Apenas notificações não expiradas
    ).order_by('-created_at')
    
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def get_unread_count(request):
    """Obter contagem de notificações não lidas"""
    count = Notification.objects.filter(
        user=request.user,
        is_read=False,
        expires_at__gt=timezone.now()
    ).count()
    
    return Response({'unread_count': count})


@api_view(['PUT'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def mark_as_read(request, notification_id):
    """Marcar notificação como lida"""
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.mark_as_read()
    
    return Response({'message': 'Notificação marcada como lida'})


@api_view(['PUT'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def mark_all_as_read(request):
    """Marcar todas as notificações como lidas"""
    Notification.objects.filter(
        user=request.user,
        is_read=False,
        expires_at__gt=timezone.now()
    ).update(is_read=True, read_at=timezone.now())
    
    return Response({'message': 'Todas as notificações foram marcadas como lidas'})


# Views de administração (apenas para superusers)
@api_view(['GET'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def list_all_notifications(request):
    """Listar todas as notificações - apenas para superusers"""
    if not request.user.is_superuser:
        return Response({'error': 'Acesso negado. Apenas superusers podem listar todas as notificações.'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    notifications = Notification.objects.all().order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True)
    return Response(serializer.data)


@api_view(['POST'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def create_notification(request):
    """Criar nova notificação - apenas para superusers"""
    if not request.user.is_superuser:
        return Response({'error': 'Acesso negado. Apenas superusers podem criar notificações.'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    serializer = NotificationCreateSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def update_notification(request, notification_id):
    """Atualizar notificação - apenas para superusers"""
    if not request.user.is_superuser:
        return Response({'error': 'Acesso negado. Apenas superusers podem atualizar notificações.'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    notification = get_object_or_404(Notification, id=notification_id)
    serializer = NotificationSerializer(notification, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAuthenticated])
def delete_notification(request, notification_id):
    """Deletar notificação - apenas para superusers"""
    if not request.user.is_superuser:
        return Response({'error': 'Acesso negado. Apenas superusers podem deletar notificações.'}, 
                       status=status.HTTP_403_FORBIDDEN)
    
    notification = get_object_or_404(Notification, id=notification_id)
    notification.delete()
    
    return Response({'message': 'Notificação deletada com sucesso'}, status=status.HTTP_200_OK)
