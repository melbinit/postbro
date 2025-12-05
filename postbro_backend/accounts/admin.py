from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Plan, Subscription, UserUsage

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'full_name', 'company_name', 'is_active', 'email_verified', 'created_at')
    list_filter = ('is_active', 'email_verified', 'created_at')
    search_fields = ('email', 'full_name', 'company_name')
    ordering = ('-created_at',)
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('full_name', 'company_name')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'email_verified')}),
        ('Important dates', {'fields': ('last_login', 'created_at', 'updated_at')}),
    )
    readonly_fields = ('created_at', 'updated_at')
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'full_name', 'company_name'),
        }),
    )

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'max_handles', 'max_urls', 'max_analyses_per_day', 'max_questions_per_day', 'is_active')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name', 'description')
    ordering = ('price',)

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('user', 'plan', 'status', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'start_date', 'created_at')
    search_fields = ('user__email', 'plan__name')
    ordering = ('-created_at',)
    raw_id_fields = ('user', 'plan')

@admin.register(UserUsage)
class UserUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'platform', 'handle_analyses', 'url_lookups', 'post_suggestions', 'questions_asked')
    list_filter = ('date', 'platform', 'created_at')
    search_fields = ('user__email', 'platform')
    ordering = ('-date', '-created_at')
    raw_id_fields = ('user',)
