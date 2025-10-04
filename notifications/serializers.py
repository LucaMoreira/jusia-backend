from rest_framework import serializers
from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'id', 'title', 'message', 'notification_type', 'is_read',
            'created_at', 'read_at', 'expires_at', 'action_url', 'action_text'
        ]
        read_only_fields = ['id', 'created_at', 'read_at']

    def create(self, validated_data):
        # Se não especificado, definir expiração para 30 dias
        if not validated_data.get('expires_at'):
            from django.utils import timezone
            from datetime import timedelta
            validated_data['expires_at'] = timezone.now() + timedelta(days=30)
        
        return super().create(validated_data)


class NotificationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = [
            'user', 'title', 'message', 'notification_type',
            'expires_at', 'action_url', 'action_text'
        ]

    def create(self, validated_data):
        # Se não especificado, definir expiração para 30 dias
        if not validated_data.get('expires_at'):
            from django.utils import timezone
            from datetime import timedelta
            validated_data['expires_at'] = timezone.now() + timedelta(days=30)
        
        return super().create(validated_data)
