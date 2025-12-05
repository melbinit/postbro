"""
Analytics Models for Enterprise-Level Tracking

This module contains models for tracking:
- API access logs (all API requests)
- Authentication events (signups, logins, logouts)
- External API calls (Gemini, BrightData, Supabase)
"""
import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.conf import settings


class APIAccessLog(models.Model):
    """
    Tracks every API request to the backend.
    
    Used for:
    - Performance monitoring
    - Usage analytics
    - Error tracking
    - User activity analysis
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='api_access_logs',
        help_text='User who made the request (null for unauthenticated)'
    )
    endpoint = models.CharField(
        max_length=255,
        db_index=True,
        help_text='API endpoint path (e.g., /api/analysis/analyze/)'
    )
    method = models.CharField(
        max_length=10,
        help_text='HTTP method (GET, POST, PUT, DELETE, etc.)'
    )
    status_code = models.IntegerField(
        db_index=True,
        help_text='HTTP status code (200, 404, 500, etc.)'
    )
    response_time_ms = models.IntegerField(
        help_text='Response time in milliseconds'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text='Client IP address'
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text='User agent string from request headers'
    )
    request_size_bytes = models.IntegerField(
        null=True,
        blank=True,
        help_text='Request body size in bytes'
    )
    response_size_bytes = models.IntegerField(
        null=True,
        blank=True,
        help_text='Response body size in bytes'
    )
    query_params = models.JSONField(
        default=dict,
        blank=True,
        help_text='URL query parameters as dictionary'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if request failed'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Timestamp when request was made'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'API Access Log'
        verbose_name_plural = 'API Access Logs'
        indexes = [
            models.Index(fields=['user', 'created_at'], name='analytics_api_user_created'),
            models.Index(fields=['endpoint', 'created_at'], name='analytics_api_endpoint_created'),
            models.Index(fields=['status_code', 'created_at'], name='analytics_api_status_created'),
            models.Index(fields=['created_at'], name='analytics_api_created'),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} - {self.status_code} ({self.response_time_ms}ms)"


class AuthenticationLog(models.Model):
    """
    Tracks all authentication events.
    
    Used for:
    - Security monitoring
    - User behavior analysis
    - Abuse detection
    - Login analytics
    """
    
    class EventType(models.TextChoices):
        SIGNUP = 'signup', _('Sign Up')
        LOGIN = 'login', _('Login')
        LOGOUT = 'logout', _('Logout')
        LOGIN_FAILED = 'login_failed', _('Login Failed')
        TOKEN_REFRESH = 'token_refresh', _('Token Refresh')
        PASSWORD_RESET = 'password_reset', _('Password Reset')
        PASSWORD_RESET_REQUEST = 'password_reset_request', _('Password Reset Request')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='authentication_logs',
        help_text='User associated with event (null for failed attempts)'
    )
    event_type = models.CharField(
        max_length=30,
        choices=EventType.choices,
        db_index=True,
        help_text='Type of authentication event'
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        db_index=True,
        help_text='IP address from which event originated'
    )
    user_agent = models.TextField(
        blank=True,
        null=True,
        help_text='User agent string'
    )
    success = models.BooleanField(
        default=True,
        db_index=True,
        help_text='Whether the event was successful'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if event failed'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional context data (email used, etc.)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Timestamp when event occurred'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Authentication Log'
        verbose_name_plural = 'Authentication Logs'
        indexes = [
            models.Index(fields=['user', 'created_at'], name='analytics_auth_user_created'),
            models.Index(fields=['event_type', 'created_at'], name='analytics_auth_event_created'),
            models.Index(fields=['success', 'created_at'], name='analytics_auth_success_created'),
            models.Index(fields=['ip_address', 'created_at'], name='analytics_auth_ip_created'),
        ]

    def __str__(self):
        status = "✓" if self.success else "✗"
        user_str = str(self.user.email) if self.user else "Unknown"
        return f"{status} {self.get_event_type_display()} - {user_str} ({self.created_at})"


class ExternalAPICallLog(models.Model):
    """
    Tracks calls to external APIs (Gemini, BrightData, Supabase).
    
    Used for:
    - Cost tracking
    - Service performance monitoring
    - API usage analytics
    - Billing/chargeback
    """
    
    class ServiceType(models.TextChoices):
        GEMINI = 'gemini', _('Google Gemini')
        BRIGHTDATA = 'brightdata', _('BrightData')
        TWITTERAPI = 'twitterapi', _('TwitterAPI.io')
        SUPABASE = 'supabase', _('Supabase')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='external_api_call_logs',
        help_text='User who triggered the API call'
    )
    service = models.CharField(
        max_length=20,
        choices=ServiceType.choices,
        db_index=True,
        help_text='External service name'
    )
    endpoint = models.CharField(
        max_length=500,
        help_text='External API endpoint URL'
    )
    method = models.CharField(
        max_length=10,
        help_text='HTTP method used'
    )
    status_code = models.IntegerField(
        help_text='HTTP status code from external API'
    )
    response_time_ms = models.IntegerField(
        help_text='Response time in milliseconds'
    )
    cost_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=6,
        null=True,
        blank=True,
        help_text='Estimated cost in USD'
    )
    request_size_bytes = models.IntegerField(
        null=True,
        blank=True,
        help_text='Request payload size in bytes'
    )
    response_size_bytes = models.IntegerField(
        null=True,
        blank=True,
        help_text='Response payload size in bytes'
    )
    error_message = models.TextField(
        null=True,
        blank=True,
        help_text='Error message if call failed'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional context (model used, tokens, etc.)'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
        help_text='Timestamp when API call was made'
    )

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'External API Call Log'
        verbose_name_plural = 'External API Call Logs'
        indexes = [
            models.Index(fields=['user', 'service', 'created_at'], name='analytics_ext_user_service'),
            models.Index(fields=['service', 'created_at'], name='analytics_ext_service_created'),
            models.Index(fields=['created_at'], name='analytics_ext_created'),
        ]

    def __str__(self):
        status = "✓" if 200 <= self.status_code < 300 else "✗"
        return f"{status} {self.get_service_display()} - {self.endpoint} ({self.response_time_ms}ms)"
