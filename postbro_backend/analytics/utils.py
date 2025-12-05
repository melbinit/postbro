"""
Analytics Utility Functions

Helper functions for analytics tracking, including flush manager
for efficient batch processing of logs.
"""
import time
import threading
import logging
from typing import Dict, List, Any, Optional
from django.conf import settings
from .config import get_analytics_config

logger = logging.getLogger(__name__)


class LogFlushManager:
    """
    Manages flushing of API logs with configurable strategy.
    
    Supports:
    - Time-based flush (every N seconds)
    - Count-based flush (when queue reaches N logs)
    - Hybrid (both strategies)
    
    Thread-safe and optimized for high-throughput scenarios.
    """
    
    def __init__(self):
        """Initialize flush manager with configuration"""
        self.config = get_analytics_config()
        self.queue: List[Dict[str, Any]] = []
        self.lock = threading.Lock()
        self.last_flush = time.time()
        self.timer_thread: Optional[threading.Thread] = None
        self.timer_running = False
        
        # Start timer if time-based or hybrid strategy
        if self.config['FLUSH_STRATEGY'] in ('time', 'hybrid'):
            self._start_timer()
    
    def add_log(self, log_data: Dict[str, Any]) -> None:
        """
        Add log entry to queue.
        Triggers flush if count threshold reached (for count/hybrid strategies).
        
        Args:
            log_data: Dictionary containing log entry data
        """
        if not self.config['ENABLED']:
            return
        
        with self.lock:
            self.queue.append(log_data)
            queue_size = len(self.queue)
            
            # Check count-based flush (for count or hybrid strategy)
            if self.config['FLUSH_STRATEGY'] in ('count', 'hybrid'):
                threshold = self.config['FLUSH_COUNT_THRESHOLD']
                if queue_size >= threshold:
                    logger.debug(f"📊 [FlushManager] Count threshold reached ({queue_size}), triggering flush")
                    self._trigger_flush()
    
    def _trigger_flush(self) -> None:
        """
        Flush queue to database via Celery task.
        Must be called with lock held.
        """
        if not self.queue:
            return
        
        # Copy queue and clear it
        logs_to_flush = self.queue.copy()
        self.queue.clear()
        self.last_flush = time.time()
        
        # Dispatch to Celery task for async processing
        try:
            from .tasks import flush_api_logs
            flush_api_logs.delay(logs_to_flush)
            logger.debug(f"✅ [FlushManager] Flushed {len(logs_to_flush)} logs to Celery queue")
        except Exception as e:
            # If Celery is not available, log error but don't block
            # In production, Celery should always be available
            logger.warning(f"⚠️ [FlushManager] Celery not available, logs queued in memory: {e}")
            # Re-add logs to queue on error (prevent data loss)
            # They'll be flushed when Celery is available
            self.queue.extend(logs_to_flush)
    
    def _start_timer(self) -> None:
        """Start background timer thread for time-based flushing"""
        if self.timer_running:
            return
        
        self.timer_running = True
        
        def timer_loop():
            """Timer loop that checks and flushes periodically"""
            interval = self.config['FLUSH_INTERVAL_SECONDS']
            while self.timer_running:
                time.sleep(interval)
                
                with self.lock:
                    # Check if time-based flush is needed
                    time_since_flush = time.time() - self.last_flush
                    if time_since_flush >= interval:
                        if self.queue:  # Only flush if there are logs
                            logger.debug(f"📊 [FlushManager] Timer expired ({time_since_flush:.1f}s), triggering flush")
                            self._trigger_flush()
        
        self.timer_thread = threading.Thread(target=timer_loop, daemon=True)
        self.timer_thread.start()
        logger.info(f"🕐 [FlushManager] Timer started (interval: {self.config['FLUSH_INTERVAL_SECONDS']}s)")
    
    def flush_now(self) -> None:
        """
        Manually trigger flush immediately.
        Useful for shutdown or testing.
        """
        with self.lock:
            self._trigger_flush()
    
    def get_queue_size(self) -> int:
        """Get current queue size (for monitoring)"""
        with self.lock:
            return len(self.queue)
    
    def shutdown(self) -> None:
        """Stop timer and flush remaining logs"""
        self.timer_running = False
        if self.timer_thread:
            self.timer_thread.join(timeout=5)
        self.flush_now()  # Flush any remaining logs


# Global flush manager instance
_flush_manager: Optional[LogFlushManager] = None


def get_flush_manager() -> LogFlushManager:
    """
    Get or create global flush manager instance.
    Singleton pattern for thread-safe access.
    
    Returns:
        LogFlushManager instance
    """
    global _flush_manager
    if _flush_manager is None:
        _flush_manager = LogFlushManager()
    return _flush_manager


def get_client_ip(request) -> Optional[str]:
    """
    Extract client IP address from request.
    Handles proxies and load balancers.
    
    Args:
        request: Django request object
    
    Returns:
        IP address string or None
    """
    # Check for forwarded IP (from proxy/load balancer)
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Take first IP in chain
        ip = x_forwarded_for.split(',')[0].strip()
        return ip
    
    # Fallback to direct connection IP
    return request.META.get('REMOTE_ADDR')


def get_request_size(request) -> Optional[int]:
    """
    Get request body size in bytes.
    
    Args:
        request: Django request object
    
    Returns:
        Size in bytes or None
    """
    content_length = request.META.get('CONTENT_LENGTH')
    if content_length:
        try:
            return int(content_length)
        except (ValueError, TypeError):
            return None
    return None


def get_response_size(response) -> Optional[int]:
    """
    Get response body size in bytes.
    
    Args:
        response: Django response object
    
    Returns:
        Size in bytes or None
    """
    if hasattr(response, 'content'):
        try:
            return len(response.content)
        except (TypeError, AttributeError):
            return None
    return None


def sanitize_query_params(query_params: Dict) -> Dict:
    """
    Sanitize query parameters for logging.
    Removes sensitive data and limits size.
    
    Args:
        query_params: Query parameters dictionary
    
    Returns:
        Sanitized dictionary
    """
    sanitized = {}
    sensitive_keys = ['password', 'token', 'secret', 'key', 'api_key', 'access_token']
    
    for key, value in query_params.items():
        # Skip sensitive keys
        if any(sensitive in key.lower() for sensitive in sensitive_keys):
            sanitized[key] = '***REDACTED***'
        else:
            # Limit value length
            if isinstance(value, str) and len(value) > 100:
                sanitized[key] = value[:100] + '...'
            else:
                sanitized[key] = value
    
    return sanitized

