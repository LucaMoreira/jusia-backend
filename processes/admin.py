from django.contrib import admin
from .models import (
    ProcessSearch, ProcessData, ProcessParty, 
    ProcessMovement, UserProcessFavorite, ProcessNotification
)


@admin.register(ProcessSearch)
class ProcessSearchAdmin(admin.ModelAdmin):
    list_display = ['user', 'process_number', 'search_date', 'success']
    list_filter = ['success', 'search_date']
    search_fields = ['user__email', 'process_number']
    readonly_fields = ['search_date']


@admin.register(ProcessData)
class ProcessDataAdmin(admin.ModelAdmin):
    list_display = ['process_number', 'court_name', 'case_class', 'status', 'updated_at']
    list_filter = ['court_code', 'status', 'created_at']
    search_fields = ['process_number', 'court_name', 'case_class']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProcessParty)
class ProcessPartyAdmin(admin.ModelAdmin):
    list_display = ['process', 'name', 'party_type', 'document']
    list_filter = ['party_type']
    search_fields = ['name', 'document', 'process__process_number']


@admin.register(ProcessMovement)
class ProcessMovementAdmin(admin.ModelAdmin):
    list_display = ['process', 'date', 'movement_type', 'description_short']
    list_filter = ['movement_type', 'date']
    search_fields = ['process__process_number', 'description']
    readonly_fields = ['date']
    
    def description_short(self, obj):
        return obj.description[:50] + '...' if len(obj.description) > 50 else obj.description
    description_short.short_description = 'Descrição'


@admin.register(UserProcessFavorite)
class UserProcessFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'process', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'process__process_number']


@admin.register(ProcessNotification)
class ProcessNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'process', 'notification_type', 'title', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'process__process_number', 'title']
    readonly_fields = ['created_at']




