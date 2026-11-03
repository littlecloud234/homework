from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "display_name", "role", "department", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "display_name", "department", "email")
    fieldsets = BaseUserAdmin.fieldsets + (
        ("教学信息", {"fields": ("role", "display_name", "department")}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("教学信息", {"fields": ("role", "display_name", "department")}),
    )
