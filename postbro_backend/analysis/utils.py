"""
Utility functions for analysis processing
"""
import logging
import traceback
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from django.utils import timezone
from .models import PostAnalysisRequest, AnalysisStatusHistory

logger = logging.getLogger(__name__)


def create_status(
    analysis_request: PostAnalysisRequest,
    stage: str,
    message: str,
    metadata: Optional[Dict] = None,
    progress_percentage: int = 0,
    api_calls_made: int = 0,
    cost_estimate: Optional[Decimal] = None,
    duration_seconds: Optional[float] = None,
) -> AnalysisStatusHistory:
    """
    Create a status history entry for an analysis request.
    
    Args:
        analysis_request: The analysis request to create status for
        stage: The stage identifier (e.g., 'fetching_social_data')
        message: Human-readable status message
        metadata: Additional data (post_count, post_ids, etc.)
        progress_percentage: Progress percentage (0-100)
        api_calls_made: Number of API calls made
        cost_estimate: Estimated cost in USD
        duration_seconds: Duration of this stage in seconds
    
    Returns:
        The created AnalysisStatusHistory instance
    """
    status = AnalysisStatusHistory.objects.create(
        analysis_request=analysis_request,
        stage=stage,
        message=message,
        metadata=metadata or {},
        is_error=False,
        progress_percentage=progress_percentage,
        api_calls_made=api_calls_made,
        cost_estimate=cost_estimate,
        duration_seconds=duration_seconds,
    )
    
    logger.info(f"Created status for {analysis_request.id}: {stage} - {message}")
    return status


def create_error_status(
    analysis_request: PostAnalysisRequest,
    error_code: str,
    message: str,
    retryable: bool = False,
    actionable_message: Optional[str] = None,
    metadata: Optional[Dict] = None,
    progress_percentage: int = 0,
) -> AnalysisStatusHistory:
    """
    Create an error status history entry for an analysis request.
    
    Args:
        analysis_request: The analysis request to create error status for
        error_code: Machine-readable error code (e.g., 'RATE_LIMIT', 'INVALID_URL')
        message: Human-readable error message
        retryable: Whether the user can retry this operation
        actionable_message: Actionable message telling the user what they can do
        metadata: Additional error data
        progress_percentage: Progress percentage at time of error
    
    Returns:
        The created AnalysisStatusHistory instance
    """
    status = AnalysisStatusHistory.objects.create(
        analysis_request=analysis_request,
        stage=AnalysisStatusHistory.StatusStage.ERROR,
        message=message,
        metadata=metadata or {},
        is_error=True,
        error_code=error_code,
        retryable=retryable,
        actionable_message=actionable_message,
        progress_percentage=progress_percentage,
    )
    
    logger.error(f"Created error status for {analysis_request.id}: {error_code} - {message}")
    return status


def create_partial_success_status(
    analysis_request: PostAnalysisRequest,
    succeeded: int,
    failed: int,
    total: int,
    failed_urls: Optional[List[str]] = None,
    succeeded_post_ids: Optional[List[str]] = None,
) -> AnalysisStatusHistory:
    """
    Create a partial success status when some URLs succeeded and some failed.
    
    Args:
        analysis_request: The analysis request
        succeeded: Number of URLs that succeeded
        failed: Number of URLs that failed
        total: Total number of URLs
        failed_urls: List of URLs that failed
        succeeded_post_ids: List of post IDs that succeeded
    
    Returns:
        The created AnalysisStatusHistory instance
    """
    progress_percentage = int((succeeded / total) * 50) if total > 0 else 0  # Max 50% for partial success
    
    status = AnalysisStatusHistory.objects.create(
        analysis_request=analysis_request,
        stage=AnalysisStatusHistory.StatusStage.PARTIAL_SUCCESS,
        message=f'Fetched {succeeded} of {total} posts successfully. {failed} failed.',
        metadata={
            'succeeded': succeeded,
            'failed': failed,
            'total': total,
            'failed_urls': failed_urls or [],
            'succeeded_post_ids': succeeded_post_ids or [],
        },
        is_error=False,
        progress_percentage=progress_percentage,
    )
    
    logger.warning(f"Created partial success status for {analysis_request.id}: {succeeded}/{total} succeeded")
    return status


def estimate_cost(
    platform: str,
    api_calls: int,
    operation_type: str = 'scraping',
) -> Decimal:
    """
    Estimate the cost of API operations.
    
    Args:
        platform: Platform name ('instagram', 'x', 'youtube')
        api_calls: Number of API calls made
        operation_type: Type of operation ('scraping', 'analysis', etc.)
    
    Returns:
        Estimated cost in USD as Decimal
    """
    # Cost per API call (in USD) - adjust based on your actual pricing
    cost_per_call = {
        'instagram': Decimal('0.01'),  # $0.01 per Instagram API call
        'x': Decimal('0.005'),  # $0.005 per X/Twitter API call
        'youtube': Decimal('0.002'),  # $0.002 per YouTube API call
    }
    
    base_cost = cost_per_call.get(platform.lower(), Decimal('0.01'))
    
    # Calculate total cost
    total_cost = base_cost * api_calls
    
    # Add operation type multiplier if needed
    if operation_type == 'analysis':
        total_cost *= Decimal('2.0')  # AI analysis costs more
    
    return total_cost


def calculate_progress_percentage(
    current_stage: str,
    total_stages: int = 6,
    stage_progress: float = 0.0,
) -> int:
    """
    Calculate progress percentage based on current stage and stage-specific progress.
    
    Args:
        current_stage: Current stage identifier
        total_stages: Total number of stages in the process
        stage_progress: Progress within current stage (0.0 to 1.0)
    
    Returns:
        Progress percentage (0-100)
    """
    # Stage mapping to approximate percentages
    stage_percentages = {
        'request_created': 0,
        'fetching_social_data': 10,
        'social_data_fetched': 50,
        'displaying_content': 60,
        'analyzing_posts': 70,
        'analysis_complete': 100,
    }
    
    # Get base percentage for current stage
    base_percentage = stage_percentages.get(current_stage, 0)
    
    # Add stage-specific progress (if provided)
    if stage_progress > 0:
        # Calculate stage range
        next_stage_percentage = 100
        for stage, percentage in stage_percentages.items():
            if percentage > base_percentage:
                next_stage_percentage = percentage
                break
        
        stage_range = next_stage_percentage - base_percentage
        additional_progress = int(stage_range * stage_progress)
        base_percentage += additional_progress
    
    return min(100, max(0, base_percentage))


def categorize_error(exception: Exception) -> str:
    """
    Categorize exception into error category for internal tracking.
    
    Args:
        exception: The exception that occurred
        
    Returns:
        Error category string (from PostAnalysisRequest.ErrorCategory)
    """
    error_str = str(exception).lower()
    error_type = type(exception).__name__
    
    # Rate limit errors
    if 'rate limit' in error_str or '429' in error_str or 'RateLimit' in error_type:
        return 'rate_limit'
    
    # Network errors
    if any(x in error_type for x in ['ConnectionError', 'Timeout', 'Network', 'ConnectTimeout']):
        return 'network_error'
    
    # Timeout errors
    if 'timeout' in error_str or 'Timeout' in error_type or 'timed out' in error_str:
        return 'timeout'
    
    # API errors (HTTP errors, API failures)
    if any(x in error_str for x in ['api', 'http', 'status code', '500', '502', '503', '504']):
        return 'api_error'
    
    # Quota errors
    if 'quota' in error_str or 'limit exceeded' in error_str or 'quota exceeded' in error_str:
        return 'quota_exceeded'
    
    # Validation errors
    if 'ValidationError' in error_type or 'invalid' in error_str or 'not found' in error_str:
        return 'validation_error'
    
    # Processing errors (general processing failures)
    if any(x in error_type for x in ['ValueError', 'TypeError', 'AttributeError', 'KeyError']):
        return 'processing_error'
    
    return 'unknown'


def is_retryable_error(exception: Exception) -> bool:
    """
    Determine if error is retryable (user can retry).
    
    Args:
        exception: The exception that occurred
        
    Returns:
        bool: True if error is retryable, False otherwise
    """
    error_code = categorize_error(exception)
    
    # Retryable errors (transient issues)
    retryable_codes = ['rate_limit', 'network_error', 'timeout', 'api_error']
    
    # Non-retryable errors (permanent issues)
    non_retryable_codes = ['validation_error', 'quota_exceeded']
    
    if error_code in retryable_codes:
        return True
    if error_code in non_retryable_codes:
        return False
    
    # Unknown errors - default to retryable (let user decide)
    return True


def get_user_friendly_error_message(error_stage: str, error_category: str, exception: Exception) -> Tuple[str, str]:
    """
    Get user-friendly error message and actionable message.
    ChatGPT-style: Simple, clear, no technical details.
    
    Args:
        error_stage: Stage where error occurred (internal)
        error_category: Category of error (internal)
        exception: The exception that occurred
        
    Returns:
        Tuple of (error_message, actionable_message)
    """
    # User-friendly messages based on stage (not technical details)
    stage_messages = {
        'social_collection': 'Failed to fetch post data from the platform.',
        'media_extraction': 'Failed to process media (images/videos).',
        'gemini_analysis': 'Failed to analyze with AI.',
    }
    
    # Base message
    base_message = stage_messages.get(error_stage, 'Analysis failed.')
    
    # Actionable messages based on error category
    actionable_messages = {
        'rate_limit': 'The API rate limit was exceeded. Please try again in a few minutes.',
        'network_error': 'A network error occurred. Please check your connection and try again.',
        'timeout': 'The request timed out. Please try again.',
        'api_error': 'An external API error occurred. Please try again in a few minutes.',
        'quota_exceeded': 'Your quota has been exceeded. Please upgrade your plan or try again tomorrow.',
        'validation_error': 'Invalid input data. Please check your URLs and try again.',
        'processing_error': 'An error occurred while processing your request. Please try again.',
        'unknown': 'An unexpected error occurred. Please try again or contact support if this persists.',
    }
    
    actionable_message = actionable_messages.get(error_category, actionable_messages['unknown'])
    
    return base_message, actionable_message


def get_error_details(exception: Exception, include_traceback: bool = False) -> Dict:
    """
    Get detailed error information for logging/debugging (internal use only).
    
    Args:
        exception: The exception that occurred
        include_traceback: Whether to include full traceback
        
    Returns:
        Dictionary with error details
    """
    details = {
        'exception_type': type(exception).__name__,
        'exception_message': str(exception),
        'error_category': categorize_error(exception),
    }
    
    if include_traceback:
        details['traceback'] = traceback.format_exc()
    
    # Add specific details for common exceptions
    if hasattr(exception, 'response'):
        details['response_status'] = getattr(exception.response, 'status_code', None)
        details['response_text'] = getattr(exception.response, 'text', None)[:500] if hasattr(exception.response, 'text') else None
    
    return details


def handle_analysis_error(
    analysis_request: PostAnalysisRequest,
    error_stage: str,
    exception: Exception,
    failed_at_stage: Optional[str] = None,
    metadata: Optional[Dict] = None,
) -> AnalysisStatusHistory:
    """
    Handle analysis error: categorize, log, create error status, and update request.
    
    This is the main error handling function - use this for all analysis errors.
    
    Args:
        analysis_request: The analysis request that failed
        error_stage: Stage where error occurred (from ErrorStage choices)
        exception: The exception that occurred
        failed_at_stage: Last successful stage before failure (for smart retry)
        metadata: Additional metadata for error status
        
    Returns:
        The created AnalysisStatusHistory error entry
    """
    error_category = categorize_error(exception)
    retryable = is_retryable_error(exception)
    error_message, actionable_message = get_user_friendly_error_message(
        error_stage, error_category, exception
    )
    
    # Get error details for logging
    error_details = get_error_details(exception, include_traceback=True)
    
    # Log error with full context
    logger.error(
        f"❌ [Analysis] Error in {error_stage} for analysis_request_id={analysis_request.id}: "
        f"{error_category} - {str(exception)}",
        exc_info=True,
        extra={
            'analysis_request_id': str(analysis_request.id),
            'user_id': str(analysis_request.user.id),
            'error_stage': error_stage,
            'error_category': error_category,
            'retryable': retryable,
        }
    )
    
    # Create error status
    error_status = create_error_status(
        analysis_request,
        error_code=error_category,
        message=error_message,
        retryable=retryable,
        actionable_message=actionable_message,
        metadata={
            **(metadata or {}),
            'error_stage': error_stage,
            'error_category': error_category,
        },
        progress_percentage=analysis_request.status_history.filter(is_error=False).last().progress_percentage if analysis_request.status_history.filter(is_error=False).exists() else 0,
    )
    
    # Update analysis request with error information
    analysis_request.status = PostAnalysisRequest.Status.FAILED
    analysis_request.error_stage = error_stage
    analysis_request.error_category = error_category
    analysis_request.error_message = error_message  # User-friendly message
    analysis_request.error_details = error_details  # Internal details
    analysis_request.failed_at_stage = failed_at_stage
    analysis_request.save()
    
    return error_status


