from rest_framework import serializers
from .models import PostAnalysisRequest, AnalysisStatusHistory, PostAnalysis, ChatSession, ChatMessage, AnalysisNote
from datetime import datetime, timedelta
from social.models import Post
from django.utils import timezone
from urllib.parse import urlparse
import uuid
import re

class AnalysisStatusHistorySerializer(serializers.ModelSerializer):
    """Serializer for analysis status history entries."""
    class Meta:
        model = AnalysisStatusHistory
        fields = [
            'id', 'stage', 'message', 'metadata',
            'is_error', 'error_code', 'retryable', 'actionable_message',
            'progress_percentage', 'duration_seconds',
            'api_calls_made', 'cost_estimate',
            'created_at'
        ]
        read_only_fields = fields


class PostAnalysisSerializer(serializers.ModelSerializer):
    """Serializer for AI analysis results of individual posts."""
    class Meta:
        model = PostAnalysis
        fields = [
            'id', 'post', 'task_id', 'is_viral', 'virality_reasoning',
            'quick_takeaways', 'content_observation', 'replicable_elements',
            'analysis_data', 'improvements', 'suggestions_for_future_posts',
            'viral_formula', 'metadata_used', 'llm_model', 
            'processing_time_seconds', 'created_at', 'updated_at'
        ]
        read_only_fields = fields


class PostAnalysisRequestSerializer(serializers.ModelSerializer):
    """Serializer for analysis requests with status history."""
    status_history = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()  # Returns display_name for sidebar (with fallback)
    posts = serializers.SerializerMethodField()  # Include posts in response
    post_analyses = serializers.SerializerMethodField()  # Include AI analysis results
    retry_count = serializers.IntegerField(read_only=True)
    max_retries = serializers.IntegerField(read_only=True)
    last_retry_at = serializers.DateTimeField(read_only=True)
    
    class Meta:
        model = PostAnalysisRequest
        fields = [
            'id', 'platform', 'username', 'display_name', 'post_urls',
            'status', 'task_id', 'results', 'error_message',
            'retry_count', 'max_retries', 'last_retry_at',
            'status_history', 'posts', 'post_analyses',
            'created_at', 'updated_at', 'completed_at'
        ]
        read_only_fields = [
            'id', 'status', 
            'task_id', 'results', 'error_message',
            'retry_count', 'max_retries', 'last_retry_at',
            'status_history',
            'created_at', 'updated_at', 'completed_at'
        ]
    
    def get_status_history(self, obj):
        """Get all status history entries ordered by created_at."""
        # Check if status_history should be included (default: False for list view performance)
        include_status_history = self.context.get('include_status_history', False)
        if not include_status_history:
            return []  # Return empty array for list view (sidebar doesn't need it)
        
        # Use prefetched status_history (already prefetched in view)
        # Convert to list to use prefetched cache, then sort
        statuses = list(obj.status_history.all())
        # Sort by created_at (prefetched data, no new query)
        statuses.sort(key=lambda s: s.created_at)
        return AnalysisStatusHistorySerializer(statuses, many=True).data
    
    def get_username(self, obj):
        """
        Get display name for sidebar (ChatGPT-like behavior).
        
        Priority:
        1. display_name (stored when social data is fetched) - FASTEST, no queries needed
        2. Fallback to extracting from posts (ONLY if posts are prefetched - avoids N+1 queries)
        
        This eliminates the need to query posts just for sidebar display.
        """
        # First priority: Use stored display_name (set when social data is fetched)
        # This is the professional approach - denormalized for performance
        if obj.display_name:
            return obj.display_name
        
        # Fallback: Extract from posts (for old analyses created before display_name was added)
        # ONLY if posts are already prefetched (to avoid N+1 queries in list view)
        include_posts = self.context.get('include_posts', False)
        if include_posts:
            # Posts are prefetched - safe to access
            try:
                posts = list(obj.posts.all()[:2])  # Get first 2 posts (uses prefetch cache)
                if posts:
                    # Sort by posted_at
                    posts.sort(key=lambda p: p.posted_at if p.posted_at else timezone.now())
                    first_post = posts[0]
                    if first_post and first_post.username:
                        return first_post.username
            except Exception:
                pass
        
        # Final fallback: Use first URL as identifier
        if obj.post_urls and len(obj.post_urls) > 0:
            url = obj.post_urls[0]
            # Extract a short identifier from URL
            if '/' in url:
                parts = url.rstrip('/').split('/')
                return parts[-1][:30] if parts[-1] else url[:30]
            return url[:30]
        
        return None
    
    def get_posts(self, obj):
        """
        Serialize posts associated with this analysis request.
        Uses prefetched posts and media to avoid N+1 queries.
        Note: posts, media, and platform are already prefetched in the view.
        Only includes posts if include_posts=True in context (for performance).
        """
        # Check if posts should be included (default: False for list view performance)
        include_posts = self.context.get('include_posts', False)
        if not include_posts:
            return []  # Return empty array for list view (sidebar doesn't need full posts)
        
        # Use prefetched posts directly - don't create new queryset (bypasses prefetch)
        posts = list(obj.posts.all())  # This uses the prefetched cache
        
        posts_data = []
        for post in posts:
            # Get media - already prefetched via 'posts__media' in view
            # Using list() ensures we use the prefetched cache
            media = list(post.media.all())
            media_data = []
            for m in media:
                media_data.append({
                    'id': str(m.id),
                    'media_type': m.media_type,
                    'source_url': m.source_url,
                    'supabase_url': m.supabase_url,
                    'uploaded_to_supabase': m.uploaded_to_supabase,
                })
            
            # Get thumbnail (first image or video thumbnail)
            thumbnail = None
            thumbnail_media = post.media.filter(
                media_type__in=['image', 'video_thumbnail']
            ).first()
            if thumbnail_media:
                thumbnail = thumbnail_media.supabase_url or thumbnail_media.source_url
            
            posts_data.append({
                'id': str(post.id),
                'platform': post.platform.name,
                'platform_post_id': post.platform_post_id,
                'username': post.username,
                'content': post.content,
                'url': post.url,
                'engagement_score': post.engagement_score,
                'metrics': post.metrics,
                'posted_at': post.posted_at.isoformat(),
                'thumbnail': thumbnail,
                'media': media_data,
                'transcript': post.transcript,
                'formatted_transcript': post.formatted_transcript,
            })
        
        return posts_data
    
    def get_post_analyses(self, obj):
        """Get AI analysis results for posts."""
        include_analyses = self.context.get('include_analyses', True)  # Default: True
        if not include_analyses:
            return []
        
        # Use prefetched post_analyses if available
        analyses = list(obj.post_analyses.all())
        return PostAnalysisSerializer(analyses, many=True).data
    
    def validate(self, data):
        # post_urls is required (enforced at model level, but validate here too)
        post_urls = data.get('post_urls', [])
        if not post_urls or len(post_urls) == 0:
            raise serializers.ValidationError(
                "At least one post_url must be provided"
            )
        
        return data

class PostAnalysisRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostAnalysisRequest
        fields = [
            'platform', 'post_urls'
        ]
    
    def validate(self, data):
        # post_urls is required
        post_urls = data.get('post_urls', [])
        if not post_urls or len(post_urls) == 0:
            raise serializers.ValidationError(
                "At least one post_url must be provided"
            )
        
        # Validate that only one URL is provided
        if len(post_urls) > 1:
            raise serializers.ValidationError(
                "Only one URL is allowed at a time"
            )
        
        # Validate that URLs are from supported social media platforms
        platform = data.get('platform')
        url = post_urls[0]
        
        # Parse URL
        try:
            # Handle URLs without scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url.lower())
            hostname = parsed.netloc or ''
            
            # Clean hostname - remove www. and m. prefixes only
            if hostname.startswith('www.'):
                hostname = hostname[4:]
            if hostname.startswith('m.'):
                hostname = hostname[2:]
            
            if not hostname:
                raise serializers.ValidationError(
                    f"Invalid URL format: {url}. Please provide a complete URL with domain name."
                )
        except Exception as e:
            raise serializers.ValidationError(
                f"Invalid URL format: {url}. Error: {str(e)}"
            )
        
        # Define allowed domains for each platform
        allowed_domains = {
            'instagram': ['instagram.com', 'instagr.am'],
            'x': ['x.com', 'twitter.com', 't.co'],
            'youtube': ['youtube.com', 'youtu.be', 'm.youtube.com'],
        }
        
        # Check if URL matches the selected platform
        platform_domains = allowed_domains.get(platform, [])
        is_valid_domain = any(domain in hostname for domain in platform_domains)
        
        if not is_valid_domain:
            platform_names = {
                'instagram': 'Instagram',
                'x': 'X (Twitter)',
                'youtube': 'YouTube'
            }
            raise serializers.ValidationError(
                f"URL must be from {platform_names.get(platform, platform)}. "
                f"Detected domain: {hostname}. "
                f"Please provide a valid {platform_names.get(platform, platform)} post URL."
            )
        
        return data


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'tokens_used', 'created_at']
        read_only_fields = ['id', 'tokens_used', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions."""
    messages = ChatMessageSerializer(many=True, read_only=True)
    post_analysis_id = serializers.UUIDField(source='post_analysis.id', read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'post_analysis_id', 'status', 'messages', 'message_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        """Get count of messages in this session."""
        if hasattr(obj, 'messages'):
            return obj.messages.count()
        return 0


class ChatSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating a chat session."""
    post_analysis_id = serializers.UUIDField(required=True)
    
    def validate_post_analysis_id(self, value):
        """Validate that post_analysis exists and user has access."""
        try:
            post_analysis = PostAnalysis.objects.select_related(
                'analysis_request__user'
            ).get(id=value)
            
            # Check if user owns the analysis request
            request = self.context.get('request')
            if request and request.user:
                if post_analysis.analysis_request.user != request.user:
                    raise serializers.ValidationError(
                        "You don't have permission to access this post analysis"
                    )
            
            return value
        except PostAnalysis.DoesNotExist:
            raise serializers.ValidationError("Post analysis not found")


class ChatMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating a chat message."""
    message = serializers.CharField(
        required=True,
        max_length=5000,
        help_text='User message text (max 5000 characters)'
    )
    
    def validate_message(self, value):
        """Validate message is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


class AnalysisNoteSerializer(serializers.ModelSerializer):
    """Serializer for analysis notes."""
    post_analysis_id = serializers.UUIDField(source='post_analysis.id', read_only=True)
    
    class Meta:
        model = AnalysisNote
        fields = ['id', 'post_analysis_id', 'title', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalysisNoteCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating an analysis note."""
    post_analysis_id = serializers.UUIDField(required=True)
    title = serializers.CharField(required=True, max_length=200)
    content = serializers.CharField(required=True, allow_blank=True)
    
    def validate_post_analysis_id(self, value):
        """Validate that post_analysis exists and user has access."""
        try:
            post_analysis = PostAnalysis.objects.select_related(
                'analysis_request__user'
            ).get(id=value)
            
            # Check if user owns the analysis request
            request = self.context.get('request')
            if request and request.user:
                if post_analysis.analysis_request.user != request.user:
                    raise serializers.ValidationError(
                        "You don't have permission to access this post analysis"
                    )
            
            return value
        except PostAnalysis.DoesNotExist:
            raise serializers.ValidationError("Post analysis not found")
        # Check if status_history should be included (default: False for list view performance)
        include_status_history = self.context.get('include_status_history', False)
        if not include_status_history:
            return []  # Return empty array for list view (sidebar doesn't need it)
        
        # Use prefetched status_history (already prefetched in view)
        # Convert to list to use prefetched cache, then sort
        statuses = list(obj.status_history.all())
        # Sort by created_at (prefetched data, no new query)
        statuses.sort(key=lambda s: s.created_at)
        return AnalysisStatusHistorySerializer(statuses, many=True).data
    
    def get_username(self, obj):
        """
        Get display name for sidebar (ChatGPT-like behavior).
        
        Priority:
        1. display_name (stored when social data is fetched) - FASTEST, no queries needed
        2. Fallback to extracting from posts (ONLY if posts are prefetched - avoids N+1 queries)
        
        This eliminates the need to query posts just for sidebar display.
        """
        # First priority: Use stored display_name (set when social data is fetched)
        # This is the professional approach - denormalized for performance
        if obj.display_name:
            return obj.display_name
        
        # Fallback: Extract from posts (for old analyses created before display_name was added)
        # ONLY if posts are already prefetched (to avoid N+1 queries in list view)
        include_posts = self.context.get('include_posts', False)
        if include_posts:
            # Posts are prefetched - safe to access
            try:
                posts = list(obj.posts.all()[:2])  # Get first 2 posts (uses prefetch cache)
                if posts:
                    # Sort by posted_at
                    posts.sort(key=lambda p: p.posted_at if p.posted_at else timezone.now())
                    first_post = posts[0]
                    if first_post and first_post.username:
                        return first_post.username
            except Exception:
                pass
        
        # Final fallback: Use first URL as identifier
        if obj.post_urls and len(obj.post_urls) > 0:
            url = obj.post_urls[0]
            # Extract a short identifier from URL
            if '/' in url:
                parts = url.rstrip('/').split('/')
                return parts[-1][:30] if parts[-1] else url[:30]
            return url[:30]
        
        return None
    
    def get_posts(self, obj):
        """
        Serialize posts associated with this analysis request.
        Uses prefetched posts and media to avoid N+1 queries.
        Note: posts, media, and platform are already prefetched in the view.
        Only includes posts if include_posts=True in context (for performance).
        """
        # Check if posts should be included (default: False for list view performance)
        include_posts = self.context.get('include_posts', False)
        if not include_posts:
            return []  # Return empty array for list view (sidebar doesn't need full posts)
        
        # Use prefetched posts directly - don't create new queryset (bypasses prefetch)
        posts = list(obj.posts.all())  # This uses the prefetched cache
        
        posts_data = []
        for post in posts:
            # Get media - already prefetched via 'posts__media' in view
            # Using list() ensures we use the prefetched cache
            media = list(post.media.all())
            media_data = []
            for m in media:
                media_data.append({
                    'id': str(m.id),
                    'media_type': m.media_type,
                    'source_url': m.source_url,
                    'supabase_url': m.supabase_url,
                    'uploaded_to_supabase': m.uploaded_to_supabase,
                })
            
            # Get thumbnail (first image or video thumbnail)
            thumbnail = None
            thumbnail_media = post.media.filter(
                media_type__in=['image', 'video_thumbnail']
            ).first()
            if thumbnail_media:
                thumbnail = thumbnail_media.supabase_url or thumbnail_media.source_url
            
            posts_data.append({
                'id': str(post.id),
                'platform': post.platform.name,
                'platform_post_id': post.platform_post_id,
                'username': post.username,
                'content': post.content,
                'url': post.url,
                'engagement_score': post.engagement_score,
                'metrics': post.metrics,
                'posted_at': post.posted_at.isoformat(),
                'thumbnail': thumbnail,
                'media': media_data,
                'transcript': post.transcript,
                'formatted_transcript': post.formatted_transcript,
            })
        
        return posts_data
    
    def get_post_analyses(self, obj):
        """Get AI analysis results for posts."""
        include_analyses = self.context.get('include_analyses', True)  # Default: True
        if not include_analyses:
            return []
        
        # Use prefetched post_analyses if available
        analyses = list(obj.post_analyses.all())
        return PostAnalysisSerializer(analyses, many=True).data
    
    def validate(self, data):
        # post_urls is required (enforced at model level, but validate here too)
        post_urls = data.get('post_urls', [])
        if not post_urls or len(post_urls) == 0:
            raise serializers.ValidationError(
                "At least one post_url must be provided"
            )
        
        return data

class PostAnalysisRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostAnalysisRequest
        fields = [
            'platform', 'post_urls'
        ]
    
    def validate(self, data):
        # post_urls is required
        post_urls = data.get('post_urls', [])
        if not post_urls or len(post_urls) == 0:
            raise serializers.ValidationError(
                "At least one post_url must be provided"
            )
        
        # Validate that only one URL is provided
        if len(post_urls) > 1:
            raise serializers.ValidationError(
                "Only one URL is allowed at a time"
            )
        
        # Validate that URLs are from supported social media platforms
        platform = data.get('platform')
        url = post_urls[0]
        
        # Parse URL
        try:
            # Handle URLs without scheme
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            
            parsed = urlparse(url.lower())
            hostname = parsed.netloc or ''
            
            # Clean hostname - remove www. and m. prefixes only
            if hostname.startswith('www.'):
                hostname = hostname[4:]
            if hostname.startswith('m.'):
                hostname = hostname[2:]
            
            if not hostname:
                raise serializers.ValidationError(
                    f"Invalid URL format: {url}. Please provide a complete URL with domain name."
                )
        except Exception as e:
            raise serializers.ValidationError(
                f"Invalid URL format: {url}. Error: {str(e)}"
            )
        
        # Define allowed domains for each platform
        allowed_domains = {
            'instagram': ['instagram.com', 'instagr.am'],
            'x': ['x.com', 'twitter.com', 't.co'],
            'youtube': ['youtube.com', 'youtu.be', 'm.youtube.com'],
        }
        
        # Check if URL matches the selected platform
        platform_domains = allowed_domains.get(platform, [])
        is_valid_domain = any(domain in hostname for domain in platform_domains)
        
        if not is_valid_domain:
            platform_names = {
                'instagram': 'Instagram',
                'x': 'X (Twitter)',
                'youtube': 'YouTube'
            }
            raise serializers.ValidationError(
                f"URL must be from {platform_names.get(platform, platform)}. "
                f"Detected domain: {hostname}. "
                f"Please provide a valid {platform_names.get(platform, platform)} post URL."
            )
        
        return data


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages."""
    class Meta:
        model = ChatMessage
        fields = ['id', 'role', 'content', 'tokens_used', 'created_at']
        read_only_fields = ['id', 'tokens_used', 'created_at']


class ChatSessionSerializer(serializers.ModelSerializer):
    """Serializer for chat sessions."""
    messages = ChatMessageSerializer(many=True, read_only=True)
    post_analysis_id = serializers.UUIDField(source='post_analysis.id', read_only=True)
    message_count = serializers.SerializerMethodField()
    
    class Meta:
        model = ChatSession
        fields = [
            'id', 'post_analysis_id', 'status', 'messages', 'message_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'status', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        """Get count of messages in this session."""
        if hasattr(obj, 'messages'):
            return obj.messages.count()
        return 0


class ChatSessionCreateSerializer(serializers.Serializer):
    """Serializer for creating a chat session."""
    post_analysis_id = serializers.UUIDField(required=True)
    
    def validate_post_analysis_id(self, value):
        """Validate that post_analysis exists and user has access."""
        try:
            post_analysis = PostAnalysis.objects.select_related(
                'analysis_request__user'
            ).get(id=value)
            
            # Check if user owns the analysis request
            request = self.context.get('request')
            if request and request.user:
                if post_analysis.analysis_request.user != request.user:
                    raise serializers.ValidationError(
                        "You don't have permission to access this post analysis"
                    )
            
            return value
        except PostAnalysis.DoesNotExist:
            raise serializers.ValidationError("Post analysis not found")


class ChatMessageCreateSerializer(serializers.Serializer):
    """Serializer for creating a chat message."""
    message = serializers.CharField(
        required=True,
        max_length=5000,
        help_text='User message text (max 5000 characters)'
    )
    
    def validate_message(self, value):
        """Validate message is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("Message cannot be empty")
        return value.strip()


class AnalysisNoteSerializer(serializers.ModelSerializer):
    """Serializer for analysis notes."""
    post_analysis_id = serializers.UUIDField(source='post_analysis.id', read_only=True)
    
    class Meta:
        model = AnalysisNote
        fields = ['id', 'post_analysis_id', 'title', 'content', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AnalysisNoteCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating an analysis note."""
    post_analysis_id = serializers.UUIDField(required=True)
    title = serializers.CharField(required=True, max_length=200)
    content = serializers.CharField(required=True, allow_blank=True)
    
    def validate_post_analysis_id(self, value):
        """Validate that post_analysis exists and user has access."""
        try:
            post_analysis = PostAnalysis.objects.select_related(
                'analysis_request__user'
            ).get(id=value)
            
            # Check if user owns the analysis request
            request = self.context.get('request')
            if request and request.user:
                if post_analysis.analysis_request.user != request.user:
                    raise serializers.ValidationError(
                        "You don't have permission to access this post analysis"
                    )
            
            return value
        except PostAnalysis.DoesNotExist:
            raise serializers.ValidationError("Post analysis not found")