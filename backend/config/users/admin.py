from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Profile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('id', 'username', 'email', 'student_id', 'first_name', 'last_name', 'is_staff')
    search_fields = ('username', 'email', 'student_id')
    fieldsets = BaseUserAdmin.fieldsets + (
        ('KBTU Fields', {'fields': ('student_id',)}),
    )


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'faculty', 'phone', 'bio')
    search_fields = ('user__username', 'faculty')
