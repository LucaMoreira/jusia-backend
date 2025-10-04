from django.contrib import admin
from .models import ChatSession, ChatMessage, ChatContext


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'title', 'process', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at', 'user']
    search_fields = ['user__email', 'title', 'process__process_number']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'message_type', 'content_preview', 'created_at']
    list_filter = ['message_type', 'created_at', 'session__user']
    search_fields = ['content', 'session__user__email', 'session__title']
    readonly_fields = ['created_at']
    ordering = ['-created_at']
    
    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Conteúdo'


@admin.register(ChatContext)
class ChatContextAdmin(admin.ModelAdmin):
    list_display = ['id', 'session', 'created_at', 'updated_at']
    list_filter = ['created_at', 'updated_at']
    search_fields = ['session__user__email', 'session__title']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-updated_at']