"""
Celery Tasks for Analytics

Async tasks for logging API requests, authentication events, and external API calls.
All logging is done asynchronously to avoid blocking request processing.
"""
import logging
from typing import Dict, List, Any, Optional
from celery import shared_task
from django.utils import timezone
from django.db import transaction
from django.conf import settings

from .models import APIAccessLog, AuthenticationLog, ExternalAPICallLog
from .config import get_analytics_config

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def flush_api_logs(self, log_entries: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk insert API access logs to database.
    
    This task receives a batch of log entries and inserts them in a single
    database transaction for efficiency.
    
    Args:
        log_entries: List of dictionaries containing log data
    
    Returns:
        Dictionary with flush results
    """
    if not log_entries:
        return {'status': 'skipped', 'reason': 'empty_batch'}
    
    config = get_analytics_config()
    if not config['ENABLED']:
        return {'status': 'skipped', 'reason': 'disabled'}
    
    try:
        start_time = timezone.now()
        
        # Prepare model instances
        log_objects = []
        for entry in log_entries:
            try:
                # Get user if user_id provided
                user = None
                if entry.get('user_id'):
                    from accounts.models import User
                    try:
                        user = User.objects.get(id=entry['user_id'])
                    except User.DoesNotExist:
                        pass
                
                log_obj = APIAccessLog(
                    user=user,
                    endpoint=entry.get('endpoint', ''),
                    method=entry.get('method', 'GET'),
                    status_code=entry.get('status_code', 200),
                    response_time_ms=entry.get('response_time_ms', 0),
                    ip_address=entry.get('ip_address'),
                    user_agent=entry.get('user_agent', '')[:500] if entry.get('user_agent') else '',  # Limit length
                    request_size_bytes=entry.get('request_size_bytes'),
                    response_size_bytes=entry.get('response_size_bytes'),
                    query_params=entry.get('query_params', {}),
                    error_message=entry.get('error_message', '')[:1000] if entry.get('error_message') else '',  # Limit length
                    created_at=entry.get('created_at', timezone.now()),
                )
                log_objects.append(log_obj)
            except Exception as e:
                logger.error(f"❌ [flush_api_logs] Failed to create log object: {e}", exc_info=True)
                continue
        
        if not log_objects:
            return {'status': 'error', 'reason': 'no_valid_objects'}
        
        # Bulk insert in transaction
        with transaction.atomic():
            APIAccessLog.objects.bulk_create(log_objects, ignore_conflicts=True)
        
        duration = (timezone.now() - start_time).total_seconds()
        logger.info(f"✅ [flush_api_logs] Inserted {len(log_objects)} logs in {duration:.3f}s")
        
        return {
            'status': 'success',
            'count': len(log_objects),
            'duration_seconds': duration,
        }
        
    except Exception as e:
        logger.error(f"❌ [flush_api_logs] Failed to flush logs: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def log_auth_event(
    self,
    user_id: Optional[str],
    event_type: str,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Log authentication event immediately.
    
    Authentication events are critical and should be logged immediately,
    not batched. This ensures security monitoring works in real-time.
    
    Args:
        user_id: User UUID (None for failed attempts)
        event_type: Type of event (signup, login, logout, etc.)
        ip_address: Client IP address
        user_agent: User agent string
        success: Whether event was successful
        error_message: Error message if failed
        metadata: Additional context data
    
    Returns:
        Dictionary with log result
    """
    config = get_analytics_config()
    if not config['ENABLED']:
        return {'status': 'skipped', 'reason': 'disabled'}
    
    try:
        # Get user if user_id provided
        user = None
        if user_id:
            from accounts.models import User
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        
        log_entry = AuthenticationLog.objects.create(
            user=user,
            event_type=event_type,
            ip_address=ip_address,
            user_agent=user_agent[:500] if user_agent else '',  # Limit length
            success=success,
            error_message=error_message[:1000] if error_message else '',  # Limit length
            metadata=metadata or {},
            created_at=timezone.now(),
        )
        
        logger.debug(f"✅ [log_auth_event] Logged {event_type} for user {user_id}")
        
        return {
            'status': 'success',
            'log_id': str(log_entry.id),
        }
        
    except Exception as e:
        logger.error(f"❌ [log_auth_event] Failed to log auth event: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=30 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def log_external_api_call(
    self,
    user_id: Optional[str],
    service: str,
    endpoint: str,
    method: str,
    status_code: int,
    response_time_ms: int,
    cost_estimate: Optional[float] = None,
    request_size_bytes: Optional[int] = None,
    response_size_bytes: Optional[int] = None,
    error_message: Optional[str] = None,
    metadata: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    Log external API call (Gemini, BrightData, Supabase).
    
    Can be called immediately or batched depending on configuration.
    For now, logs immediately (can be optimized later if needed).
    
    Args:
        user_id: User UUID who triggered the call
        service: Service name (gemini, brightdata, supabase)
        endpoint: API endpoint URL
        method: HTTP method
        status_code: HTTP status code
        response_time_ms: Response time in milliseconds
        cost_estimate: Estimated cost in USD
        request_size_bytes: Request payload size
        response_size_bytes: Response payload size
        error_message: Error message if failed
        metadata: Additional context (model, tokens, etc.)
    
    Returns:
        Dictionary with log result
    """
    config = get_analytics_config()
    if not config['ENABLED']:
        return {'status': 'skipped', 'reason': 'disabled'}
    
    try:
        # Get user if user_id provided
        user = None
        if user_id:
            from accounts.models import User
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                pass
        
        log_entry = ExternalAPICallLog.objects.create(
            user=user,
            service=service,
            endpoint=endpoint[:500],  # Limit length
            method=method,
            status_code=status_code,
            response_time_ms=response_time_ms,
            cost_estimate=cost_estimate,
            request_size_bytes=request_size_bytes,
            response_size_bytes=response_size_bytes,
            error_message=error_message[:1000] if error_message else '',  # Limit length
            metadata=metadata or {},
            created_at=timezone.now(),
        )
        
        logger.debug(f"✅ [log_external_api_call] Logged {service} call: {endpoint}")
        
        return {
            'status': 'success',
            'log_id': str(log_entry.id),
        }
        
    except Exception as e:
        logger.error(f"❌ [log_external_api_call] Failed to log external API call: {e}", exc_info=True)
        # Retry with exponential backoff
        raise self.retry(exc=e, countdown=60 * (2 ** self.request.retries))


@shared_task
def queue_api_log(log_data: Dict[str, Any]) -> None:
    """
    Queue API log entry for batch processing.
    
    This is a lightweight task that just adds the log to the flush manager queue.
    The flush manager handles batching and flushing.
    
    Note: This task is called from middleware. If Celery is not available,
    the middleware will handle it synchronously.
    
    Args:
        log_data: Dictionary containing log entry data
    """
    from .utils import get_flush_manager
    
    config = get_analytics_config()
    if not config['ENABLED']:
        return
    
    try:
        flush_manager = get_flush_manager()
        flush_manager.add_log(log_data)
    except Exception as e:
        logger.error(f"❌ [queue_api_log] Failed to queue log: {e}", exc_info=True)

