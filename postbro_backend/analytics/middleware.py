"""
API Tracking Middleware

Tracks all API requests asynchronously without blocking the request-response cycle.
Uses Celery tasks and flush manager for efficient batch processing.
"""
import time
import logging
from typing import Callable
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from .config import get_analytics_config, should_track_endpoint, should_sample_request
from .utils import get_client_ip, get_request_size, get_response_size, sanitize_query_params
from .tasks import queue_api_log

logger = logging.getLogger(__name__)


class APITrackingMiddleware(MiddlewareMixin):
    """
    Middleware to track API requests for analytics.
    
    Position: After AuthenticationMiddleware (to access request.user)
    Position: After CorsMiddleware (to handle CORS properly)
    
    Features:
    - Non-blocking async logging via Celery
    - Configurable endpoint exclusions
    - Request/response size tracking
    - Error tracking
    - Sampling support for high-traffic endpoints
    """
    
    def __init__(self, get_response: Callable):
        """Initialize middleware"""
        super().__init__(get_response)
        self.config = get_analytics_config()
    
    def process_request(self, request: HttpRequest) -> None:
        """Store request start time for response time calculation"""
        if not self.config['ENABLED']:
            return None
        
        # Store start time on request object
        request._analytics_start_time = time.time()
        return None
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """
        Track API request after response is generated.
        
        This method:
        1. Checks if endpoint should be tracked
        2. Collects request/response data
        3. Queues log entry for async processing
        """
        if not self.config['ENABLED']:
            return response
        
        # Get endpoint path
        endpoint = request.path
        
        # Check if endpoint should be tracked
        if not should_track_endpoint(endpoint, self.config):
            return response
        
        # Check if we should track authenticated-only requests
        if self.config.get('TRACK_AUTHENTICATED_ONLY', False):
            if not hasattr(request, 'user') or not request.user.is_authenticated:
                return response
        
        # Check sampling (for high-traffic endpoints)
        if not should_sample_request(endpoint, self.config):
            return response
        
        # Calculate response time
        start_time = getattr(request, '_analytics_start_time', None)
        if start_time:
            response_time_ms = int((time.time() - start_time) * 1000)
        else:
            response_time_ms = 0
        
        # Get user ID (if authenticated)
        user_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
        
        # Get client info
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Get request/response sizes
        request_size_bytes = None
        response_size_bytes = None
        
        if self.config.get('TRACK_REQUEST_SIZE', True):
            request_size_bytes = get_request_size(request)
            # Limit tracking of large requests
            max_size = self.config.get('MAX_REQUEST_SIZE_BYTES', 10485760)  # 10MB
            if request_size_bytes and request_size_bytes > max_size:
                request_size_bytes = None  # Don't track oversized requests
        
        if self.config.get('TRACK_RESPONSE_SIZE', True):
            response_size_bytes = get_response_size(response)
            # Limit tracking of large responses
            max_size = self.config.get('MAX_RESPONSE_SIZE_BYTES', 10485760)  # 10MB
            if response_size_bytes and response_size_bytes > max_size:
                response_size_bytes = None  # Don't track oversized responses
        
        # Get query parameters (sanitized)
        query_params = {}
        if self.config.get('LOG_QUERY_PARAMS', True):
            query_params = sanitize_query_params(request.GET.dict())
        
        # Get error message if response indicates error
        error_message = None
        if response.status_code >= 400:
            # Try to extract error message from response
            if hasattr(response, 'data') and isinstance(response.data, dict):
                error_message = str(response.data.get('error', response.data.get('detail', '')))[:1000]
            elif hasattr(response, 'content'):
                try:
                    content_str = str(response.content)[:500]
                    error_message = content_str if response.status_code >= 500 else None
                except:
                    pass
        
        # Prepare log data
        log_data = {
            'user_id': user_id,
            'endpoint': endpoint,
            'method': request.method,
            'status_code': response.status_code,
            'response_time_ms': response_time_ms,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'request_size_bytes': request_size_bytes,
            'response_size_bytes': response_size_bytes,
            'query_params': query_params,
            'error_message': error_message,
            'created_at': timezone.now(),
        }
        
        # Queue log entry for async processing
        try:
            queue_api_log.delay(log_data)
        except Exception as e:
            # If Celery is not available, log warning but don't block request
            logger.warning(f"⚠️ [APITrackingMiddleware] Failed to queue API log: {e}")
            # Optionally, could fall back to synchronous logging here
            # But for production, Celery should always be available
        
        return response
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """
        Track exceptions that occur during request processing.
        
        This ensures we log 500 errors even if they're not caught by views.
        """
        if not self.config['ENABLED']:
            return None
        
        endpoint = request.path
        if not should_track_endpoint(endpoint, self.config):
            return None
        
        # Calculate response time
        start_time = getattr(request, '_analytics_start_time', None)
        if start_time:
            response_time_ms = int((time.time() - start_time) * 1000)
        else:
            response_time_ms = 0
        
        # Get user ID
        user_id = None
        if hasattr(request, 'user') and request.user.is_authenticated:
            user_id = str(request.user.id)
        
        # Prepare log data for exception
        log_data = {
            'user_id': user_id,
            'endpoint': endpoint,
            'method': request.method,
            'status_code': 500,  # Exception = 500 error
            'response_time_ms': response_time_ms,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
            'request_size_bytes': get_request_size(request),
            'response_size_bytes': None,
            'query_params': sanitize_query_params(request.GET.dict()) if self.config.get('LOG_QUERY_PARAMS', True) else {},
            'error_message': str(exception)[:1000],
            'created_at': timezone.now(),
        }
        
        # Queue log entry
        try:
            queue_api_log.delay(log_data)
        except Exception as e:
            logger.warning(f"⚠️ [APITrackingMiddleware] Failed to queue exception log: {e}")
        
        return None  # Let Django handle the exception normally






