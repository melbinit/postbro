"""
Analytics Configuration

Centralized configuration for analytics and tracking system.
All settings can be overridden via environment variables.
"""
import os
from typing import List, Dict, Any


def get_analytics_config() -> Dict[str, Any]:
    """
    Get analytics configuration from environment variables with defaults.
    
    Returns:
        Dictionary with all analytics configuration settings
    """
    return {
        # Enable/disable analytics
        'ENABLED': os.getenv('ANALYTICS_ENABLED', 'True') == 'True',
        
        # Flush Strategy: 'time', 'count', or 'hybrid'
        'FLUSH_STRATEGY': os.getenv('ANALYTICS_FLUSH_STRATEGY', 'hybrid'),
        
        # Time-based flush: flush every N seconds
        'FLUSH_INTERVAL_SECONDS': int(os.getenv('ANALYTICS_FLUSH_INTERVAL_SECONDS', '10')),
        
        # Count-based flush: flush when queue reaches N logs
        'FLUSH_COUNT_THRESHOLD': int(os.getenv('ANALYTICS_FLUSH_COUNT_THRESHOLD', '100')),
        
        # Sampling configuration
        'ENABLE_SAMPLING': os.getenv('ANALYTICS_ENABLE_SAMPLING', 'False') == 'True',
        'SAMPLING_RATE': float(os.getenv('ANALYTICS_SAMPLING_RATE', '0.1')),  # 10%
        
        # Endpoints to skip tracking
        'SKIP_ENDPOINTS': [
            '/health/',
            '/health/live/',
            '/health/ready/',
            '/static/',
            '/media/',
            '/admin/',
            '/admin/jsi18n/',
        ],
        
        # Only track authenticated requests
        'TRACK_AUTHENTICATED_ONLY': os.getenv('ANALYTICS_TRACK_AUTHENTICATED_ONLY', 'False') == 'True',
        
        # Track request/response body sizes
        'TRACK_REQUEST_SIZE': os.getenv('ANALYTICS_TRACK_REQUEST_SIZE', 'True') == 'True',
        'TRACK_RESPONSE_SIZE': os.getenv('ANALYTICS_TRACK_RESPONSE_SIZE', 'True') == 'True',
        
        # Maximum request/response size to track (in bytes)
        'MAX_REQUEST_SIZE_BYTES': int(os.getenv('ANALYTICS_MAX_REQUEST_SIZE_BYTES', '10485760')),  # 10MB
        'MAX_RESPONSE_SIZE_BYTES': int(os.getenv('ANALYTICS_MAX_RESPONSE_SIZE_BYTES', '10485760')),  # 10MB
        
        # Error tracking
        'TRACK_ERRORS_ONLY': os.getenv('ANALYTICS_TRACK_ERRORS_ONLY', 'False') == 'True',  # Only log errors
        'LOG_QUERY_PARAMS': os.getenv('ANALYTICS_LOG_QUERY_PARAMS', 'True') == 'True',
        
        # Performance thresholds (for alerting)
        'SLOW_REQUEST_THRESHOLD_MS': int(os.getenv('ANALYTICS_SLOW_REQUEST_THRESHOLD_MS', '1000')),  # 1 second
        'VERY_SLOW_REQUEST_THRESHOLD_MS': int(os.getenv('ANALYTICS_VERY_SLOW_REQUEST_THRESHOLD_MS', '5000')),  # 5 seconds
    }


def should_track_endpoint(endpoint: str, config: Dict[str, Any] = None) -> bool:
    """
    Check if an endpoint should be tracked based on configuration.
    
    Args:
        endpoint: API endpoint path
        config: Analytics configuration (if None, fetches from get_analytics_config())
    
    Returns:
        True if endpoint should be tracked, False otherwise
    """
    if config is None:
        config = get_analytics_config()
    
    if not config['ENABLED']:
        return False
    
    # Check skip list
    skip_endpoints = config.get('SKIP_ENDPOINTS', [])
    for skip_pattern in skip_endpoints:
        if endpoint.startswith(skip_pattern):
            return False
    
    return True


def should_sample_request(endpoint: str, config: Dict[str, Any] = None) -> bool:
    """
    Determine if a request should be sampled (for high-traffic endpoints).
    
    Args:
        endpoint: API endpoint path
        config: Analytics configuration
    
    Returns:
        True if request should be logged, False if it should be skipped (sampled out)
    """
    if config is None:
        config = get_analytics_config()
    
    if not config.get('ENABLE_SAMPLING', False):
        return True  # No sampling, log everything
    
    import random
    sampling_rate = config.get('SAMPLING_RATE', 0.1)
    
    # Always log errors (100% error logging)
    # This check happens in middleware after we know if there's an error
    
    # Random sampling
    return random.random() < sampling_rate


# Export default config for easy access
ANALYTICS_CONFIG = get_analytics_config()

