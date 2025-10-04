from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator

User = get_user_model()

class ProcessSearch(models.Model):
    """
    Modelo para armazenar buscas de processos realizadas pelos usuários
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='process_searches')
    process_number = models.CharField(
        max_length=25,
        validators=[
            RegexValidator(
                regex=r'^(\d{7}-\d{2}\.\d{4}\.\d{1}\.\d{2}\.\d{4}|\d{20})$',
                message='Número do processo deve estar no formato: NNNNNNN-DD.AAAA.J.TR.OOOO ou apenas 20 dígitos'
            )
        ]
    )
    search_date = models.DateTimeField(auto_now_add=True)
    success = models.BooleanField(default=False)
    error_message = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-search_date']
        verbose_name = 'Busca de Processo'
        verbose_name_plural = 'Buscas de Processos'
    
    def __str__(self):
        return f"{self.user.email} - {self.process_number}"


class ProcessData(models.Model):
    """
    Modelo para armazenar dados de processos consultados
    """
    process_number = models.CharField(max_length=25, unique=True, blank=True, null=True)
    process_id = models.CharField(max_length=100, blank=True, null=True)
    court_code = models.CharField(max_length=10, blank=True, null=True)
    court_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Dados básicos do processo
    case_class = models.CharField(max_length=200, blank=True, null=True, verbose_name='Classe')
    subject = models.TextField(blank=True, null=True, verbose_name='Assunto')
    value = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True, verbose_name='Valor da Causa')
    distribution_date = models.DateField(null=True, blank=True, verbose_name='Data de Distribuição')
    
    # Status
    status = models.CharField(max_length=100, blank=True, null=True, verbose_name='Status')
    last_update = models.DateTimeField(null=True, blank=True, verbose_name='Última Atualização')
    
    # Dados brutos da API
    raw_data = models.JSONField(default=dict, verbose_name='Dados Brutos')
    
    # Metadados
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        verbose_name = 'Dados de Processo'
        verbose_name_plural = 'Dados de Processos'
    
    def __str__(self):
        return f"{self.process_number} - {self.court_name or 'Tribunal não identificado'}"


class ProcessParty(models.Model):
    """
    Modelo para armazenar partes dos processos
    """
    PARTY_TYPES = [
        ('autor', 'Autor'),
        ('reu', 'Réu'),
        ('terceiro', 'Terceiro'),
        ('testemunha', 'Testemunha'),
        ('outros', 'Outros'),
    ]
    
    process = models.ForeignKey(ProcessData, on_delete=models.CASCADE, related_name='parties')
    name = models.CharField(max_length=500, verbose_name='Nome')
    party_type = models.CharField(max_length=20, choices=PARTY_TYPES, verbose_name='Tipo da Parte')
    document = models.CharField(max_length=20, blank=True, null=True, verbose_name='Documento')
    lawyer = models.CharField(max_length=500, blank=True, null=True, verbose_name='Advogado')
    
    class Meta:
        verbose_name = 'Parte do Processo'
        verbose_name_plural = 'Partes do Processo'
    
    def __str__(self):
        return f"{self.name} ({self.get_party_type_display()})"


class ProcessMovement(models.Model):
    """
    Modelo para armazenar movimentações dos processos
    """
    process = models.ForeignKey(ProcessData, on_delete=models.CASCADE, related_name='movements')
    date = models.DateTimeField(verbose_name='Data')
    description = models.TextField(verbose_name='Descrição')
    movement_type = models.CharField(max_length=100, blank=True, null=True, verbose_name='Tipo de Movimentação')
    
    class Meta:
        ordering = ['-date']
        verbose_name = 'Movimentação do Processo'
        verbose_name_plural = 'Movimentações do Processo'
    
    def __str__(self):
        return f"{self.process.process_number} - {self.date.strftime('%d/%m/%Y')}"


class UserProcessFavorite(models.Model):
    """
    Modelo para processos favoritos dos usuários
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_processes')
    process = models.ForeignKey(ProcessData, on_delete=models.CASCADE, related_name='favorited_by')
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['user', 'process']
        verbose_name = 'Processo Favorito'
        verbose_name_plural = 'Processos Favoritos'
    
    def __str__(self):
        return f"{self.user.email} - {self.process.process_number}"


class ProcessNotification(models.Model):
    """
    Modelo para notificações de atualizações de processos
    """
    NOTIFICATION_TYPES = [
        ('movement', 'Nova Movimentação'),
        ('status_change', 'Mudança de Status'),
        ('deadline', 'Prazo Próximo'),
        ('general', 'Geral'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='process_notifications')
    process = models.ForeignKey(ProcessData, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=20, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notificação de Processo'
        verbose_name_plural = 'Notificações de Processos'
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"
