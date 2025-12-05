"""
Post Saver Service

This module provides utilities to normalize API responses from different
social media platforms and save them to the database models.
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional
from django.utils import timezone
from django.db import transaction

from social.models import Post, PostMedia, PostComment, Platform
from analysis.models import PostAnalysisRequest
from social.services.media_processor import MediaProcessor

logger = logging.getLogger(__name__)


class PostSaver:
    """
    Service class to normalize and save social media posts to the database.
    
    This class handles:
    - Normalizing API responses from different platforms
    - Saving posts, media, and comments to database
    - Calculating engagement scores
    - Handling duplicates and edge cases
    """
    
    def __init__(self, analysis_request: PostAnalysisRequest, media_bytes_cache: dict = None):
        """
        Initialize PostSaver with an analysis request.
        
        Args:
            analysis_request: The PostAnalysisRequest instance this post belongs to
            media_bytes_cache: Optional dict to store media bytes {post_id: {media_id: [bytes_dicts]}}
            
        Raises:
            ValueError: If platform is not found
        """
        self.analysis_request = analysis_request
        self.media_bytes_cache = media_bytes_cache if media_bytes_cache is not None else {}
        
        # Get platform object
        try:
            # Map analysis request platform to social Platform model
            platform_name_map = {
                'instagram': 'instagram',
                'x': 'twitter',  # Twitter model uses 'twitter', not 'x'
                'youtube': 'youtube',
            }
            platform_name = platform_name_map.get(analysis_request.platform)
            
            if not platform_name:
                raise ValueError(f"Unsupported platform: {analysis_request.platform}")
            
            self.platform_obj = Platform.objects.get(name=platform_name)
        except Platform.DoesNotExist:
            raise ValueError(f"Platform '{platform_name}' not found in database")
        
        # Initialize media processor
        self.media_processor = MediaProcessor()
    
    def _parse_datetime(self, date_string: Optional[str]) -> datetime:
        """
        Parse datetime string to timezone-aware datetime object.
        
        Args:
            date_string: ISO format datetime string or None
            
        Returns:
            Timezone-aware datetime object (UTC)
        """
        if not date_string:
            return timezone.now()
        
        try:
            # Handle ISO format: "2025-11-20T18:59:55.000Z"
            if date_string.endswith('Z'):
                date_string = date_string[:-1] + '+00:00'
            
            # Handle Twitter format: "Sun Nov 23 19:34:44 +0000 2025"
            if '+' in date_string and len(date_string.split()) > 5:
                try:
                    from dateutil import parser
                    return parser.parse(date_string).replace(tzinfo=timezone.utc)
                except ImportError:
                    # Fallback: try to parse manually
                    # Format: "Sun Nov 23 19:34:44 +0000 2025"
                    parts = date_string.split()
                    if len(parts) >= 6:
                        # Extract date parts and reconstruct ISO format
                        month_map = {
                            'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                            'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                            'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
                        }
                        month = month_map.get(parts[1], '01')
                        day = parts[2].zfill(2)
                        time_part = parts[3]
                        year = parts[5]
                        iso_string = f"{year}-{month}-{day}T{time_part}+00:00"
                        return datetime.fromisoformat(iso_string).replace(tzinfo=timezone.utc)
            
            # Standard ISO format
            dt = datetime.fromisoformat(date_string.replace('Z', '+00:00'))
            if dt.tzinfo is None:
                dt = timezone.make_aware(dt, timezone.utc)
            return dt
        
        except (ValueError, AttributeError) as e:
            logger.warning(f"Failed to parse datetime '{date_string}': {e}")
            return timezone.now()
    
    def _calculate_engagement_score(
        self,
        likes: int = 0,
        comments: int = 0,
        shares: int = 0,
        views: int = 0,
        retweets: int = 0
    ) -> float:
        """
        Calculate engagement score based on various metrics.
        
        Formula: (likes * 1) + (comments * 2) + (shares * 3) + (retweets * 2) / max(views, 1)
        This gives higher weight to interactions that require more effort.
        
        Args:
            likes: Number of likes
            comments: Number of comments
            shares: Number of shares
            views: Number of views
            retweets: Number of retweets
            
        Returns:
            Engagement score as float
        """
        if views == 0:
            views = 1  # Avoid division by zero
        
        engagement = (
            (likes * 1.0) +
            (comments * 2.0) +
            (shares * 3.0) +
            (retweets * 2.0)
        ) / views
        
        return round(engagement, 4)
    
    def extract_instagram_metrics(self, data: Dict) -> Dict:
        """
        Extract metrics from Instagram API response (BrightData format).
        Used for fast path when post already exists.
        
        Args:
            data: Instagram API response data
            
        Returns:
            Dictionary with metrics in same format as save_instagram_post
        """
        likes = int(data.get('likes', 0) or 0)
        comments_count = int(data.get('num_comments', 0) or 0)
        followers = int(data.get('followers', 0) or 0)
        posts_count = int(data.get('posts_count', 0) or 0)
        is_verified = data.get('is_verified', False)
        
        tagged_users = []
        if data.get('tagged_users'):
            for tagged_user in data['tagged_users']:
                tagged_users.append({
                    'username': tagged_user.get('username', ''),
                    'full_name': tagged_user.get('full_name', ''),
                    'is_verified': tagged_user.get('is_verified', False),
                    'id': tagged_user.get('id', ''),
                })
        
        return {
            'likes': likes,
            'comments': comments_count,
            'content_type': data.get('content_type', ''),
            'shortcode': data.get('shortcode', ''),
            'tagged_users': tagged_users,
            'tagged_users_count': len(tagged_users),
            'followers': followers,
            'posts_count': posts_count,
            'is_verified': is_verified,
        }
    
    def extract_youtube_metrics(self, data: Dict) -> Dict:
        """
        Extract metrics from YouTube API response (BrightData format).
        Used for fast path when post already exists.
        
        Args:
            data: YouTube API response data
            
        Returns:
            Dictionary with metrics in same format as save_youtube_video
        """
        views = int(data.get('views', 0) or 0)
        likes = int(data.get('likes', 0) or 0)
        comments_count = int(data.get('comments', 0) or 0)
        
        # Extract channel info
        followers = int(data.get('followers', 0) or 0)
        verified = data.get('verified', False)
        
        # Extract sponsored details if any
        is_sponsored = data.get('is_sponsored', False)
        sponsored_details = {}
        if is_sponsored:
            sponsored_details = {
                'sponsor_name': data.get('sponsor_name', ''),
                'sponsor_url': data.get('sponsor_url', ''),
            }
        
        return {
            'views': views,
            'likes': likes,
            'comments': comments_count,
            'video_id': data.get('video_id', ''),
            'youtuber': data.get('youtuber', ''),
            'youtuber_id': data.get('youtuber_id', ''),
            'channel_url': data.get('channel_url', ''),
            'handle_name': data.get('handle_name', ''),
            'verified': verified,
            'followers': followers,
            'post_type': data.get('post_type', 'post'),  # 'short' or 'post'
            'is_sponsored': is_sponsored,
            **sponsored_details,
        }
    
    def extract_twitter_metrics(self, data: Dict) -> Dict:
        """
        Extract metrics from Twitter API response (TwitterAPI.io format).
        Used for fast path when post already exists.
        
        Args:
            data: Twitter API response data
            
        Returns:
            Dictionary with metrics in same format as save_twitter_post
        """
        return {
            'likes': data.get('like_count', 0) or 0,
            'retweets': data.get('retweet_count', 0) or 0,
            'replies': data.get('reply_count', 0) or 0,
            'quotes': data.get('quote_count', 0) or 0,
            'views': data.get('view_count', 0) or 0,
            'bookmarks': data.get('bookmark_count', 0) or 0,
        }
    
    def update_existing_post_metrics(self, post: Post, fresh_data: Dict, platform: str) -> Post:
        """
        Fast path: Update only metrics for existing post.
        Skips all media processing (downloads, frame extraction, uploads, transcription).
        
        Args:
            post: Existing Post instance
            fresh_data: Fresh API response data
            platform: Platform name ('instagram', 'youtube', 'x', 'twitter')
            
        Returns:
            Updated Post instance
        """
        # Extract metrics from fresh API response
        if platform == 'instagram':
            metrics = self.extract_instagram_metrics(fresh_data)
            # Recalculate engagement score
            post.engagement_score = self._calculate_engagement_score(
                likes=metrics.get('likes', 0),
                comments=metrics.get('comments', 0),
                views=max(metrics.get('likes', 0) * 10, 1)  # Estimate views
            )
        elif platform == 'youtube':
            metrics = self.extract_youtube_metrics(fresh_data)
            # Recalculate engagement score
            post.engagement_score = self._calculate_engagement_score(
                likes=metrics.get('likes', 0),
                comments=metrics.get('comments', 0),
                views=metrics.get('views', 1)
            )
        elif platform in ('x', 'twitter'):
            metrics = self.extract_twitter_metrics(fresh_data)
            # Recalculate engagement score
            post.engagement_score = self._calculate_engagement_score(
                likes=metrics.get('likes', 0),
                comments=metrics.get('replies', 0),
                shares=metrics.get('retweets', 0),
                retweets=metrics.get('retweets', 0),
                views=metrics.get('views', 1)
            )
        else:
            logger.warning(f"Unknown platform {platform} for metrics update")
            return post
        
        # Update post metrics
        post.metrics = metrics
        post.save()
        logger.info(f"✅ [FastPath] Updated metrics for existing post {post.id} ({platform})")
        
        return post
    
    def reuse_existing_media(self, post: Post) -> Dict:
        """
        Reuse existing media from Supabase for existing posts.
        Fetches bytes from Supabase URLs and validates with PIL (following current practices).
        
        Returns: media_bytes_by_post_id structure compatible with Gemini analysis.
        Structure: {post_id: {media_id: [{'bytes': bytes, 'mime_type': str, 'media_type': str}]}}
        """
        import requests
        from PIL import Image
        from io import BytesIO
        
        if post.id not in self.media_bytes_cache:
            self.media_bytes_cache[post.id] = {}
        
        def get_mime_type_from_url(url: str) -> str:
            """Infer MIME type from URL extension"""
            url_lower = url.lower()
            if url_lower.endswith('.jpg') or url_lower.endswith('.jpeg'):
                return 'image/jpeg'
            elif url_lower.endswith('.png'):
                return 'image/png'
            elif url_lower.endswith('.gif'):
                return 'image/gif'
            elif url_lower.endswith('.webp'):
                return 'image/webp'
            else:
                return 'image/jpeg'  # Default
        
        # Fetch existing media from DB
        for media in post.media.all():
            if not media.supabase_url:
                logger.warning(f"⚠️ [FastPath] Media {media.id} has no Supabase URL, skipping")
                continue
            
            try:
                # Fetch bytes from Supabase URL (public URLs are accessible)
                logger.info(f"📥 [FastPath] Fetching {media.media_type} from Supabase: {media.supabase_url[:80]}...")
                response = requests.get(media.supabase_url, timeout=30)
                response.raise_for_status()
                media_bytes = response.content
                
                # PIL validation (following current practices from media_processor.py)
                try:
                    pil_image = Image.open(BytesIO(media_bytes))
                    pil_image.verify()  # Verify it's a valid image
                    pil_image = Image.open(BytesIO(media_bytes))  # Reopen after verify (verify() closes it)
                    
                    logger.debug(
                        f"✅ [FastPath] PIL validated {media.media_type} as {pil_image.format} "
                        f"({pil_image.size[0]}x{pil_image.size[1]}, {len(media_bytes)} bytes)"
                    )
                except Exception as pil_error:
                    logger.error(f"❌ [FastPath] PIL validation failed for {media.media_type}: {pil_error}")
                    logger.error(f"   Bytes length: {len(media_bytes)}, URL: {media.supabase_url[:100]}")
                    logger.error(f"   First 50 bytes (hex): {media_bytes[:50].hex()}")
                    # Skip invalid images
                    continue
                
                # Detect MIME type
                mime_type = get_mime_type_from_url(media.supabase_url)
                
                # Store in cache (same format as new processing)
                if media.id not in self.media_bytes_cache[post.id]:
                    self.media_bytes_cache[post.id][media.id] = []
                
                self.media_bytes_cache[post.id][media.id].append({
                    'bytes': media_bytes,
                    'mime_type': mime_type,
                    'media_type': media.media_type
                })
                
                logger.info(
                    f"✅ [FastPath] Reused {media.media_type} from Supabase: "
                    f"{len(media_bytes)} bytes (mime: {mime_type})"
                )
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"⚠️ [FastPath] Failed to fetch {media.media_type} from Supabase {media.supabase_url[:80]}: {e}")
                # Could fallback to re-processing this media item if needed
                continue
            except Exception as e:
                logger.error(f"❌ [FastPath] Unexpected error fetching {media.media_type}: {e}", exc_info=True)
                continue
        
        return self.media_bytes_cache
    
    def save_instagram_post(self, data: Dict) -> Post:
        """
        Save Instagram post from BrightData API response.
        
        Args:
            data: Instagram post data from BrightData API
            
        Returns:
            Post instance (created or existing)
            
        Raises:
            ValueError: If required data is missing
        """
        if not data.get('success', True):
            error_msg = data.get('error', 'Unknown error')
            logger.error(f"BrightData returned error for Instagram post: {error_msg}")
            logger.error(f"Full BrightData response: {data}")
            raise ValueError(f"Failed to scrape Instagram post: {error_msg}")
        
        # Extract post ID (prefer post_id, fallback to shortcode)
        post_id = data.get('post_id') or data.get('shortcode') or data.get('pk')
        if not post_id:
            # Log the full response to debug
            logger.error("Missing post_id, shortcode, or pk in Instagram data")
            logger.error(f"Available keys in response: {list(data.keys())}")
            logger.error(f"Full BrightData response: {data}")
            logger.error(f"Response type: {type(data)}")
            logger.error(f"Response length: {len(str(data))} characters")
            raise ValueError("Missing post_id, shortcode, or pk in Instagram data")
        
        post_id = str(post_id)
        
        # Extract basic information
        username = data.get('user_posted', '').strip()
        content = data.get('description', '').strip()
        url = data.get('url', '')
        posted_at = self._parse_datetime(data.get('date_posted'))
        
        # Extract metrics
        likes = int(data.get('likes', 0) or 0)
        comments_count = int(data.get('num_comments', 0) or 0)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(
            likes=likes,
            comments=comments_count,
            views=max(likes * 10, 1)  # Estimate views (Instagram doesn't provide)
        )
        
        # Prepare metrics JSON
        # Extract tagged users - save usernames and key details (for celebrity/influencer detection)
        tagged_users = []
        if data.get('tagged_users'):
            for tagged_user in data['tagged_users']:
                tagged_users.append({
                    'username': tagged_user.get('username', ''),
                    'full_name': tagged_user.get('full_name', ''),
                    'is_verified': tagged_user.get('is_verified', False),
                    'id': tagged_user.get('id', ''),
                })
        
        # Extract user info for better insights
        followers = int(data.get('followers', 0) or 0)
        posts_count = int(data.get('posts_count', 0) or 0)
        is_verified = data.get('is_verified', False)
        
        metrics = {
            'likes': likes,
            'comments': comments_count,
            'content_type': data.get('content_type', ''),
            'shortcode': data.get('shortcode', ''),
            'tagged_users': tagged_users,  # Full list with usernames
            'tagged_users_count': len(tagged_users),
            'followers': followers,  # Important for influencer/celebrity detection
            'posts_count': posts_count,  # Total posts by user
            'is_verified': is_verified,  # Verification status
        }
        
        # Get or create post
        post, created = Post.objects.get_or_create(
            platform=self.platform_obj,
            platform_post_id=post_id,
            defaults={
                'username': username,
                'content': content,
                'url': url,
                'posted_at': posted_at,
                'engagement_score': engagement_score,
                'metrics': metrics,
            }
        )
        
        # Update if post already existed (refresh data)
        if not created:
            post.username = username
            post.content = content
            post.url = url
            post.posted_at = posted_at
            post.engagement_score = engagement_score
            post.metrics = metrics
            post.save()
        
        logger.info(
            f"{'Created' if created else 'Updated'} Instagram post: {post_id} by @{username} "
            f"for analysis_request_id={self.analysis_request.id}"
        )
        
        # Initialize base64 cache on post object (in-memory, not in DB)
        if not hasattr(post, '_media_base64_cache'):
            post._media_base64_cache = []
        
        # Initialize bytes cache on post object (in-memory, for Gemini analysis)
        # Key: media.id, Value: list of {'bytes': bytes, 'mime_type': str, 'media_type': str}
        if not hasattr(post, '_media_bytes_cache'):
            post._media_bytes_cache = {}
        
        # Save and process media from post_content array (primary source - most reliable)
        # post_content contains all media items with type information (Photo/Video)
        if data.get('post_content'):
            for i, content_item in enumerate(data['post_content']):
                if not content_item:
                    continue
                
                content_type = content_item.get('type', '').strip()
                media_url = content_item.get('url', '').strip()
                
                if not media_url:
                    logger.warning(f"Instagram post_content item {i} missing URL, skipping")
                    continue
                
                content_type_lower = content_type.lower()
                
                if content_type_lower == 'photo':
                    # Process photo: download, upload to Supabase, convert to base64
                    media, created = PostMedia.objects.get_or_create(
                        post=post,
                        source_url=media_url,
                        defaults={
                            'media_type': 'image',
                            'source_url': media_url,
                            'uploaded_to_supabase': False,
                        }
                    )
                    
                    # Process media (immediate upload for Instagram images - CORS blocking on CDN URLs)
                    # Only process if newly created or if supabase_url is missing
                    if created or not media.supabase_url:
                        self._process_media(media, platform='instagram', media_type='image', media_index=i)
                        # Refresh media object to get updated supabase_url
                        media.refresh_from_db()
                        # Verify upload completed
                        if not media.supabase_url:
                            logger.warning(f"Media upload may not have completed for {media_url[:50]}...")
                        # Get base64 from media object cache and add to post cache
                        if hasattr(media, '_base64_cache') and media._base64_cache:
                            post._media_base64_cache.extend(media._base64_cache)
                
                elif content_type_lower == 'video':
                    # Process video: extract frames, upload to Supabase, and transcribe audio
                    try:
                        logger.info(f"Processing Instagram video frames from: {media_url[:100]}...")
                        frame_urls, frame_bytes_list = self.media_processor.process_video_frames(
                            video_url=media_url,
                            post_id=str(post.id),
                            num_frames=5
                        )
                        
                        # Save each frame as PostMedia with video_frame type + store bytes
                        for j, (frame_url, frame_bytes) in enumerate(zip(frame_urls, frame_bytes_list)):
                            frame_media = PostMedia.objects.create(
                                post=post,
                                media_type='video_frame',
                                source_url=media_url,  # Store original video URL
                                supabase_url=frame_url,
                                uploaded_to_supabase=True,
                            )
                            # Store raw bytes in separate cache dict (survives refresh_from_db())
                            if post.id not in self.media_bytes_cache:
                                self.media_bytes_cache[post.id] = {}
                            if frame_media.id not in self.media_bytes_cache[post.id]:
                                self.media_bytes_cache[post.id][frame_media.id] = []
                            self.media_bytes_cache[post.id][frame_media.id].append({
                                'bytes': frame_bytes,
                                'mime_type': 'image/jpeg',
                                'media_type': 'video_frame'
                            })
                            logger.debug(f"Stored frame {j+1} bytes in cache ({len(frame_bytes)} bytes)")
                        logger.info(f"Successfully processed {len(frame_urls)} frames for Instagram video (item {i})")
                        
                        # Create or get PostMedia entry for the video itself (to store transcript)
                        video_media, video_created = PostMedia.objects.get_or_create(
                            post=post,
                            media_type='video',
                            source_url=media_url,
                            defaults={
                                'source_url': media_url,
                                'uploaded_to_supabase': False,
                            }
                        )
                        
                        # Extract and transcribe audio (first 3 minutes)
                        try:
                            logger.info("Extracting and transcribing audio from Instagram video...")
                            transcript = self.media_processor.extract_and_transcribe_video(
                                video_url=media_url,
                                max_duration=180  # 3 minutes
                            )
                            if transcript:
                                # Save transcript to PostMedia (media-specific)
                                video_media.transcript = transcript
                                video_media.save(update_fields=['transcript'])
                                logger.info(
                                    f"✅ Saved transcript ({len(transcript)} chars) to PostMedia for Instagram video "
                                    f"(analysis_request_id={self.analysis_request.id}, post_id={post.id})"
                                )
                            else:
                                logger.warning(
                                    f"Could not transcribe Instagram video audio "
                                    f"(analysis_request_id={self.analysis_request.id}, post_id={post.id})"
                                )
                        except Exception as e:
                            logger.warning(
                                f"Failed to transcribe Instagram video audio for analysis_request_id={self.analysis_request.id}, "
                                f"post_id={post.id}: {e}"
                            )
                            # Don't fail the entire video processing if transcription fails
                        
                    except Exception as e:
                        logger.error(
                            f"Failed to process Instagram video frames from {media_url[:100]} "
                            f"for analysis_request_id={self.analysis_request.id}, post_id={post.id}: {e}",
                            exc_info=True,
                        )
                        # Fallback: save video URL without frames (for manual processing later)
                        PostMedia.objects.get_or_create(
                            post=post,
                            source_url=media_url,
                            defaults={
                                'media_type': 'video',
                                'source_url': media_url,
                                'uploaded_to_supabase': False,
                            }
                        )
                else:
                    logger.warning(f"Unknown Instagram content type '{content_type}' for item {i}, skipping")
        
        # Fallback: Process photos array if post_content is not available (backward compatibility)
        elif data.get('photos'):
            logger.info("post_content not available, falling back to photos array")
            for i, photo_url in enumerate(data['photos']):
                if photo_url:
                    media, created = PostMedia.objects.get_or_create(
                        post=post,
                        source_url=photo_url,
                        defaults={
                            'media_type': 'image',
                            'source_url': photo_url,
                            'uploaded_to_supabase': False,
                        }
                    )
                    
                    # Process media (immediate upload for Instagram images - CORS blocking on CDN URLs)
                    # Only process if newly created or if supabase_url is missing
                    if created or not media.supabase_url:
                        self._process_media(media, platform='instagram', media_type='image', media_index=i)
                        # Refresh media object to get updated supabase_url
                        media.refresh_from_db()
                        # Verify upload completed
                        if not media.supabase_url:
                            logger.warning(f"Media upload may not have completed for {photo_url[:50]}...")
                        # Get base64 from media object cache and add to post cache
                        if hasattr(media, '_base64_cache') and media._base64_cache:
                            post._media_base64_cache.extend(media._base64_cache)
        
        # Process videos array if post_content didn't have videos (fallback for Reels)
        # This handles cases where videos array exists but post_content might be incomplete
        if data.get('videos') and not any(
            item.get('type', '').lower() == 'video' 
            for item in data.get('post_content', [])
        ):
            logger.info("Processing videos array as fallback (Reel or incomplete post_content)")
            for i, video_url in enumerate(data['videos']):
                if not video_url:
                    continue
                
                try:
                    logger.info(f"Processing Instagram video frames from videos array: {video_url[:100]}...")
                    frame_urls, frame_bytes_list = self.media_processor.process_video_frames(
                        video_url=video_url,
                        post_id=str(post.id),
                        num_frames=5
                    )
                    
                    # Save each frame as PostMedia with video_frame type + store bytes
                    for j, (frame_url, frame_bytes) in enumerate(zip(frame_urls, frame_bytes_list)):
                        frame_media = PostMedia.objects.create(
                            post=post,
                            media_type='video_frame',
                            source_url=video_url,
                            supabase_url=frame_url,
                            uploaded_to_supabase=True,
                        )
                        # Store raw bytes on Post object for Gemini (persists across DB queries)
                        if not hasattr(post, '_media_bytes_cache'):
                            post._media_bytes_cache = {}
                        if frame_media.id not in post._media_bytes_cache:
                            post._media_bytes_cache[frame_media.id] = []
                        post._media_bytes_cache[frame_media.id].append({
                            'bytes': frame_bytes,
                            'mime_type': 'image/jpeg',
                            'media_type': 'video_frame'
                        })
                    logger.info(f"Successfully processed {len(frame_urls)} frames for Instagram video from videos array")
                    
                except Exception as e:
                    logger.error(
                        f"Failed to process Instagram video frames from videos array for "
                        f"analysis_request_id={self.analysis_request.id}, post_id={post.id}: {e}",
                        exc_info=True,
                    )
                    # Fallback: save video URL without frames
                    PostMedia.objects.get_or_create(
                        post=post,
                        source_url=video_url,
                        defaults={
                            'media_type': 'video',
                            'source_url': video_url,
                            'uploaded_to_supabase': False,
                        }
                    )
        
        # Save and process thumbnail (optional - for display purposes)
        if data.get('thumbnail'):
            media, created = PostMedia.objects.get_or_create(
                post=post,
                source_url=data['thumbnail'],
                defaults={
                    'media_type': 'image',
                    'source_url': data['thumbnail'],
                    'uploaded_to_supabase': False,
                }
            )
            if created or not media.supabase_url:
                self._process_media(media, platform='instagram', media_type='image', media_index=0)
                media.refresh_from_db()
        
        # Refresh post to ensure all media is loaded
        post.refresh_from_db()
        
        # Save comments
        if data.get('latest_comments'):
            for comment_data in data['latest_comments']:
                if comment_data and comment_data.get('comments'):
                    PostComment.objects.get_or_create(
                        post=post,
                        comment_data=comment_data,
                        defaults={
                            'comment_data': comment_data,
                        }
                    )
        
        return post
    
    @transaction.atomic
    def save_youtube_video(self, data: Dict) -> Post:
        """
        Save YouTube video from BrightData API response.
        
        Args:
            data: YouTube video data from BrightData API
            
        Returns:
            Post instance (created or existing)
            
        Raises:
            ValueError: If required data is missing
        """
        if not data.get('success', True):
            raise ValueError(f"Failed to scrape YouTube video: {data.get('error', 'Unknown error')}")
        
        # Extract video ID
        video_id = data.get('video_id') or data.get('shortcode')
        if not video_id:
            raise ValueError("Missing video_id or shortcode in YouTube data")
        
        video_id = str(video_id)
        
        # Extract basic information
        youtuber = (data.get('youtuber') or '').replace('@', '').strip()
        title = (data.get('title') or '').strip()
        description = (data.get('description') or '').strip()
        
        # Post.content: combine title + description for regular videos, title only for Shorts
        # For Shorts: use title only. For regular videos: combine title + description
        if description:
            # Regular video: combine title and description
            content = f"{title}\n\n{description}".strip() if title else description
        else:
            # Shorts: use title only
            content = title
        
        url = data.get('url', '')
        posted_at = self._parse_datetime(data.get('date_posted'))
        
        # Extract transcript - handle both null (Shorts) and string (regular videos)
        transcript_raw = data.get('transcript')
        if transcript_raw is None:
            transcript = ''
        elif isinstance(transcript_raw, str):
            transcript = transcript_raw.strip()
        else:
            transcript = str(transcript_raw).strip()
        
        # Extract formatted_transcript - handle both null (Shorts) and array (regular videos)
        formatted_transcript_raw = data.get('formatted_transcript')
        if formatted_transcript_raw is None:
            formatted_transcript = []
        elif isinstance(formatted_transcript_raw, list):
            formatted_transcript = formatted_transcript_raw
        else:
            formatted_transcript = []
        
        # Extract metrics
        likes = int(data.get('likes', 0) or 0)
        views = int(data.get('views', 0) or 0)
        comments_count = int(data.get('num_comments', 0) or 0)
        subscribers = int(data.get('subscribers', 0) or 0)
        video_length = int(data.get('video_length', 0) or 0)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(
            likes=likes,
            comments=comments_count,
            views=views
        )
        
        # Prepare metrics JSON
        # Extract sponsored content details if available
        is_sponsored = data.get('is_sponsored', False)
        sponsored_details = {}
        if is_sponsored:
            # Save any sponsored content details if available in the API response
            # This helps Gemini understand sponsorship context
            sponsored_details = {
                'is_sponsored': True,
                # Add any other sponsored-related fields from API if available
            }
        
        # Post.metrics should only contain engagement metrics (like Instagram/Twitter)
        # Media-specific data (title, description, video_length, preview_image) goes to PostMedia
        metrics = {
            'likes': likes,
            'views': views,
            'comments': comments_count,
            'subscribers': subscribers,
            'youtuber_id': data.get('youtuber_id', ''),
            'channel_url': data.get('channel_url', ''),
            'handle_name': data.get('handle_name', ''),
            'verified': data.get('verified', False),
            'post_type': data.get('post_type', 'post'),  # 'short' or 'post'
            'is_sponsored': is_sponsored,
            **sponsored_details,  # Merge sponsored details if any
        }
        
        # Get or create post
        post, created = Post.objects.get_or_create(
            platform=self.platform_obj,
            platform_post_id=video_id,
            defaults={
                'username': youtuber,
                'content': content,
                'url': url,
                'posted_at': posted_at,
                'engagement_score': engagement_score,
                'metrics': metrics,
                'transcript': transcript,
                'formatted_transcript': formatted_transcript,
            }
        )
        
        # Update if post already existed
        if not created:
            post.username = youtuber
            post.content = content
            post.url = url
            post.posted_at = posted_at
            post.engagement_score = engagement_score
            post.metrics = metrics
            post.transcript = transcript
            post.formatted_transcript = formatted_transcript
            post.save()
        
        logger.info(
            f"{'Created' if created else 'Updated'} YouTube video: {video_id} by {youtuber} "
            f"for analysis_request_id={self.analysis_request.id}"
        )
        
        # Create PostMedia entry for the video itself (unified with Instagram/Twitter structure)
        # Just like Instagram/Twitter: only source_url, transcript, supabase_url
        video_media, video_media_created = PostMedia.objects.get_or_create(
            post=post,
            media_type='video',
            source_url=url,  # Video URL (like Instagram/Twitter)
            defaults={
                'source_url': url,
                'uploaded_to_supabase': False,
                'transcript': transcript,  # Transcript (like Instagram/Twitter videos)
            }
        )
        
        # Update if video media already existed
        if not video_media_created:
            video_media.transcript = transcript
            video_media.save(update_fields=['transcript'])
        
        logger.info(f"✅ Saved video PostMedia for YouTube video {video_id}")
        
        # If transcript is empty or missing, try Whisper transcription as fallback
        if not transcript or len(transcript.strip()) == 0:
            try:
                logger.info(f"📝 YouTube transcript is empty, attempting Whisper transcription for video {video_id}...")
                whisper_transcript = self.media_processor.extract_and_transcribe_youtube(
                    video_id=video_id,
                    max_duration=180  # 3 minutes
                )
                if whisper_transcript and len(whisper_transcript.strip()) > 0:
                    # Save Whisper transcript to PostMedia (media-specific)
                    video_media.transcript = whisper_transcript.strip()
                    video_media.save(update_fields=['transcript'])
                    logger.info(f"✅ Saved Whisper transcript ({len(whisper_transcript)} chars) to PostMedia for YouTube video {video_id}")
                else:
                    logger.warning(f"Whisper transcription returned empty result for YouTube video {video_id}")
            except Exception as e:
                logger.warning(f"Failed to transcribe YouTube video {video_id} with Whisper: {e}")
                # Don't fail the entire save process if transcription fails
        
        # Initialize base64 cache on post object (in-memory, not in DB)
        if not hasattr(post, '_media_base64_cache'):
            post._media_base64_cache = []
        
        # Initialize bytes cache on post object (in-memory, for Gemini analysis)
        # Key: media.id, Value: list of {'bytes': bytes, 'mime_type': str, 'media_type': str}
        if not hasattr(post, '_media_bytes_cache'):
            post._media_bytes_cache = {}
        
        # NOTE: Frame extraction is now done AFTER social_data_fetched status is created
        # This allows the frontend to update the sidebar with username immediately
        # Frame extraction will happen in a separate step (see tasks.py after status creation)
        
        # Save and process thumbnail (media-specific, goes to PostMedia)
        if data.get('preview_image'):
            thumbnail_media, created_thumbnail = PostMedia.objects.get_or_create(
                post=post,
                media_type='video_thumbnail',
                source_url=data['preview_image'],
                defaults={
                    'source_url': data['preview_image'],
                    'uploaded_to_supabase': False,
                }
            )
            if created_thumbnail or not thumbnail_media.supabase_url:
                self._process_media(thumbnail_media, platform='youtube', media_type='image', media_index=0)
                # Refresh media object to get updated supabase_url
                thumbnail_media.refresh_from_db()
                # Get base64 from media object cache and add to post cache
                if hasattr(thumbnail_media, '_base64_cache') and thumbnail_media._base64_cache:
                    post._media_base64_cache.extend(thumbnail_media._base64_cache)
        
        return post
    
    @transaction.atomic
    def save_twitter_tweet(self, data: Dict) -> Post:
        """
        Save Twitter/X tweet from TwitterAPI.io response.
        
        Args:
            data: Tweet data from TwitterAPI.io
            
        Returns:
            Post instance (created or existing)
            
        Raises:
            ValueError: If required data is missing
        """
        if not data.get('success', True):
            raise ValueError(f"Failed to scrape Twitter/X tweet: {data.get('error', 'Unknown error')}")
        
        # Extract tweet ID
        tweet_id = data.get('id') or data.get('tweet_id')
        if not tweet_id:
            raise ValueError("Missing id or tweet_id in Twitter/X data")
        
        tweet_id = str(tweet_id)
        
        # Extract author info
        author = data.get('author', {})
        username = author.get('userName', '').strip()
        if not username:
            raise ValueError("Missing author.userName in Twitter/X data")
        
        # Extract basic information
        content = data.get('text', '').strip()
        url = data.get('url', '') or data.get('twitterUrl', '')
        posted_at = self._parse_datetime(data.get('createdAt'))
        
        # Extract metrics
        likes = int(data.get('likeCount', 0) or 0)
        retweets = int(data.get('retweetCount', 0) or 0)
        replies = int(data.get('replyCount', 0) or 0)
        quotes = int(data.get('quoteCount', 0) or 0)
        views = int(data.get('viewCount', 0) or 0)
        bookmarks = int(data.get('bookmarkCount', 0) or 0)
        
        # Calculate engagement score
        engagement_score = self._calculate_engagement_score(
            likes=likes,
            comments=replies,
            shares=quotes,
            views=views,
            retweets=retweets
        )
        
        # Prepare metrics JSON
        # Extract full author details for better insights (bio, location, stats, etc.)
        metrics = {
            'likes': likes,
            'retweets': retweets,
            'replies': replies,
            'quotes': quotes,
            'views': views,
            'bookmarks': bookmarks,
            'author': {
                'id': author.get('id', ''),
                'userName': author.get('userName', ''),
                'name': author.get('name', ''),
                'isVerified': author.get('isVerified', False),
                'isBlueVerified': author.get('isBlueVerified', False),
                'followers': author.get('followers', 0),
                'following': author.get('following', 0),
                'profilePicture': author.get('profilePicture', ''),
                'description': author.get('description', ''),  # Bio
                'location': author.get('location', ''),
                'createdAt': author.get('createdAt', ''),  # Account creation date
                'mediaCount': author.get('mediaCount', 0),  # Total posts
                'statusesCount': author.get('statusesCount', 0),  # Total tweets
                'coverPicture': author.get('coverPicture', ''),
                'url': author.get('url', ''),
                'twitterUrl': author.get('twitterUrl', ''),
            },
            'isReply': data.get('isReply', False),
            'isRetweet': data.get('isRetweet', False),
            'isQuote': data.get('isQuote', False),
        }
        
        # Get or create post
        post, created = Post.objects.get_or_create(
            platform=self.platform_obj,
            platform_post_id=tweet_id,
            defaults={
                'username': username,
                'content': content,
                'url': url,
                'posted_at': posted_at,
                'engagement_score': engagement_score,
                'metrics': metrics,
            }
        )
        
        # Update if post already existed
        if not created:
            post.username = username
            post.content = content
            post.url = url
            post.posted_at = posted_at
            post.engagement_score = engagement_score
            post.metrics = metrics
            post.save()
        
        logger.info(
            f"{'Created' if created else 'Updated'} Twitter/X tweet: {tweet_id} by @{username} "
            f"for analysis_request_id={self.analysis_request.id}"
        )
        
        # Initialize base64 cache on post object (in-memory, not in DB)
        # Note: Twitter uses lazy upload, so base64 won't be available here
        # It will be downloaded on-demand in openai_service.py if needed
        if not hasattr(post, '_media_base64_cache'):
            post._media_base64_cache = []
        
        # Save and process media
        if data.get('extendedEntities', {}).get('media'):
            for i, media_item in enumerate(data['extendedEntities']['media']):
                # Determine media type
                media_type_str = media_item.get('type', '').lower()
                
                if media_type_str == 'video':
                    # For videos, extract actual video URL from video_info.variants
                    video_info = media_item.get('video_info', {})
                    variants = video_info.get('variants', [])
                    
                    # Find the best quality MP4 video URL (highest bitrate)
                    video_url = None
                    max_bitrate = 0
                    for variant in variants:
                        content_type = variant.get('content_type', '')
                        if content_type == 'video/mp4':
                            bitrate = variant.get('bitrate', 0)
                            if bitrate > max_bitrate:
                                max_bitrate = bitrate
                                video_url = variant.get('url', '')
                    
                    # Fallback to first MP4 variant if no bitrate info
                    if not video_url:
                        for variant in variants:
                            if variant.get('content_type') == 'video/mp4':
                                video_url = variant.get('url', '')
                                break
                    
                    # Fallback to thumbnail if no video URL found
                    if not video_url:
                        video_url = media_item.get('media_url_https', '')
                        logger.warning(f"No video URL found in variants, using thumbnail: {video_url}")
                    
                    if not video_url:
                        logger.error(f"No video URL available for video media item {i}")
                        continue
                    
                    # Process video: extract frames immediately and transcribe audio
                    try:
                        logger.info(f"Processing Twitter video frames from: {video_url[:100]}...")
                        frame_urls, frame_bytes_list = self.media_processor.process_video_frames(
                            video_url=video_url,
                            post_id=str(post.id),
                            num_frames=5
                        )
                        
                        # Save frame URLs + store bytes
                        for j, (frame_url, frame_bytes) in enumerate(zip(frame_urls, frame_bytes_list)):
                            frame_media = PostMedia.objects.create(
                                post=post,
                                media_type='video_frame',
                                source_url=video_url,  # Store actual video URL, not thumbnail
                                supabase_url=frame_url,
                                uploaded_to_supabase=True,
                            )
                            # Store raw bytes in memory for Gemini
                            if not hasattr(frame_media, '_bytes_cache'):
                                frame_media._bytes_cache = []
                            frame_media._bytes_cache.append({
                                'bytes': frame_bytes,
                                'mime_type': 'image/jpeg',
                                'media_type': 'video_frame'
                            })
                        logger.info(f"Successfully processed {len(frame_urls)} frames for Twitter video")
                        
                        # Create or get PostMedia entry for the video itself (to store transcript)
                        video_media, video_created = PostMedia.objects.get_or_create(
                            post=post,
                            media_type='video',
                            source_url=video_url,
                            defaults={
                                'source_url': video_url,
                                'uploaded_to_supabase': False,
                            }
                        )
                        
                        # Extract and transcribe audio (first 3 minutes)
                        try:
                            logger.info(f"Extracting and transcribing audio from Twitter video...")
                            transcript = self.media_processor.extract_and_transcribe_video(
                                video_url=video_url,
                                max_duration=180  # 3 minutes
                            )
                            if transcript:
                                # Save transcript to PostMedia (media-specific)
                                video_media.transcript = transcript
                                video_media.save(update_fields=['transcript'])
                                logger.info(f"✅ Saved transcript ({len(transcript)} chars) to PostMedia for Twitter video")
                            else:
                                logger.warning(f"Could not transcribe Twitter video audio")
                        except Exception as e:
                            logger.warning(
                                f"Failed to transcribe Twitter video audio for analysis_request_id={self.analysis_request.id}, "
                                f"post_id={post.id}: {e}"
                            )
                            # Don't fail the entire video processing if transcription fails
                            
                    except Exception as e:
                        logger.error(
                            f"Failed to process Twitter video frames from {video_url[:100]} "
                            f"for analysis_request_id={self.analysis_request.id}, post_id={post.id}: {e}",
                            exc_info=True,
                        )
                        # Save original video URL as fallback
                        PostMedia.objects.create(
                            post=post,
                            media_type='video',
                            source_url=video_url,
                            uploaded_to_supabase=False,
                        )
                else:
                    # Image: use media_url_https
                    media_url = media_item.get('media_url_https', '')
                    if not media_url:
                        continue
                    
                    # Image: download and upload (same as Instagram/YouTube)
                    media, created_media = PostMedia.objects.get_or_create(
                        post=post,
                        source_url=media_url,
                        defaults={
                            'media_type': 'image',
                            'source_url': media_url,
                            'uploaded_to_supabase': False,
                        }
                    )
                    # Process media (download, upload, convert to base64)
                    if created_media or not media.supabase_url:
                        self._process_media(media, platform='x', media_type='image', media_index=i)
                        # Refresh media object to get updated supabase_url
                        media.refresh_from_db()
                        # Get base64 from media object cache and add to post cache
                        if hasattr(media, '_base64_cache') and media._base64_cache:
                            post._media_base64_cache.extend(media._base64_cache)
        
        return post
    
    def save_posts_batch(self, posts_data: List[Dict], platform: str) -> List[Post]:
        """
        Save multiple posts in a batch.
        
        Args:
            posts_data: List of post data dictionaries
            platform: Platform name ('instagram', 'youtube', 'x')
            
        Returns:
            List of Post instances (created or existing)
        """
        saved_posts = []
        failed_posts = []
        
        for post_data in posts_data:
            try:
                if platform == 'instagram':
                    post = self.save_instagram_post(post_data)
                elif platform == 'youtube':
                    post = self.save_youtube_video(post_data)
                elif platform == 'x':
                    post = self.save_twitter_tweet(post_data)
                else:
                    logger.error(f"Unsupported platform: {platform}")
                    continue
                
                saved_posts.append(post)
            
            except Exception as e:
                logger.error(f"Failed to save post: {str(e)}")
                failed_posts.append({
                    'url': post_data.get('url', 'unknown'),
                    'error': str(e)
                })
        
        if failed_posts:
            logger.warning(f"Failed to save {len(failed_posts)} posts: {failed_posts}")
        
        return saved_posts
    
    def _process_media(
        self,
        media: PostMedia,
        platform: str,
        media_type: str,
        media_index: int = 0
    ) -> None:
        """
        Process media based on platform and type.
        
        Implements smart upload strategy:
        - Video frames: Always upload immediately
        - Instagram images: Lazy upload (URLs stay active for hours)
        - YouTube thumbnails: Upload immediately (URLs expire)
        - Twitter images: Lazy upload (URLs don't expire)
        
        Args:
            media: PostMedia instance to process
            platform: Platform name ('instagram', 'youtube', 'twitter')
            media_type: Media type ('image', 'video', 'video_frame')
            media_index: Index of media item (for filename)
        """
        try:
            should_upload = self.media_processor.should_upload_immediately(
                platform=platform,
                media_type=media_type,
                source_url=media.source_url
            )
            
            if should_upload:
                # Upload immediately and get base64 data + raw bytes (download once, use multiple times!)
                supabase_url, base64_data, base64_mime_type, raw_bytes = self.media_processor.process_image(
                    image_url=media.source_url,
                    post_id=str(media.post.id),
                    media_index=media_index
                )
                
                if supabase_url:
                    media.supabase_url = supabase_url
                    media.uploaded_to_supabase = True
                    # Store base64 data on media object (in-memory, for passing to AI function)
                    if base64_data and base64_mime_type:
                        if not hasattr(media, '_base64_cache'):
                            media._base64_cache = []
                        media._base64_cache.append({
                            'base64': base64_data,
                            'mime_type': base64_mime_type
                        })
                    # Store raw bytes in separate cache dict (survives refresh_from_db())
                    if raw_bytes and base64_mime_type:
                        post_id = media.post.id
                        if post_id not in self.media_bytes_cache:
                            self.media_bytes_cache[post_id] = {}
                        if media.id not in self.media_bytes_cache[post_id]:
                            self.media_bytes_cache[post_id][media.id] = []
                        self.media_bytes_cache[post_id][media.id].append({
                            'bytes': raw_bytes,
                            'mime_type': base64_mime_type,
                            'media_type': media.media_type  # Track if it's 'image' or 'video_frame'
                        })
                        logger.debug(f"Stored raw bytes in cache for Gemini ({len(raw_bytes)} bytes, {base64_mime_type})")
                    media.save(update_fields=['supabase_url', 'uploaded_to_supabase'])
                    logger.info(f"Uploaded {media_type} to Supabase: {supabase_url}")
                    if base64_data:
                        logger.debug(f"Stored base64 in memory for GPT-4o ({len(base64_data)} chars, {base64_mime_type})")
                else:
                    logger.warning(f"Failed to upload {media_type}, will retry in background job")
            else:
                # Lazy upload (Twitter images)
                media.uploaded_to_supabase = False
                media.save(update_fields=['uploaded_to_supabase'])
                logger.debug(f"Marked {media_type} for lazy upload: {media.source_url}")
                
        except Exception as e:
            logger.error(f"Error processing media {media.id}: {e}")
            # Don't fail the entire post save if media processing fails

