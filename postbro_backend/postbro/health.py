"""
Health check endpoint for monitoring and Docker health checks.
"""
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from django.conf import settings
import redis
import logging

logger = logging.getLogger(__name__)


def health_check(request):
    """
    Health check endpoint that verifies:
    - Django is running
    - Database connection is working
    - Redis connection is working (if configured)
    
    Returns:
        JsonResponse with status and component checks
    """
    health_status = {
        'status': 'healthy',
        'service': 'postbro-backend',
        'checks': {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        health_status['checks']['database'] = {
            'status': 'healthy',
            'message': 'Database connection successful'
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status['checks']['database'] = {
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }
        health_status['status'] = 'unhealthy'
    
    # Check Redis connection (for Celery)
    try:
        redis_url = getattr(settings, 'CELERY_BROKER_URL', None)
        if redis_url:
            # Parse Redis URL (e.g., redis://redis:6379/0 or redis://localhost:6379/0)
            from urllib.parse import urlparse
            parsed = urlparse(redis_url)
            host = parsed.hostname or 'localhost'
            port = parsed.port or 6379
            db = int(parsed.path.lstrip('/')) if parsed.path else 0
            
            r = redis.Redis(host=host, port=port, db=db, socket_connect_timeout=2)
            r.ping()
            health_status['checks']['redis'] = {
                'status': 'healthy',
                'message': 'Redis connection successful'
            }
        else:
            health_status['checks']['redis'] = {
                'status': 'not_configured',
                'message': 'Redis not configured'
            }
    except ImportError:
        health_status['checks']['redis'] = {
            'status': 'unknown',
            'message': 'Redis library not available'
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        health_status['checks']['redis'] = {
            'status': 'unhealthy',
            'message': f'Redis connection failed: {str(e)}'
        }
        # Don't mark overall status as unhealthy if Redis fails (it's not critical for basic health)
    
    # Determine HTTP status code
    http_status = 200 if health_status['status'] == 'healthy' else 503
    
    return JsonResponse(health_status, status=http_status)


def liveness_check(request):
    """
    Simple liveness check - just confirms the service is running.
    Used by Kubernetes/Docker for basic liveness probes.
    """
    return JsonResponse({
        'status': 'alive',
        'service': 'postbro-backend'
    })


def readiness_check(request):
    """
    Readiness check - confirms the service is ready to accept traffic.
    Checks critical dependencies (database).
    """
    try:
        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        
        return JsonResponse({
            'status': 'ready',
            'service': 'postbro-backend'
        })
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return JsonResponse({
            'status': 'not_ready',
            'service': 'postbro-backend',
            'error': str(e)
        }, status=503)

