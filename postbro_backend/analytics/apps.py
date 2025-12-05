import atexit
from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    verbose_name = 'Analytics'

    def ready(self):
        """Initialize analytics app when Django starts"""
        # Register shutdown handler for flush manager
        from .utils import get_flush_manager
        
        def shutdown_handler():
            """Flush remaining logs on shutdown"""
            try:
                flush_manager = get_flush_manager()
                flush_manager.shutdown()
            except Exception:
                pass  # Ignore errors during shutdown
        
        atexit.register(shutdown_handler)
