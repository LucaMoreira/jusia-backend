from django.db import models
from django.conf import settings
from django.utils import timezone


class Notification(models.Model):
    NOTIFICATION_TYPES = [
        ('info', 'Informação'),
        ('success', 'Sucesso'),
        ('warning', 'Aviso'),
        ('error', 'Erro'),
        ('system', 'Sistema'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Usuário'
    )
    title = models.CharField(max_length=200, verbose_name='Título')
    message = models.TextField(verbose_name='Mensagem')
    notification_type = models.CharField(
        max_length=20,
        choices=NOTIFICATION_TYPES,
        default='info',
        verbose_name='Tipo'
    )
    is_read = models.BooleanField(default=False, verbose_name='Lida')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Criada em')
    read_at = models.DateTimeField(null=True, blank=True, verbose_name='Lida em')
    expires_at = models.DateTimeField(null=True, blank=True, verbose_name='Expira em')
    action_url = models.URLField(null=True, blank=True, verbose_name='URL de Ação')
    action_text = models.CharField(max_length=100, null=True, blank=True, verbose_name='Texto da Ação')

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificação'
        verbose_name_plural = 'Notificações'

    def __str__(self):
        return f"{self.title} - {self.user.email}"

    def mark_as_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    def is_expired(self):
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False
