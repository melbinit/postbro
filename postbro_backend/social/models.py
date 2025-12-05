import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from accounts.models import User

class Platform(models.Model):
    class PlatformType(models.TextChoices):
        TWITTER = 'twitter', _('Twitter')
        INSTAGRAM = 'instagram', _('Instagram')
        YOUTUBE = 'youtube', _('YouTube')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=50, choices=PlatformType.choices, unique=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.get_name_display()

class Post(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    platform = models.ForeignKey(Platform, on_delete=models.PROTECT)
    platform_post_id = models.CharField(max_length=255)  # Original post ID from platform
    username = models.CharField(max_length=255)
    content = models.TextField()
    engagement_score = models.FloatField(default=0.0)
    metrics = models.JSONField(default=dict)  # Stores likes, shares, comments, etc.
    url = models.URLField(max_length=2048)
    posted_at = models.DateTimeField()
    collected_at = models.DateTimeField(auto_now_add=True)
    
    # Video transcript fields (YouTube, Instagram, Twitter/X)
    transcript = models.TextField(
        blank=True,
        null=True,
        help_text='Full transcript text (from YouTube API or Whisper AI for Instagram/Twitter videos)'
    )
    formatted_transcript = models.JSONField(
        default=list,
        blank=True,
        help_text='Timestamped transcript segments with start_time, end_time, duration, text (YouTube only)'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['platform', 'platform_post_id']
        indexes = [
            models.Index(fields=['engagement_score']),
            models.Index(fields=['username']),
            models.Index(fields=['platform']),
            models.Index(fields=['posted_at']),
        ]
        ordering = ['-posted_at']

    def __str__(self):
        return f"{self.username} - {self.platform} - {self.posted_at.date()}"

class PostMedia(models.Model):
    class MediaType(models.TextChoices):
        IMAGE = 'image', _('Image')
        VIDEO = 'video', _('Video')
        VIDEO_THUMBNAIL = 'video_thumbnail', _('Video Thumbnail')
        VIDEO_FRAME = 'video_frame', _('Video Frame')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='media')
    media_type = models.CharField(max_length=20, choices=MediaType.choices)
    file = models.FileField(upload_to='post_media/', blank=True, null=True)
    source_url = models.URLField(max_length=2048, help_text='Original API URL')
    supabase_url = models.URLField(
        max_length=2048,
        blank=True,
        null=True,
        help_text='Supabase Storage URL (if uploaded)'
    )
    uploaded_to_supabase = models.BooleanField(
        default=False,
        help_text='Whether this media has been uploaded to Supabase Storage'
    )
    transcript = models.TextField(
        blank=True,
        null=True,
        help_text='Audio transcript for video media (from Whisper AI or YouTube API)'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['uploaded_to_supabase']),
            models.Index(fields=['post', 'media_type']),
        ]

    def __str__(self):
        return f"{self.post} - {self.get_media_type_display()}"
    
    def get_display_url(self) -> str:
        """
        Get the best URL for display.
        Prefers Supabase URL if available, falls back to source URL.
        """
        return self.supabase_url or self.source_url

class PostComment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    comment_data = models.JSONField()  # Stores comment text, author, likes, etc.
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Comment on {self.post}"

class UserPostActivity(models.Model):
    class SourceType(models.TextChoices):
        HANDLE = 'handle', _('Handle')
        URL = 'url', _('URL')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='post_activities')
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='user_activities')
    # analysis_task = models.ForeignKey('analysis.AnalysisTask', on_delete=models.SET_NULL, null=True, blank=True, related_name='post_activities')
    source = models.CharField(max_length=10, choices=SourceType.choices)
    viewed_at = models.DateTimeField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['user', 'viewed_at']),
        ]
        ordering = ['-viewed_at']

    def __str__(self):
        return f"{self.user.email} viewed {self.post} via {self.source}"
