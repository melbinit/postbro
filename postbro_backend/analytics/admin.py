"""
Django Admin configuration for Analytics models
"""
from django.contrib import admin
from .models import APIAccessLog, AuthenticationLog, ExternalAPICallLog


@admin.register(APIAccessLog)
class APIAccessLogAdmin(admin.ModelAdmin):
    """Admin interface for API Access Logs"""
    list_display = ['endpoint', 'method', 'status_code', 'response_time_ms', 'user', 'ip_address', 'created_at']
    list_filter = ['method', 'status_code', 'created_at', 'endpoint']
    search_fields = ['endpoint', 'user__email', 'ip_address', 'error_message']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Info', {
            'fields': ('user', 'endpoint', 'method', 'status_code', 'response_time_ms')
        }),
        ('Client Info', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Size Info', {
            'fields': ('request_size_bytes', 'response_size_bytes')
        }),
        ('Additional', {
            'fields': ('query_params', 'error_message', 'created_at')
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(AuthenticationLog)
class AuthenticationLogAdmin(admin.ModelAdmin):
    """Admin interface for Authentication Logs"""
    list_display = ['event_type', 'user', 'success', 'ip_address', 'created_at']
    list_filter = ['event_type', 'success', 'created_at']
    search_fields = ['user__email', 'ip_address', 'error_message']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Event Info', {
            'fields': ('user', 'event_type', 'success')
        }),
        ('Client Info', {
            'fields': ('ip_address', 'user_agent')
        }),
        ('Additional', {
            'fields': ('error_message', 'metadata', 'created_at')
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(ExternalAPICallLog)
class ExternalAPICallLogAdmin(admin.ModelAdmin):
    """Admin interface for External API Call Logs"""
    list_display = ['service', 'endpoint', 'status_code', 'response_time_ms', 'cost_estimate', 'user', 'created_at']
    list_filter = ['service', 'status_code', 'created_at']
    search_fields = ['endpoint', 'user__email', 'error_message']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Call Info', {
            'fields': ('user', 'service', 'endpoint', 'method', 'status_code', 'response_time_ms')
        }),
        ('Cost & Size', {
            'fields': ('cost_estimate', 'request_size_bytes', 'response_size_bytes')
        }),
        ('Additional', {
            'fields': ('error_message', 'metadata', 'created_at')
        }),
    )

    def get_queryset(self, request):
        """Optimize queryset with select_related"""
        qs = super().get_queryset(request)
        return qs.select_related('user')
