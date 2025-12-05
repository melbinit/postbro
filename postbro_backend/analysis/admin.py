from django.contrib import admin
from .models import PostAnalysisRequest, AnalysisStatusHistory


@admin.register(PostAnalysisRequest)
class PostAnalysisRequestAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'user', 'platform', 'display_name', 'status', 'retry_count', 
        'created_at'
    ]
    list_filter = ['platform', 'status', 'created_at']
    search_fields = ['user__email', 'display_name', 'task_id']
    readonly_fields = [
        'id', 'created_at', 'updated_at', 'completed_at', 
        'retry_count', 'last_retry_at'
    ]
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'platform', 'status')
        }),
        ('Analysis Parameters', {
            'fields': ('post_urls', 'display_name')
        }),
        ('Processing', {
            'fields': ('task_id', 'results', 'error_message')
        }),
        ('Retry Mechanism', {
            'fields': ('retry_count', 'max_retries', 'last_retry_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(AnalysisStatusHistory)
class AnalysisStatusHistoryAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'analysis_request', 'stage', 'is_error', 
        'progress_percentage', 'created_at'
    ]
    list_filter = ['stage', 'is_error', 'created_at']
    search_fields = ['analysis_request__id', 'message', 'error_code']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'analysis_request', 'stage', 'message')
        }),
        ('Error Information', {
            'fields': ('is_error', 'error_code', 'retryable', 'actionable_message'),
            'classes': ('collapse',)
        }),
        ('Progress & Analytics', {
            'fields': (
                'progress_percentage', 'duration_seconds',
                'api_calls_made', 'cost_estimate'
            ),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        qs = super().get_queryset(request)
        return qs.select_related('analysis_request')
