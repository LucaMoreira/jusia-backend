from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _
from .models import CustomUser
from django.contrib.auth.models import Permission

admin.site.site_header = "Administração Legatio"
admin.site.site_title = "Legatio Admin"
admin.site.index_title = "Painel de Administração"

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ("email", "username", "is_staff", "is_active")
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Informações pessoais"), {"fields": ("username", "first_name", "last_name")}),
        (_("Permissões"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Datas importantes"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "password1", "password2", "is_staff", "is_active", "is_superuser", "groups"),
        }),
    )

    search_fields = ("email", "username")
    ordering = ("email",)

admin.site.register(Permission)