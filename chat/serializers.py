from rest_framework import serializers
from .models import ChatSession, ChatMessage, ChatContext
from processes.serializers import ProcessDataSerializer


class ChatMessageSerializer(serializers.ModelSerializer):
    """
    Serializer para mensagens do chat
    """
    class Meta:
        model = ChatMessage
        fields = ['id', 'message_type', 'content', 'created_at', 'metadata']
        read_only_fields = ['id', 'created_at']


class ChatContextSerializer(serializers.ModelSerializer):
    """
    Serializer para contexto do chat
    """
    class Meta:
        model = ChatContext
        fields = ['process_summary', 'legal_analysis', 'key_points', 'recommendations', 'created_at', 'updated_at']
        read_only_fields = ['created_at', 'updated_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """
    Serializer para sessões de chat
    """
    messages = ChatMessageSerializer(many=True, read_only=True)
    process = ProcessDataSerializer(read_only=True)
    context = ChatContextSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = ['id', 'title', 'process', 'created_at', 'updated_at', 'is_active', 'messages', 'context', 'message_count']
        read_only_fields = ['id', 'created_at', 'updated_at', 'message_count']
    
    def get_message_count(self, obj):
        return obj.messages.count()


class ChatSessionCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de sessões de chat
    """
    class Meta:
        model = ChatSession
        fields = ['title', 'process']
    
    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class ChatMessageCreateSerializer(serializers.ModelSerializer):
    """
    Serializer para criação de mensagens
    """
    class Meta:
        model = ChatMessage
        fields = ['content', 'message_type']
    
    def create(self, validated_data):
        validated_data['session_id'] = self.context['session_id']
        return super().create(validated_data)


class ChatResponseSerializer(serializers.Serializer):
    """
    Serializer para respostas da IA
    """
    message = serializers.CharField()
    session_id = serializers.IntegerField()
    message_id = serializers.IntegerField()
    context_updated = serializers.BooleanField(default=False)
    suggestions = serializers.ListField(child=serializers.CharField(), required=False)




