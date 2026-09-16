from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'email', 'role', 'display_name', 'is_staff', 'is_active')
    list_filter = ('role', 'is_staff', 'is_active')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Novu role', {'fields': ('role', 'display_name')}),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Novu role', {'fields': ('role', 'display_name')}),
    )
