"""
Media Extractor

Handles media extraction, frame conversion, and transcription tracking.
"""

import logging
from typing import List, Dict, Set
from analysis.models import PostAnalysisRequest
from social.models import Post, PostMedia

logger = logging.getLogger(__name__)


def extract_media_for_analysis(
    analysis_request: PostAnalysisRequest,
    all_posts: List[Post],
    media_bytes_by_post_id: Dict,
    fast_path_post_ids: Set = None,
) -> None:
    """
    Extract media (frames, etc.) for analysis.
    Skips fast path posts (media already exists and cache already populated).
    
    Args:
        analysis_request: The analysis request
        all_posts: List of posts to extract media for
        media_bytes_by_post_id: Cache dict to store media bytes
        fast_path_post_ids: Set of post IDs that used fast path (skip extraction)
    """
    if fast_path_post_ids is None:
        fast_path_post_ids = set()
    
    # Extract frames for YouTube videos (only for slow path posts)
    if analysis_request.platform == 'youtube' and all_posts:
        from social.services.media_processor import MediaProcessor
        
        # Filter out fast path posts
        posts_to_process = [p for p in all_posts if p.id not in fast_path_post_ids]
        
        if not posts_to_process:
            logger.info(f"⚡ [FastPath] All posts used fast path, skipping frame extraction")
            return
        
        logger.info(f"🎬 Starting frame extraction for {len(posts_to_process)} YouTube video(s) (skipped {len(all_posts) - len(posts_to_process)} fast path)")
        media_processor = MediaProcessor()
        
        for post in posts_to_process:
            if post.platform.name == 'youtube':
                video_id = post.platform_post_id
                try:
                    logger.info(f"Extracting frames for YouTube video {video_id} (post {post.id})")
                    frame_urls, frame_bytes_list = media_processor.process_youtube_video(
                        video_id=video_id,
                        post_id=str(post.id),
                        num_frames=5
                    )
                    
                    if frame_urls:
                        # Save frame URLs to PostMedia + store bytes
                        for i, (frame_url, frame_bytes) in enumerate(zip(frame_urls, frame_bytes_list)):
                            frame_media = PostMedia.objects.create(
                                post=post,
                                media_type='video_frame',
                                source_url=post.url,
                                supabase_url=frame_url,
                                uploaded_to_supabase=True,
                            )
                            # Store raw bytes in separate cache dict (survives refresh_from_db())
                            if post.id not in media_bytes_by_post_id:
                                media_bytes_by_post_id[post.id] = {}
                            if frame_media.id not in media_bytes_by_post_id[post.id]:
                                media_bytes_by_post_id[post.id][frame_media.id] = []
                            media_bytes_by_post_id[post.id][frame_media.id].append({
                                'bytes': frame_bytes,
                                'mime_type': 'image/jpeg',
                                'media_type': 'video_frame'
                            })
                        logger.info(f"✅ Saved {len(frame_urls)} frames for YouTube video {video_id} (with bytes)")
                    else:
                        logger.warning(f"⚠️ Could not extract frames for YouTube video {video_id} - continuing without frames")
                except Exception as e:
                    logger.warning(f"⚠️ Frame extraction failed for YouTube video {video_id}: {e} - continuing without frames")
                    # Continue even if frame extraction fails - don't block the analysis
        
        logger.info(f"✅ Frame extraction completed for analysis {analysis_request.id}")


def check_transcription_status(all_posts: List[Post]) -> bool:
    """
    Check if any posts have videos that need transcription.
    
    Args:
        all_posts: List of posts to check
        
    Returns:
        bool: True if any posts have videos
    """
    return any(
        post.media.filter(media_type='video').exists() 
        for post in all_posts
    )
