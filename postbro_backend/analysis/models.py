import uuid
from decimal import Decimal
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.models import User


class PostAnalysisRequest(models.Model):
    class Platform(models.TextChoices):
        INSTAGRAM = 'instagram', _('Instagram')
        X = 'x', _('X (Twitter)')
        YOUTUBE = 'youtube', _('YouTube')

    class DateRangeType(models.TextChoices):
        LAST_7_DAYS = 'last_7_days', _('Last 7 Days')
        LAST_14_DAYS = 'last_14_days', _('Last 14 Days')
        LAST_30_DAYS = 'last_30_days', _('Last 30 Days')

    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        COMPLETED = 'completed', _('Completed')
        FAILED = 'failed', _('Failed')
    
    class ErrorStage(models.TextChoices):
        """Internal error stage tracking (not exposed to users)"""
        SOCIAL_COLLECTION = 'social_collection', _('Social Media Collection')
        MEDIA_EXTRACTION = 'media_extraction', _('Media Extraction & Upload')
        GEMINI_ANALYSIS = 'gemini_analysis', _('Gemini API Analysis')
    
    class ErrorCategory(models.TextChoices):
        """Internal error category tracking (not exposed to users)"""
        RATE_LIMIT = 'rate_limit', _('Rate Limit Exceeded')
        API_ERROR = 'api_error', _('External API Error')
        NETWORK_ERROR = 'network_error', _('Network Error')
        VALIDATION_ERROR = 'validation_error', _('Validation Error')
        PROCESSING_ERROR = 'processing_error', _('Processing Error')
        TIMEOUT = 'timeout', _('Request Timeout')
        QUOTA_EXCEEDED = 'quota_exceeded', _('Quota Exceeded')
        UNKNOWN = 'unknown', _('Unknown Error')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='analysis_requests')
    platform = models.CharField(max_length=20, choices=Platform.choices)
    display_name = models.CharField(
        max_length=255, 
        blank=True, 
        null=True, 
        help_text='Display name extracted from posts (for sidebar/title). Set automatically when social data is fetched.'
    )
    post_urls = models.JSONField(default=list, help_text='List of specific post URLs to analyze (required)')
    posts = models.ManyToManyField(
        'social.Post',
        related_name='analysis_requests',
        blank=True,
        help_text='Posts analyzed in this request (enables post reuse/caching)'
    )
    
    # Processing fields
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    task_id = models.CharField(max_length=255, blank=True, null=True, help_text='Celery task ID')
    results = models.JSONField(default=dict, blank=True, help_text='AI analysis results')
    error_message = models.TextField(blank=True, null=True, help_text='User-friendly error message if processing failed')
    
    # Error tracking (internal - for debugging and smart retry logic)
    error_stage = models.CharField(
        max_length=50,
        choices=ErrorStage.choices,
        null=True,
        blank=True,
        help_text='Internal: Stage where error occurred (not exposed to users)'
    )
    error_category = models.CharField(
        max_length=50,
        choices=ErrorCategory.choices,
        null=True,
        blank=True,
        help_text='Internal: Category of error (not exposed to users)'
    )
    error_details = models.JSONField(
        default=dict,
        blank=True,
        help_text='Internal: Detailed error information for debugging (exception type, traceback, etc.)'
    )
    failed_at_stage = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text='Internal: Last successful stage before failure (for smart retry)'
    )
    
    # Retry mechanism
    retry_count = models.PositiveIntegerField(
        default=0,
        help_text='Number of times this request has been retried'
    )
    max_retries = models.PositiveIntegerField(
        default=3,
        help_text='Maximum number of retry attempts allowed'
    )
    last_retry_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text='Timestamp of the last retry attempt'
    )
    
    # Business metrics (for analytics and monitoring)
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text='Total processing duration in seconds (calculated after completion)'
    )
    total_api_calls = models.IntegerField(
        default=0,
        help_text='Total number of external API calls made during processing'
    )
    posts_processed = models.IntegerField(
        default=0,
        help_text='Number of posts successfully processed'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['platform']),
            models.Index(fields=['display_name']),  # Index for fast sidebar queries
            models.Index(fields=['error_stage', 'error_category']),  # For error analytics
            models.Index(fields=['status', 'retry_count']),  # For retry queries
        ]

    def __str__(self):
        if self.post_urls:
            return f"{self.user.email} - {self.platform} - {len(self.post_urls)} URLs ({self.status})"
        return f"{self.user.email} - {self.platform} ({self.status})"

    def clean(self):
        """Validate that post_urls is provided"""
        from django.core.exceptions import ValidationError
        
        if not self.post_urls or len(self.post_urls) == 0:
            raise ValidationError("At least one post_url must be provided")
    
    def can_retry(self) -> bool:
        """
        Check if this request can be retried.
        
        Returns:
            bool: True if request can be retried, False otherwise
        """
        return self.retry_count < self.max_retries and self.status == 'failed'


class PostAnalysis(models.Model):
    """
    Stores AI analysis results for individual posts.
    Each post gets analyzed separately and results are stored here.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_request = models.ForeignKey(
        PostAnalysisRequest,
        on_delete=models.CASCADE,
        related_name='post_analyses',
        help_text='The analysis request this post analysis belongs to'
    )
    post = models.ForeignKey(
        'social.Post',
        on_delete=models.CASCADE,
        related_name='analyses',
        help_text='The post being analyzed'
    )
    
    # LLM Response Data (from v1.txt schema)
    task_id = models.CharField(max_length=255, help_text='Task ID from prompt')
    is_viral = models.BooleanField(default=False, help_text='Whether the post is viral')
    virality_reasoning = models.TextField(blank=True, help_text='Reasoning for virality (max 150 words)')
    
    # Quick takeaways (scannable insights)
    quick_takeaways = models.JSONField(
        default=list,
        blank=True,
        help_text='3-5 bullet points summarizing key reasons it went viral (or why it didn\'t)'
    )
    
    # Creator context (who posted this - celebrity, influencer, brand, etc.)
    creator_context = models.TextField(
        blank=True,
        help_text='Who is this creator? (celebrity, influencer, brand, etc.) If they have a large following, identify them by name. Their influence level and niche.'
    )
    
    # Content observation (what AI sees - transparency)
    content_observation = models.JSONField(
        default=dict,
        blank=True,
        help_text='Content observation: caption_observation, visual_observation, engagement_context, platform_signals'
    )
    
    # Replicable elements (prescriptive format)
    replicable_elements = models.JSONField(
        default=list,
        blank=True,
        help_text='Prescriptive replicable elements: "Hook type: [X] → works for [Y]" format'
    )
    
    # Analysis data (JSON structure matching prompt schema)
    analysis_data = models.JSONField(
        default=dict,
        help_text='Analysis data: platform, framework_used, strengths, weaknesses, deep_analysis (hook, structure, psychology)'
    )
    
    # Viral formula (1-2 line summary)
    viral_formula = models.TextField(
        blank=True,
        help_text='1-2 line summary of viral formula or improvement formula'
    )
    
    # Improvements
    improvements = models.JSONField(
        default=list,
        help_text='List of improvement suggestions (max 25 words each)'
    )
    
    # Future post suggestions
    suggestions_for_future_posts = models.JSONField(
        default=list,
        help_text='List of 4 future post suggestions with hook, outline, why_it_works'
    )
    
    # Metadata
    metadata_used = models.JSONField(
        default=dict,
        help_text='Metadata used in analysis: username, posted_at, requested_at, media_count, platform_metrics'
    )
    
    # LLM processing info
    llm_model = models.CharField(max_length=50, default='gemini-2.0-flash-exp', help_text='LLM model used')
    llm_response_raw = models.TextField(blank=True, help_text='Raw JSON response from LLM')
    processing_time_seconds = models.FloatField(null=True, blank=True, help_text='Time taken to process')
    
    # Analysis completion flag (for quick look)
    analysis_completed = models.BooleanField(
        default=False,
        help_text='Whether the analysis has been completed (first Gemini call done)'
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        unique_together = ['analysis_request', 'post']  # One analysis per post per request
        indexes = [
            models.Index(fields=['analysis_request', 'created_at']),
            models.Index(fields=['post']),
        ]
    
    def __str__(self):
        return f"Analysis for {self.post.username} - {self.analysis_request.platform}"


class AnalysisStatusHistory(models.Model):
    """
    Timestamped status history for analysis requests.
    
    This model stores a complete timeline of status updates for each analysis request,
    enabling a chat-like interface that can replay the entire analysis process.
    Supports real-time updates via Supabase Realtime.
    """
    
    class StatusStage(models.TextChoices):
        # Initial
        REQUEST_CREATED = 'request_created', _('Request Created')
        
        # Scraping phase
        FETCHING_POSTS = 'fetching_posts', _('Fetching Posts')
        FETCHING_SOCIAL_DATA = 'fetching_social_data', _('Fetching Social Data')  # Legacy, kept for compatibility
        SOCIAL_DATA_FETCHED = 'social_data_fetched', _('Social Data Fetched')
        
        # Media processing phase
        COLLECTING_MEDIA = 'collecting_media', _('Collecting Media')
        
        # Transcription phase
        TRANSCRIBING = 'transcribing', _('Transcribing Audio')
        
        # Display phase
        DISPLAYING_CONTENT = 'displaying_content', _('Displaying Content')
        
        # Analysis phase
        ANALYZING_POSTS = 'analyzing_posts', _('PostBro is analyzing these posts')  # Legacy, kept for compatibility
        ANALYSING = 'analysing', _('Analysing')
        ANALYSIS_COMPLETE = 'analysis_complete', _('Analysis Complete')
        
        # Error states
        PARTIAL_SUCCESS = 'partial_success', _('Partial Success')
        ERROR = 'error', _('Error Occurred')
        RETRYING = 'retrying', _('Retrying...')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis_request = models.ForeignKey(
        PostAnalysisRequest,
        on_delete=models.CASCADE,
        related_name='status_history',
        help_text='The analysis request this status belongs to'
    )
    stage = models.CharField(
        max_length=50,
        choices=StatusStage.choices,
        help_text='Current stage of the analysis process'
    )
    message = models.TextField(
        help_text='Human-readable status message displayed to the user'
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text='Additional data: post_count, post_ids, error_details, etc.'
    )
    
    # Error handling
    is_error = models.BooleanField(
        default=False,
        help_text='Whether this status represents an error'
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text='Machine-readable error code (e.g., RATE_LIMIT, INVALID_URL)'
    )
    retryable = models.BooleanField(
        default=False,
        help_text='Whether the user can retry this operation'
    )
    actionable_message = models.TextField(
        blank=True,
        null=True,
        help_text='Actionable message telling the user what they can do'
    )
    
    # Progress tracking
    progress_percentage = models.IntegerField(
        default=0,
        help_text='Progress percentage (0-100)'
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text='Duration of this stage in seconds'
    )
    
    # Analytics
    api_calls_made = models.IntegerField(
        default=0,
        help_text='Number of API calls made during this stage'
    )
    cost_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text='Estimated cost in USD for this stage'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Analysis Status History'
        verbose_name_plural = 'Analysis Status Histories'
        indexes = [
            models.Index(fields=['analysis_request', 'created_at']),
            models.Index(fields=['stage', 'is_error']),
            models.Index(fields=['created_at']),
        ]
    
    def __str__(self) -> str:
        """String representation of the status history entry."""
        stage_display = self.get_stage_display()
        return f"{self.analysis_request.id} - {stage_display} - {self.created_at}"
    
    def clean(self):
        """Validate the status history entry."""
        from django.core.exceptions import ValidationError
        
        # Validate progress percentage
        if not 0 <= self.progress_percentage <= 100:
            raise ValidationError("Progress percentage must be between 0 and 100")
        
        # Validate error fields
        if self.is_error and not self.error_code:
            raise ValidationError("Error code is required when is_error is True")
        
        # Validate retryable
        if self.retryable and not self.is_error:
            raise ValidationError("retryable can only be True when is_error is True")
    
    def save(self, *args, **kwargs):
        """Override save to run validation."""
        self.full_clean()
        super().save(*args, **kwargs)


class ChatSession(models.Model):
    """
    Chat session for follow-up questions about a post analysis.
    Each analyzed post can have one chat session for conversational Q&A.
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', _('Active')
        ARCHIVED = 'archived', _('Archived')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='chat_sessions',
        help_text='User who owns this chat session'
    )
    post_analysis = models.OneToOneField(
        PostAnalysis,
        on_delete=models.CASCADE,
        related_name='chat_session',
        help_text='The post analysis this chat session belongs to'
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        help_text='Session status (active or archived)'
    )
    
    # Business metrics (for analytics and monitoring)
    messages_count = models.IntegerField(
        default=0,
        help_text='Total number of messages in this session (updated on message creation)'
    )
    total_tokens = models.IntegerField(
        null=True,
        blank=True,
        help_text='Total tokens used across all messages in this session'
    )
    duration_seconds = models.FloatField(
        null=True,
        blank=True,
        help_text='Time from first to last message in seconds (calculated on session close)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'status']),
            models.Index(fields=['post_analysis']),
            models.Index(fields=['updated_at']),
        ]
    
    def __str__(self):
        return f"Chat session for {self.post_analysis.post.username} - {self.user.email}"


class ChatMessage(models.Model):
    """
    Individual messages in a chat session.
    Stores both user messages and AI assistant responses.
    """
    class Role(models.TextChoices):
        USER = 'user', _('User')
        ASSISTANT = 'assistant', _('Assistant')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session = models.ForeignKey(
        ChatSession,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text='The chat session this message belongs to'
    )
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        help_text='Message role: user or assistant'
    )
    content = models.TextField(
        help_text='Message content'
    )
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text='Number of tokens used for this message (for analytics)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['session', 'created_at']),
        ]
    
    def __str__(self):
        role_display = self.get_role_display()
        content_preview = self.content[:50] + '...' if len(self.content) > 50 else self.content
        return f"{role_display}: {content_preview}"


class AnalysisNote(models.Model):
    """
    User notes for a specific post analysis.
    Allows users to save ideas, strategies, and insights from AI responses.
    One note per user per analysis (can be updated).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='analysis_notes',
        help_text='User who created this note'
    )
    post_analysis = models.ForeignKey(
        PostAnalysis,
        on_delete=models.CASCADE,
        related_name='notes',
        help_text='The post analysis this note belongs to'
    )
    title = models.CharField(
        max_length=200,
        help_text='Note title'
    )
    content = models.TextField(
        help_text='Note content (ideas, strategies, insights, etc.)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-updated_at']  # Newest first
        indexes = [
            models.Index(fields=['user', 'post_analysis']),
            models.Index(fields=['post_analysis', '-updated_at']),
        ]
        unique_together = [['user', 'post_analysis']]  # One note per user per analysis
    
    def __str__(self):
        return f"{self.title} - {self.post_analysis.post.username if self.post_analysis.post else 'Unknown'}"
