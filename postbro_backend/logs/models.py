import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _

class AppLog(models.Model):
    class LogLevel(models.TextChoices):
        DEBUG = 'debug', _('Debug')
        INFO = 'info', _('Info')
        WARNING = 'warning', _('Warning')
        ERROR = 'error', _('Error')
        CRITICAL = 'critical', _('Critical')

    class LogCategory(models.TextChoices):
        AUTH = 'auth', _('Authentication')
        SCRAPE = 'scrape', _('Scraping')
        API = 'api', _('API')
        ANALYSIS = 'analysis', _('Analysis')
        BILLING = 'billing', _('Billing')
        SYSTEM = 'system', _('System')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level = models.CharField(max_length=10, choices=LogLevel.choices)
    category = models.CharField(max_length=20, choices=LogCategory.choices)
    message = models.TextField()
    metadata = models.JSONField(default=dict)  # Additional context data
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['level']),
            models.Index(fields=['category']),
            models.Index(fields=['created_at']),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.get_level_display()}] {self.category} - {self.created_at}"
