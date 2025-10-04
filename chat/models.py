from django.db import models
from django.contrib.auth import get_user_model
from processes.models import ProcessData

User = get_user_model()


class ChatSession(models.Model):
    """
    Modelo para sessões de chat com IA
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    title = models.CharField(max_length=200, blank=True)
    process = models.ForeignKey(ProcessData, on_delete=models.SET_NULL, null=True, blank=True, related_name='chat_sessions')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Sessão de Chat'
        verbose_name_plural = 'Sessões de Chat'
    
    def __str__(self):
        return f"{self.user.email} - {self.title or 'Chat sem título'}"


class ChatMessage(models.Model):
    """
    Modelo para mensagens do chat
    """
    MESSAGE_TYPES = [
        ('user', 'Usuário'),
        ('assistant', 'Assistente'),
        ('system', 'Sistema'),
    ]
    
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    metadata = models.JSONField(default=dict, blank=True)  # Para armazenar dados adicionais como tokens, etc.
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Mensagem do Chat'
        verbose_name_plural = 'Mensagens do Chat'
    
    def __str__(self):
        return f"{self.session} - {self.message_type} - {self.created_at.strftime('%d/%m/%Y %H:%M')}"


class ChatContext(models.Model):
    """
    Modelo para armazenar contexto específico de processos no chat
    """
    session = models.OneToOneField(ChatSession, on_delete=models.CASCADE, related_name='context')
    process_summary = models.TextField(blank=True)
    legal_analysis = models.TextField(blank=True)
    key_points = models.JSONField(default=list, blank=True)
    recommendations = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Contexto do Chat'
        verbose_name_plural = 'Contextos do Chat'
    
    def __str__(self):
        return f"Contexto - {self.session}"