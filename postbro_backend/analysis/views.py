from django.shortcuts import render
from django.http import StreamingHttpResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .throttles import AnalyzeThrottle, ChatThrottle
from .models import PostAnalysisRequest, ChatSession, ChatMessage, PostAnalysis, AnalysisNote
from .serializers import (
    PostAnalysisRequestSerializer, PostAnalysisRequestCreateSerializer,
    ChatSessionSerializer, ChatSessionCreateSerializer, ChatMessageCreateSerializer,
    AnalysisNoteSerializer, AnalysisNoteCreateSerializer
)
from .tasks import process_analysis_request
from .utils import create_status
from .services.chat_service import send_chat_message
from .services.chat_streaming_service import stream_chat_message
from django.utils import timezone
from django.core.exceptions import PermissionDenied
from accounts.utils import check_usage_limit, increment_usage
import logging

logger = logging.getLogger(__name__)

# Create your views here.

@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([AnalyzeThrottle])  # 20 analyses per hour
def analyze_posts(request):
    """
    Endpoint to analyze posts from Instagram, X (Twitter), or YouTube
    
    Expected payload:
    {
        "platform": "instagram" or "x" or "youtube",
        "username": "elonmusk",  // optional
        "post_urls": ["https://x.com/elonmusk/status/1812258574049157405"],  // optional
        "date_range_type": "last_7_days" or "last_14_days" or "last_30_days"  // optional
    }
    """
    logger.info(f"🚀 [analyze_posts] Request received from user {request.user.id}")
    logger.info(f"📥 [analyze_posts] Request data: {request.data}")
    
    try:
        # Validate input data
        logger.info(f"🔍 [analyze_posts] Validating input data...")
        serializer = PostAnalysisRequestCreateSerializer(data=request.data)
        if not serializer.is_valid():
            logger.error(f"❌ [analyze_posts] Validation failed: {serializer.errors}")
            return Response(
                {
                    'error': 'Invalid input data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        platform = serializer.validated_data.get('platform')
        post_urls = serializer.validated_data.get('post_urls', [])
        
        logger.info(f"✅ [analyze_posts] Validation passed - platform: {platform}, post_urls: {len(post_urls)}")
        
        # Validate post_urls
        if not post_urls or len(post_urls) == 0:
            return Response(
                {'error': 'At least one post_url must be provided'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Always use URL lookups for usage tracking
        usage_type = 'url_lookups'
        
        # Check usage limit
        can_proceed, limit_info = check_usage_limit(
            request.user,
            platform,
            usage_type
        )
        
        if not can_proceed:
            return Response(
                {
                    'error': 'Usage limit reached',
                    'message': f'You have reached your daily limit of {limit_info["limit"]} URLs. Please upgrade your plan or try again tomorrow.',
                    'limit_info': limit_info
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Create the analysis request
        analysis_request = PostAnalysisRequest.objects.create(
            user=request.user,
            **serializer.validated_data
        )
        
        # Increment usage (after successful creation)
        increment_usage(request.user, platform, usage_type)
        
        # Create initial status
        create_status(
            analysis_request,
            'request_created',
            'Analysis request created',
            metadata={
                'urls_count': len(analysis_request.post_urls),
                'platform': platform,
            },
            progress_percentage=0
        )
        
        # Trigger Celery task for processing
        logger.info(f"🚀 [analyze_posts] Triggering Celery task for analysis_request_id: {analysis_request.id}")
        try:
            task = process_analysis_request.delay(str(analysis_request.id))
            logger.info(f"✅ [analyze_posts] Celery task triggered successfully - task.id: {task.id}")
        except Exception as celery_error:
            logger.error(f"❌ [analyze_posts] Failed to trigger Celery task: {celery_error}", exc_info=True)
            raise
        
        # Update analysis request with task_id and status
        analysis_request.task_id = task.id
        analysis_request.status = PostAnalysisRequest.Status.PROCESSING
        analysis_request.save()
        logger.info(f"💾 [analyze_posts] Analysis request updated - task_id: {task.id}, status: PROCESSING")
        
        # Return the created analysis request
        response_serializer = PostAnalysisRequestSerializer(analysis_request)
        
        return Response(
            {
                'message': 'Analysis request created successfully',
                'analysis_request': response_serializer.data,
                'task_id': task.id,
                'status': 'processing',
                'usage_info': {
                    'current': limit_info['current'] + 1,
                    'limit': limit_info['limit'],
                    'remaining': limit_info['remaining'] - 1
                }
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        logger.exception(
            f"❌ [Analysis] Failed to create analysis request for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to create analysis request',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_requests(request):
    """
    Get analysis requests for the current user with pagination.
    
    Query parameters:
    - limit: Number of results to return (default: 15, max: 100)
    - offset: Number of results to skip (default: 0)
    """
    import time
    import logging
    logger = logging.getLogger(__name__)
    
    request_start_time = time.time()
    logger.info(f"📥 [get_analysis_requests] Request received at {time.time()}")
    
    try:
        # Get pagination parameters
        limit = int(request.query_params.get('limit', 15))
        offset = int(request.query_params.get('offset', 0))
        include_posts = request.query_params.get('include_posts', 'false').lower() == 'true'  # Default: false for performance
        include_status_history = request.query_params.get('include_status_history', 'false').lower() == 'true'  # Default: false for performance
        
        # Validate and cap limit
        limit = min(max(limit, 1), 100)  # Between 1 and 100
        offset = max(offset, 0)  # Non-negative
        
        # Get queryset ordered by most recent first
        queryset = PostAnalysisRequest.objects.filter(user=request.user).order_by('-created_at')
        
        # Get total count (before pagination)
        total_count = queryset.count()
        
        # Apply pagination and prefetch in one go
        # Only prefetch what's needed (sidebar doesn't need posts or status_history)
        prefetch_related = []
        if include_posts:
            prefetch_related.extend(['posts__media', 'posts__platform'])
        if include_status_history:
            prefetch_related.append('status_history')
        
        if prefetch_related:
            paginated_queryset = queryset[offset:offset + limit].prefetch_related(*prefetch_related).select_related('user')
        else:
            # Lightweight query for sidebar (no prefetch = fastest)
            paginated_queryset = queryset[offset:offset + limit].select_related('user')
        
        # Evaluate queryset to get list (posts are already prefetched)
        paginated_list = list(paginated_queryset)
        
        # Serialize only the paginated results
        # Pass flags to serializer to control what to include
        serializer = PostAnalysisRequestSerializer(
            paginated_list, 
            many=True,
            context={
                'include_posts': include_posts,
                'include_status_history': include_status_history
            }
        )
        
        # Calculate if there are more results
        has_more = (offset + limit) < total_count
        
        request_end_time = time.time()
        processing_time = request_end_time - request_start_time
        logger.info(f"📤 [get_analysis_requests] Response sent in {processing_time:.2f}s")
        
        return Response(
            {
                'requests': serializer.data,
                'count': total_count,  # Total count of all analyses
                'limit': limit,
                'offset': offset,
                'has_more': has_more
            },
            status=status.HTTP_200_OK
        )
        
    except ValueError as e:
        logger.warning(
            f"⚠️ [Analysis] Invalid pagination parameters for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Invalid pagination parameters',
                'details': str(e)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception(
            f"❌ [Analysis] Failed to fetch analysis requests for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch analysis requests',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_request(request, request_id):
    """
    Get a specific analysis request by ID
    """
    try:
        # Use prefetch_related for posts (ManyToMany) and status_history
        # Also prefetch media for posts to avoid N+1 queries
        analysis_request = PostAnalysisRequest.objects.prefetch_related(
            'status_history',
            'posts__media',  # Prefetch posts and their media
            'posts__platform',  # Prefetch platform for each post
            'post_analyses__post'  # Prefetch AI analysis results
        ).select_related('user').get(
            id=request_id, 
            user=request.user
        )
        serializer = PostAnalysisRequestSerializer(
            analysis_request,
            context={
                'include_posts': True,
                'include_status_history': True,
                'include_analyses': True
            }
        )
        
        return Response(
            {
                'analysis_request': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except PostAnalysisRequest.DoesNotExist:
        logger.warning(
            f"⚠️ [Analysis] Analysis request not found: request_id={request_id}, user_id={request.user.id}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Analysis request not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Analysis] Error fetching analysis_request_id={request_id} for user_id={request.user.id}: {e}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch analysis request',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retry_analysis(request, request_id):
    """
    Retry a failed analysis request.
    
    Only allows retry if:
    - Request is in 'failed' status
    - retry_count < max_retries
    - Error is retryable (from latest error status)
    
    Smart retry: Resumes from last successful stage (internal logic).
    """
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 [retry_analysis] Retry request for analysis_request_id={request_id}, user_id={request.user.id}")
    
    try:
        analysis_request = PostAnalysisRequest.objects.get(
            id=request_id,
            user=request.user
        )
    except PostAnalysisRequest.DoesNotExist:
        logger.warning(
            f"⚠️ [retry_analysis] Analysis request not found: request_id={request_id}, user_id={request.user.id}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Analysis request not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if can retry
    if analysis_request.status != PostAnalysisRequest.Status.FAILED:
        return Response(
            {
                'error': 'Analysis is not in failed state',
                'message': f'Analysis is currently {analysis_request.status}. Only failed analyses can be retried.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if analysis_request.retry_count >= analysis_request.max_retries:
        return Response(
            {
                'error': 'Maximum retry attempts reached',
                'message': f'You have reached the maximum of {analysis_request.max_retries} retry attempts. Please create a new analysis request.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if error is retryable
    latest_error = analysis_request.status_history.filter(is_error=True).order_by('-created_at').first()
    if latest_error and not latest_error.retryable:
        return Response(
            {
                'error': 'Error is not retryable',
                'message': latest_error.actionable_message or 'This error cannot be retried. Please check your input and try creating a new analysis.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Reset status and increment retry count
    analysis_request.status = PostAnalysisRequest.Status.PENDING
    analysis_request.retry_count += 1
    analysis_request.last_retry_at = timezone.now()
    # Clear error fields (will be set again if retry fails)
    analysis_request.error_message = None
    analysis_request.error_stage = None
    analysis_request.error_category = None
    analysis_request.error_details = {}
    analysis_request.failed_at_stage = None
    analysis_request.save()
    
    # Create retry status
    from .utils import create_status
    create_status(
        analysis_request,
        'retrying',
        f'Retrying analysis (attempt {analysis_request.retry_count}/{analysis_request.max_retries})...',
        metadata={
            'retry_count': analysis_request.retry_count,
            'previous_error': latest_error.error_code if latest_error else None,
            'failed_at_stage': analysis_request.failed_at_stage,
        },
        progress_percentage=0
    )
    
    # Trigger Celery task
    try:
        from .tasks import process_analysis_request
        task = process_analysis_request.delay(str(analysis_request.id))
        analysis_request.task_id = task.id
        analysis_request.status = PostAnalysisRequest.Status.PROCESSING
        analysis_request.save()
        
        logger.info(
            f"✅ [retry_analysis] Retry started for analysis_request_id={request_id}, "
            f"retry_count={analysis_request.retry_count}, task_id={task.id}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
    except Exception as e:
        logger.error(
            f"❌ [retry_analysis] Failed to trigger retry task for analysis_request_id={request_id}: {e}",
            exc_info=True,
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to start retry', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    from .serializers import PostAnalysisRequestSerializer
    serializer = PostAnalysisRequestSerializer(analysis_request)
    
    return Response({
        'message': 'Analysis retry started',
        'retry_count': analysis_request.retry_count,
        'analysis_request': serializer.data
    }, status=status.HTTP_200_OK)


# ==================== CHAT ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """
    Create or get existing chat session for a post analysis.
    
    Request body:
    {
        "post_analysis_id": "uuid"
    }
    """
    logger = logging.getLogger(__name__)
    logger.info(f"💬 [create_chat_session] Request from user {request.user.id}")
    
    try:
        serializer = ChatSessionCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid input data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        post_analysis_id = serializer.validated_data['post_analysis_id']
        
        # Get post analysis
        post_analysis = PostAnalysis.objects.select_related(
            'analysis_request__user'
        ).get(id=post_analysis_id)
        
        # Validate user owns the analysis
        if post_analysis.analysis_request.user != request.user:
            return Response(
                {
                    'error': 'Permission denied',
                    'message': 'You don\'t have permission to access this post analysis'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create chat session
        session, created = ChatSession.objects.get_or_create(
            post_analysis=post_analysis,
            user=request.user,
            defaults={'status': ChatSession.Status.ACTIVE}
        )
        
        # Prefetch messages for serializer
        session.messages.all()  # Trigger prefetch
        
        response_serializer = ChatSessionSerializer(session)
        
        logger.info(f"{'Created' if created else 'Retrieved'} chat session {session.id} for post_analysis {post_analysis_id}")
        
        return Response(
            {
                'session': response_serializer.data,
                'created': created
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        
    except PostAnalysis.DoesNotExist:
        logger.warning(
            f"⚠️ [Chat] Post analysis not found: post_analysis_id={post_analysis_id}, user_id={request.user.id}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Post analysis not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Failed to create chat session for post_analysis_id={post_analysis_id}, user_id={request.user.id}: {e}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to create chat session',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])  # 100 chat messages per hour
def chat_session_messages(request, session_id):
    """
    Send a message in a chat session (non-streaming, for backward compatibility).
    
    Request body:
    {
        "message": "How can I improve this post?"
    }
    """
    logger = logging.getLogger(__name__)
    logger.info(f"💬 [chat_session_messages] Sending message to session {session_id}")
    
    try:
        # Validate message
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid message',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_message = serializer.validated_data['message']
        
        # Check question usage limit (questions are tracked per user, not per platform)
        # Use 'instagram' as default platform for question tracking (it's user-level anyway)
        can_proceed, limit_info = check_usage_limit(
            request.user,
            'instagram',  # Platform doesn't matter for questions, but required by function
            'questions_asked'
        )
        
        if not can_proceed:
            return Response(
                {
                    'error': 'Usage limit reached',
                    'message': f'You have reached your daily limit of {limit_info["limit"]} questions. Please upgrade your plan or try again tomorrow.',
                    'limit_info': limit_info
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Send message via chat service
        result = send_chat_message(
            session_id=str(session_id),
            user_message=user_message,
            user_id=str(request.user.id)
        )
        
        logger.info(f"✅ [chat_session_messages] Message sent successfully")
        
        return Response(
            {
                'user_message': result['user_message'],
                'assistant_message': result['assistant_message'],
                'processing_time_seconds': result['processing_time_seconds']
            },
            status=status.HTTP_200_OK
        )
    
    except ChatSession.DoesNotExist:
        logger.warning(
            f"⚠️ [Chat] Chat session not found: chat_session_id={session_id}, user_id={request.user.id}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Chat session not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionDenied as e:
        logger.warning(
            f"⚠️ [Chat] Permission denied: chat_session_id={session_id}, user_id={request.user.id}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Permission denied',
                'message': str(e)
            },
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        logger.warning(
            f"⚠️ [Chat] Invalid request for chat_session_id={session_id}, user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Invalid request',
                'message': str(e)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Error in chat_session_id={session_id} for user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to send message',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])  # 100 chat messages per hour
def chat_session_messages_stream(request, session_id):
    """
    Stream chat message response using Server-Sent Events (SSE).
    
    Request body:
    {
        "message": "How can I improve this post?"
    }
    
    Response: Server-Sent Events stream
    - Chunks: data: {"chunk": "text", "type": "chunk"}\n\n
    - Done: data: {"done": True, "message_id": "...", "tokens_used": 123}\n\n
    - Error: data: {"error": "message", "type": "error"}\n\n
    """
    logger = logging.getLogger(__name__)
    logger.info(f"💬 [chat_session_messages_stream] Starting stream for session {session_id}")
    
    try:
        # Validate message
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            # For SSE, we need to send error as data event
            def error_stream():
                import json
                yield f"data: {json.dumps({'error': 'Invalid message', 'details': serializer.errors, 'type': 'error'})}\n\n"
            
            return StreamingHttpResponse(
                error_stream(),
                content_type='text/event-stream'
            )
        
        user_message = serializer.validated_data['message']
        
        # Check question usage limit (questions are tracked per user, not per platform)
        # Use 'instagram' as default platform for question tracking (it's user-level anyway)
        can_proceed, limit_info = check_usage_limit(
            request.user,
            'instagram',  # Platform doesn't matter for questions, but required by function
            'questions_asked'
        )
        
        if not can_proceed:
            def error_stream():
                import json
                limit_value = limit_info.get('limit', 0)
                error_data = {
                    'error': 'Usage limit reached',
                    'message': f'You have reached your daily limit of {limit_value} questions. Please upgrade your plan or try again tomorrow.',
                    'limit_info': limit_info,
                    'type': 'error'
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingHttpResponse(
                error_stream(),
                content_type='text/event-stream'
            )
        
        # Create generator for streaming response
        def event_stream():
            try:
                for chunk in stream_chat_message(
                    session_id=str(session_id),
                    user_message=user_message,
                    user_id=str(request.user.id)
                ):
                    yield chunk
            except Exception as e:
                import json
                logger.exception(
                    f"❌ [Chat] Stream error in chat_session_id={session_id} for user_id={request.user.id}: {e}",
                    extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
                )
                yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        
        # Set headers for SSE
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        
        logger.info(f"✅ [chat_session_messages_stream] Stream started")
        return response
    
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Stream setup error for chat_session_id={session_id}, user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        
        def error_stream():
            import json
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
        
        return StreamingHttpResponse(
            error_stream(),
            content_type='text/event-stream'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_session(request, session_id):
    """
    Get chat session with all messages.
    """
    logger = logging.getLogger(__name__)
    
    try:
        session = ChatSession.objects.prefetch_related('messages').select_related(
            'post_analysis',
            'user'
        ).get(id=session_id)
        
        # Validate user owns the session
        if session.user != request.user:
            return Response(
                {
                    'error': 'Permission denied',
                    'message': 'You don\'t have permission to access this chat session'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .serializers import ChatSessionSerializer
        response_serializer = ChatSessionSerializer(session)
        
        return Response(
            {
                'session': response_serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except ChatSession.DoesNotExist:
        logger.warning(
            f"⚠️ [Chat] Chat session not found: chat_session_id={session_id}, user_id={request.user.id}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Chat session not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Error fetching chat_session_id={session_id} for user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch chat session',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_chat_sessions(request):
    """
    List user's chat sessions.
    
    Query parameters:
    - post_analysis_id: Filter by post analysis ID (optional)
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"📋 [list_chat_sessions] Request from user {request.user.id}")
        
        # Add retry logic for database connection issues
        from django.db import connection
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                queryset = ChatSession.objects.filter(user=request.user).select_related(
                    'post_analysis',
                    'post_analysis__post'
                ).prefetch_related('messages').order_by('-updated_at')
                
                # Optional filter by post_analysis_id
                post_analysis_id = request.query_params.get('post_analysis_id')
                if post_analysis_id:
                    logger.info(f"📋 [list_chat_sessions] Filtering by post_analysis_id: {post_analysis_id}")
                    try:
                        queryset = queryset.filter(post_analysis_id=post_analysis_id)
                    except ValueError:
                        return Response(
                            {
                                'error': 'Invalid post_analysis_id format'
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                sessions = list(queryset[:50])  # Limit to 50 most recent
                logger.info(f"✅ [list_chat_sessions] Found {len(sessions)} sessions")
                break  # Success, exit retry loop
                
            except Exception as db_error:
                retry_count += 1
                error_str = str(db_error)
                logger.warning(f"⚠️ [list_chat_sessions] Database error (attempt {retry_count}/{max_retries}): {error_str}")
                
                if retry_count >= max_retries:
                    # Close connection and re-raise
                    connection.close()
                    logger.error(
                        f"❌ [Chat] Max retries reached for list_chat_sessions, user_id={request.user.id}",
                        extra={'user_id': str(request.user.id)}
                    )
                    raise
                else:
                    # Wait a bit before retry
                    import time
                    time.sleep(0.1 * retry_count)  # 0.1s, 0.2s, 0.3s
                    connection.close()  # Close bad connection
        
        from .serializers import ChatSessionSerializer
        response_serializer = ChatSessionSerializer(sessions, many=True)
        
        return Response(
            {
                'sessions': response_serializer.data,
                'count': len(sessions)
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Error listing chat sessions for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch chat sessions',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_note(request, post_analysis_id):
    """
    Get or create note for a specific post analysis.
    Returns existing note if found, or None if not found.
    """
    logger = logging.getLogger(__name__)
    
    try:
        post_analysis = PostAnalysis.objects.select_related(
            'analysis_request__user'
        ).get(id=post_analysis_id)
        
        # Check permission
        if post_analysis.analysis_request.user != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or return None
        note = AnalysisNote.objects.filter(
            user=request.user,
            post_analysis=post_analysis
        ).first()
        
        if note:
            serializer = AnalysisNoteSerializer(note)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'note': None}, status=status.HTTP_200_OK)
    
    except PostAnalysis.DoesNotExist:
        logger.warning(
            f"⚠️ [Notes] Post analysis not found: post_analysis_id={post_analysis_id}, user_id={request.user.id}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Post analysis not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error fetching note for post_analysis_id={post_analysis_id}, user_id={request.user.id}: {e}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to fetch note', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def create_or_update_analysis_note(request):
    """
    Create or update note for a post analysis.
    POST/PUT: Create if doesn't exist, update if exists.
    """
    logger = logging.getLogger(__name__)
    
    try:
        serializer = AnalysisNoteCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        post_analysis_id = serializer.validated_data['post_analysis_id']
        title = serializer.validated_data['title']
        content = serializer.validated_data['content']
        
        post_analysis = PostAnalysis.objects.select_related(
            'analysis_request__user'
        ).get(id=post_analysis_id)
        
        # Check permission
        if post_analysis.analysis_request.user != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create note
        note, created = AnalysisNote.objects.get_or_create(
            user=request.user,
            post_analysis=post_analysis,
            defaults={
                'title': title,
                'content': content
            }
        )
        
        # Update if exists
        if not created:
            note.title = title
            note.content = content
            note.save()
        
        response_serializer = AnalysisNoteSerializer(note)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    except PostAnalysis.DoesNotExist:
        logger.warning(
            f"⚠️ [Notes] Post analysis not found: post_analysis_id={post_analysis_id}, user_id={request.user.id}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Post analysis not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error saving note for post_analysis_id={post_analysis_id}, user_id={request.user.id}: {e}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to save note', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_analysis_notes(request):
    """
    List all notes for the current user, ordered by updated_at (newest first).
    """
    logger = logging.getLogger(__name__)
    
    try:
        notes = AnalysisNote.objects.filter(
            user=request.user
        ).select_related(
            'post_analysis',
            'post_analysis__post',
            'post_analysis__analysis_request'
        ).order_by('-updated_at')
        
        serializer = AnalysisNoteSerializer(notes, many=True)
        return Response(
            {
                'notes': serializer.data,
                'count': len(serializer.data)
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error listing notes for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to fetch notes', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_analysis_note(request, note_id):
    """
    Delete a note.
    """
    logger = logging.getLogger(__name__)
    
    try:
        note = AnalysisNote.objects.select_related(
            'user',
            'post_analysis__analysis_request__user'
        ).get(id=note_id)
        
        # Check permission
        if note.user != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        note.delete()
        return Response(
            {'message': 'Note deleted successfully'},
            status=status.HTTP_200_OK
        )
    
    except AnalysisNote.DoesNotExist:
        logger.warning(
            f"⚠️ [Notes] Note not found: note_id={note_id}, user_id={request.user.id}",
            extra={'note_id': str(note_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Note not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error deleting note_id={note_id} for user_id={request.user.id}: {e}",
            extra={'note_id': str(note_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to delete note', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

        return Response(
            {
                'error': 'Failed to create analysis request',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_requests(request):
    """
    Get analysis requests for the current user with pagination.
    
    Query parameters:
    - limit: Number of results to return (default: 15, max: 100)
    - offset: Number of results to skip (default: 0)
    """
    import time
    import logging
    logger = logging.getLogger(__name__)
    
    request_start_time = time.time()
    logger.info(f"📥 [get_analysis_requests] Request received at {time.time()}")
    
    try:
        # Get pagination parameters
        limit = int(request.query_params.get('limit', 15))
        offset = int(request.query_params.get('offset', 0))
        include_posts = request.query_params.get('include_posts', 'false').lower() == 'true'  # Default: false for performance
        include_status_history = request.query_params.get('include_status_history', 'false').lower() == 'true'  # Default: false for performance
        
        # Validate and cap limit
        limit = min(max(limit, 1), 100)  # Between 1 and 100
        offset = max(offset, 0)  # Non-negative
        
        # Get queryset ordered by most recent first
        queryset = PostAnalysisRequest.objects.filter(user=request.user).order_by('-created_at')
        
        # Get total count (before pagination)
        total_count = queryset.count()
        
        # Apply pagination and prefetch in one go
        # Only prefetch what's needed (sidebar doesn't need posts or status_history)
        prefetch_related = []
        if include_posts:
            prefetch_related.extend(['posts__media', 'posts__platform'])
        if include_status_history:
            prefetch_related.append('status_history')
        
        if prefetch_related:
            paginated_queryset = queryset[offset:offset + limit].prefetch_related(*prefetch_related).select_related('user')
        else:
            # Lightweight query for sidebar (no prefetch = fastest)
            paginated_queryset = queryset[offset:offset + limit].select_related('user')
        
        # Evaluate queryset to get list (posts are already prefetched)
        paginated_list = list(paginated_queryset)
        
        # Serialize only the paginated results
        # Pass flags to serializer to control what to include
        serializer = PostAnalysisRequestSerializer(
            paginated_list, 
            many=True,
            context={
                'include_posts': include_posts,
                'include_status_history': include_status_history
            }
        )
        
        # Calculate if there are more results
        has_more = (offset + limit) < total_count
        
        request_end_time = time.time()
        processing_time = request_end_time - request_start_time
        logger.info(f"📤 [get_analysis_requests] Response sent in {processing_time:.2f}s")
        
        return Response(
            {
                'requests': serializer.data,
                'count': total_count,  # Total count of all analyses
                'limit': limit,
                'offset': offset,
                'has_more': has_more
            },
            status=status.HTTP_200_OK
        )
        
    except ValueError as e:
        logger.warning(
            f"⚠️ [Analysis] Invalid pagination parameters for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Invalid pagination parameters',
                'details': str(e)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception(
            f"❌ [Analysis] Failed to fetch analysis requests for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch analysis requests',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_request(request, request_id):
    """
    Get a specific analysis request by ID
    """
    try:
        # Use prefetch_related for posts (ManyToMany) and status_history
        # Also prefetch media for posts to avoid N+1 queries
        analysis_request = PostAnalysisRequest.objects.prefetch_related(
            'status_history',
            'posts__media',  # Prefetch posts and their media
            'posts__platform',  # Prefetch platform for each post
            'post_analyses__post'  # Prefetch AI analysis results
        ).select_related('user').get(
            id=request_id, 
            user=request.user
        )
        serializer = PostAnalysisRequestSerializer(
            analysis_request,
            context={
                'include_posts': True,
                'include_status_history': True,
                'include_analyses': True
            }
        )
        
        return Response(
            {
                'analysis_request': serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except PostAnalysisRequest.DoesNotExist:
        logger.warning(
            f"⚠️ [Analysis] Analysis request not found: request_id={request_id}, user_id={request.user.id}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Analysis request not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Analysis] Error fetching analysis_request_id={request_id} for user_id={request.user.id}: {e}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch analysis request',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def retry_analysis(request, request_id):
    """
    Retry a failed analysis request.
    
    Only allows retry if:
    - Request is in 'failed' status
    - retry_count < max_retries
    - Error is retryable (from latest error status)
    
    Smart retry: Resumes from last successful stage (internal logic).
    """
    logger = logging.getLogger(__name__)
    logger.info(f"🔄 [retry_analysis] Retry request for analysis_request_id={request_id}, user_id={request.user.id}")
    
    try:
        analysis_request = PostAnalysisRequest.objects.get(
            id=request_id,
            user=request.user
        )
    except PostAnalysisRequest.DoesNotExist:
        logger.warning(
            f"⚠️ [retry_analysis] Analysis request not found: request_id={request_id}, user_id={request.user.id}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Analysis request not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Check if can retry
    if analysis_request.status != PostAnalysisRequest.Status.FAILED:
        return Response(
            {
                'error': 'Analysis is not in failed state',
                'message': f'Analysis is currently {analysis_request.status}. Only failed analyses can be retried.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if analysis_request.retry_count >= analysis_request.max_retries:
        return Response(
            {
                'error': 'Maximum retry attempts reached',
                'message': f'You have reached the maximum of {analysis_request.max_retries} retry attempts. Please create a new analysis request.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Check if error is retryable
    latest_error = analysis_request.status_history.filter(is_error=True).order_by('-created_at').first()
    if latest_error and not latest_error.retryable:
        return Response(
            {
                'error': 'Error is not retryable',
                'message': latest_error.actionable_message or 'This error cannot be retried. Please check your input and try creating a new analysis.'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Reset status and increment retry count
    analysis_request.status = PostAnalysisRequest.Status.PENDING
    analysis_request.retry_count += 1
    analysis_request.last_retry_at = timezone.now()
    # Clear error fields (will be set again if retry fails)
    analysis_request.error_message = None
    analysis_request.error_stage = None
    analysis_request.error_category = None
    analysis_request.error_details = {}
    analysis_request.failed_at_stage = None
    analysis_request.save()
    
    # Create retry status
    from .utils import create_status
    create_status(
        analysis_request,
        'retrying',
        f'Retrying analysis (attempt {analysis_request.retry_count}/{analysis_request.max_retries})...',
        metadata={
            'retry_count': analysis_request.retry_count,
            'previous_error': latest_error.error_code if latest_error else None,
            'failed_at_stage': analysis_request.failed_at_stage,
        },
        progress_percentage=0
    )
    
    # Trigger Celery task
    try:
        from .tasks import process_analysis_request
        task = process_analysis_request.delay(str(analysis_request.id))
        analysis_request.task_id = task.id
        analysis_request.status = PostAnalysisRequest.Status.PROCESSING
        analysis_request.save()
        
        logger.info(
            f"✅ [retry_analysis] Retry started for analysis_request_id={request_id}, "
            f"retry_count={analysis_request.retry_count}, task_id={task.id}",
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
    except Exception as e:
        logger.error(
            f"❌ [retry_analysis] Failed to trigger retry task for analysis_request_id={request_id}: {e}",
            exc_info=True,
            extra={'analysis_request_id': str(request_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to start retry', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    from .serializers import PostAnalysisRequestSerializer
    serializer = PostAnalysisRequestSerializer(analysis_request)
    
    return Response({
        'message': 'Analysis retry started',
        'retry_count': analysis_request.retry_count,
        'analysis_request': serializer.data
    }, status=status.HTTP_200_OK)


# ==================== CHAT ENDPOINTS ====================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_chat_session(request):
    """
    Create or get existing chat session for a post analysis.
    
    Request body:
    {
        "post_analysis_id": "uuid"
    }
    """
    logger = logging.getLogger(__name__)
    logger.info(f"💬 [create_chat_session] Request from user {request.user.id}")
    
    try:
        serializer = ChatSessionCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid input data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        post_analysis_id = serializer.validated_data['post_analysis_id']
        
        # Get post analysis
        post_analysis = PostAnalysis.objects.select_related(
            'analysis_request__user'
        ).get(id=post_analysis_id)
        
        # Validate user owns the analysis
        if post_analysis.analysis_request.user != request.user:
            return Response(
                {
                    'error': 'Permission denied',
                    'message': 'You don\'t have permission to access this post analysis'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create chat session
        session, created = ChatSession.objects.get_or_create(
            post_analysis=post_analysis,
            user=request.user,
            defaults={'status': ChatSession.Status.ACTIVE}
        )
        
        # Prefetch messages for serializer
        session.messages.all()  # Trigger prefetch
        
        response_serializer = ChatSessionSerializer(session)
        
        logger.info(f"{'Created' if created else 'Retrieved'} chat session {session.id} for post_analysis {post_analysis_id}")
        
        return Response(
            {
                'session': response_serializer.data,
                'created': created
            },
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
        
    except PostAnalysis.DoesNotExist:
        logger.warning(
            f"⚠️ [Chat] Post analysis not found: post_analysis_id={post_analysis_id}, user_id={request.user.id}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Post analysis not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Failed to create chat session for post_analysis_id={post_analysis_id}, user_id={request.user.id}: {e}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to create chat session',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])  # 100 chat messages per hour
def chat_session_messages(request, session_id):
    """
    Send a message in a chat session (non-streaming, for backward compatibility).
    
    Request body:
    {
        "message": "How can I improve this post?"
    }
    """
    logger = logging.getLogger(__name__)
    logger.info(f"💬 [chat_session_messages] Sending message to session {session_id}")
    
    try:
        # Validate message
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {
                    'error': 'Invalid message',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_message = serializer.validated_data['message']
        
        # Check question usage limit (questions are tracked per user, not per platform)
        # Use 'instagram' as default platform for question tracking (it's user-level anyway)
        can_proceed, limit_info = check_usage_limit(
            request.user,
            'instagram',  # Platform doesn't matter for questions, but required by function
            'questions_asked'
        )
        
        if not can_proceed:
            return Response(
                {
                    'error': 'Usage limit reached',
                    'message': f'You have reached your daily limit of {limit_info["limit"]} questions. Please upgrade your plan or try again tomorrow.',
                    'limit_info': limit_info
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Send message via chat service
        result = send_chat_message(
            session_id=str(session_id),
            user_message=user_message,
            user_id=str(request.user.id)
        )
        
        logger.info(f"✅ [chat_session_messages] Message sent successfully")
        
        return Response(
            {
                'user_message': result['user_message'],
                'assistant_message': result['assistant_message'],
                'processing_time_seconds': result['processing_time_seconds']
            },
            status=status.HTTP_200_OK
        )
    
    except ChatSession.DoesNotExist:
        logger.warning(
            f"⚠️ [Chat] Chat session not found: chat_session_id={session_id}, user_id={request.user.id}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Chat session not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except PermissionDenied as e:
        logger.warning(
            f"⚠️ [Chat] Permission denied: chat_session_id={session_id}, user_id={request.user.id}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Permission denied',
                'message': str(e)
            },
            status=status.HTTP_403_FORBIDDEN
        )
    except ValueError as e:
        logger.warning(
            f"⚠️ [Chat] Invalid request for chat_session_id={session_id}, user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Invalid request',
                'message': str(e)
            },
            status=status.HTTP_400_BAD_REQUEST
        )
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Error in chat_session_id={session_id} for user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to send message',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@throttle_classes([ChatThrottle])  # 100 chat messages per hour
def chat_session_messages_stream(request, session_id):
    """
    Stream chat message response using Server-Sent Events (SSE).
    
    Request body:
    {
        "message": "How can I improve this post?"
    }
    
    Response: Server-Sent Events stream
    - Chunks: data: {"chunk": "text", "type": "chunk"}\n\n
    - Done: data: {"done": True, "message_id": "...", "tokens_used": 123}\n\n
    - Error: data: {"error": "message", "type": "error"}\n\n
    """
    logger = logging.getLogger(__name__)
    logger.info(f"💬 [chat_session_messages_stream] Starting stream for session {session_id}")
    
    try:
        # Validate message
        serializer = ChatMessageCreateSerializer(data=request.data)
        if not serializer.is_valid():
            # For SSE, we need to send error as data event
            def error_stream():
                import json
                yield f"data: {json.dumps({'error': 'Invalid message', 'details': serializer.errors, 'type': 'error'})}\n\n"
            
            return StreamingHttpResponse(
                error_stream(),
                content_type='text/event-stream'
            )
        
        user_message = serializer.validated_data['message']
        
        # Check question usage limit (questions are tracked per user, not per platform)
        # Use 'instagram' as default platform for question tracking (it's user-level anyway)
        can_proceed, limit_info = check_usage_limit(
            request.user,
            'instagram',  # Platform doesn't matter for questions, but required by function
            'questions_asked'
        )
        
        if not can_proceed:
            def error_stream():
                import json
                limit_value = limit_info.get('limit', 0)
                error_data = {
                    'error': 'Usage limit reached',
                    'message': f'You have reached your daily limit of {limit_value} questions. Please upgrade your plan or try again tomorrow.',
                    'limit_info': limit_info,
                    'type': 'error'
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            
            return StreamingHttpResponse(
                error_stream(),
                content_type='text/event-stream'
            )
        
        # Create generator for streaming response
        def event_stream():
            try:
                for chunk in stream_chat_message(
                    session_id=str(session_id),
                    user_message=user_message,
                    user_id=str(request.user.id)
                ):
                    yield chunk
            except Exception as e:
                import json
                logger.exception(
                    f"❌ [Chat] Stream error in chat_session_id={session_id} for user_id={request.user.id}: {e}",
                    extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
                )
                yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
        
        response = StreamingHttpResponse(
            event_stream(),
            content_type='text/event-stream'
        )
        
        # Set headers for SSE
        response['Cache-Control'] = 'no-cache'
        response['X-Accel-Buffering'] = 'no'  # Disable nginx buffering
        
        logger.info(f"✅ [chat_session_messages_stream] Stream started")
        return response
    
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Stream setup error for chat_session_id={session_id}, user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        
        def error_stream():
            import json
            yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
        
        return StreamingHttpResponse(
            error_stream(),
            content_type='text/event-stream'
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_session(request, session_id):
    """
    Get chat session with all messages.
    """
    logger = logging.getLogger(__name__)
    
    try:
        session = ChatSession.objects.prefetch_related('messages').select_related(
            'post_analysis',
            'user'
        ).get(id=session_id)
        
        # Validate user owns the session
        if session.user != request.user:
            return Response(
                {
                    'error': 'Permission denied',
                    'message': 'You don\'t have permission to access this chat session'
                },
                status=status.HTTP_403_FORBIDDEN
            )
        
        from .serializers import ChatSessionSerializer
        response_serializer = ChatSessionSerializer(session)
        
        return Response(
            {
                'session': response_serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except ChatSession.DoesNotExist:
        logger.warning(
            f"⚠️ [Chat] Chat session not found: chat_session_id={session_id}, user_id={request.user.id}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Chat session not found'
            },
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Error fetching chat_session_id={session_id} for user_id={request.user.id}: {e}",
            extra={'chat_session_id': str(session_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch chat session',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_chat_sessions(request):
    """
    List user's chat sessions.
    
    Query parameters:
    - post_analysis_id: Filter by post analysis ID (optional)
    """
    logger = logging.getLogger(__name__)
    
    try:
        logger.info(f"📋 [list_chat_sessions] Request from user {request.user.id}")
        
        # Add retry logic for database connection issues
        from django.db import connection
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                queryset = ChatSession.objects.filter(user=request.user).select_related(
                    'post_analysis',
                    'post_analysis__post'
                ).prefetch_related('messages').order_by('-updated_at')
                
                # Optional filter by post_analysis_id
                post_analysis_id = request.query_params.get('post_analysis_id')
                if post_analysis_id:
                    logger.info(f"📋 [list_chat_sessions] Filtering by post_analysis_id: {post_analysis_id}")
                    try:
                        queryset = queryset.filter(post_analysis_id=post_analysis_id)
                    except ValueError:
                        return Response(
                            {
                                'error': 'Invalid post_analysis_id format'
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
                
                sessions = list(queryset[:50])  # Limit to 50 most recent
                logger.info(f"✅ [list_chat_sessions] Found {len(sessions)} sessions")
                break  # Success, exit retry loop
                
            except Exception as db_error:
                retry_count += 1
                error_str = str(db_error)
                logger.warning(f"⚠️ [list_chat_sessions] Database error (attempt {retry_count}/{max_retries}): {error_str}")
                
                if retry_count >= max_retries:
                    # Close connection and re-raise
                    connection.close()
                    logger.error(
                        f"❌ [Chat] Max retries reached for list_chat_sessions, user_id={request.user.id}",
                        extra={'user_id': str(request.user.id)}
                    )
                    raise
                else:
                    # Wait a bit before retry
                    import time
                    time.sleep(0.1 * retry_count)  # 0.1s, 0.2s, 0.3s
                    connection.close()  # Close bad connection
        
        from .serializers import ChatSessionSerializer
        response_serializer = ChatSessionSerializer(sessions, many=True)
        
        return Response(
            {
                'sessions': response_serializer.data,
                'count': len(sessions)
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.exception(
            f"❌ [Chat] Error listing chat sessions for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {
                'error': 'Failed to fetch chat sessions',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_analysis_note(request, post_analysis_id):
    """
    Get or create note for a specific post analysis.
    Returns existing note if found, or None if not found.
    """
    logger = logging.getLogger(__name__)
    
    try:
        post_analysis = PostAnalysis.objects.select_related(
            'analysis_request__user'
        ).get(id=post_analysis_id)
        
        # Check permission
        if post_analysis.analysis_request.user != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or return None
        note = AnalysisNote.objects.filter(
            user=request.user,
            post_analysis=post_analysis
        ).first()
        
        if note:
            serializer = AnalysisNoteSerializer(note)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'note': None}, status=status.HTTP_200_OK)
    
    except PostAnalysis.DoesNotExist:
        logger.warning(
            f"⚠️ [Notes] Post analysis not found: post_analysis_id={post_analysis_id}, user_id={request.user.id}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Post analysis not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error fetching note for post_analysis_id={post_analysis_id}, user_id={request.user.id}: {e}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to fetch note', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST', 'PUT'])
@permission_classes([IsAuthenticated])
def create_or_update_analysis_note(request):
    """
    Create or update note for a post analysis.
    POST/PUT: Create if doesn't exist, update if exists.
    """
    logger = logging.getLogger(__name__)
    
    try:
        serializer = AnalysisNoteCreateSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid data', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        post_analysis_id = serializer.validated_data['post_analysis_id']
        title = serializer.validated_data['title']
        content = serializer.validated_data['content']
        
        post_analysis = PostAnalysis.objects.select_related(
            'analysis_request__user'
        ).get(id=post_analysis_id)
        
        # Check permission
        if post_analysis.analysis_request.user != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create note
        note, created = AnalysisNote.objects.get_or_create(
            user=request.user,
            post_analysis=post_analysis,
            defaults={
                'title': title,
                'content': content
            }
        )
        
        # Update if exists
        if not created:
            note.title = title
            note.content = content
            note.save()
        
        response_serializer = AnalysisNoteSerializer(note)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )
    
    except PostAnalysis.DoesNotExist:
        logger.warning(
            f"⚠️ [Notes] Post analysis not found: post_analysis_id={post_analysis_id}, user_id={request.user.id}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Post analysis not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error saving note for post_analysis_id={post_analysis_id}, user_id={request.user.id}: {e}",
            extra={'post_analysis_id': str(post_analysis_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to save note', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_analysis_notes(request):
    """
    List all notes for the current user, ordered by updated_at (newest first).
    """
    logger = logging.getLogger(__name__)
    
    try:
        notes = AnalysisNote.objects.filter(
            user=request.user
        ).select_related(
            'post_analysis',
            'post_analysis__post',
            'post_analysis__analysis_request'
        ).order_by('-updated_at')
        
        serializer = AnalysisNoteSerializer(notes, many=True)
        return Response(
            {
                'notes': serializer.data,
                'count': len(serializer.data)
            },
            status=status.HTTP_200_OK
        )
    
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error listing notes for user_id={request.user.id}: {e}",
            extra={'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to fetch notes', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_analysis_note(request, note_id):
    """
    Delete a note.
    """
    logger = logging.getLogger(__name__)
    
    try:
        note = AnalysisNote.objects.select_related(
            'user',
            'post_analysis__analysis_request__user'
        ).get(id=note_id)
        
        # Check permission
        if note.user != request.user:
            return Response(
                {'error': 'Permission denied'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        note.delete()
        return Response(
            {'message': 'Note deleted successfully'},
            status=status.HTTP_200_OK
        )
    
    except AnalysisNote.DoesNotExist:
        logger.warning(
            f"⚠️ [Notes] Note not found: note_id={note_id}, user_id={request.user.id}",
            extra={'note_id': str(note_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Note not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.exception(
            f"❌ [Notes] Error deleting note_id={note_id} for user_id={request.user.id}: {e}",
            extra={'note_id': str(note_id), 'user_id': str(request.user.id)}
        )
        return Response(
            {'error': 'Failed to delete note', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
