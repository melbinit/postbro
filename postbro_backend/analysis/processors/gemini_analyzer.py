"""
Gemini Analyzer

Handles AI analysis of posts using Gemini API.
Includes media preparation, post data preparation, transcript handling,
Gemini API calls, PostAnalysis creation, and chat session creation.
"""

import logging
import time
from typing import List, Dict, Tuple, Optional
from analysis.models import PostAnalysisRequest, PostAnalysis, ChatSession, ChatMessage
from analysis.services import get_analysis_service
from social.models import Post, PostMedia, PostComment

logger = logging.getLogger(__name__)


def analyze_posts_with_gemini(
    analysis_request: PostAnalysisRequest,
    all_posts: List[Post],
    media_bytes_by_post_id: Dict,
) -> Tuple[List[Dict], int, int]:
    """
    Analyze posts using Gemini API.
    
    Args:
        analysis_request: The analysis request
        all_posts: List of posts to analyze
        media_bytes_by_post_id: Cache dict with media bytes
        
    Returns:
        Tuple of (analysis_results, successful_analyses, failed_analyses)
    """
    analysis_request_id_str = str(analysis_request.id)
    analyze_post = get_analysis_service()
    
    logger.info(f"🤖 [Analysis] Using Gemini for analysis of {len(all_posts)} post(s)")
    analysis_start_time = time.time()
    analysis_results = []
    successful_analyses = 0
    failed_analyses = 0
    
    for i, post in enumerate(all_posts):
        post_analysis_start = time.time()
        try:
            logger.info(f"📊 [Analysis] Processing post {i+1}/{len(all_posts)}: {post.id} (@{post.username})")
            
            # Prepare media images
            media_images, video_url_to_index = _prepare_media_images(
                post, media_bytes_by_post_id, analysis_request_id_str
            )
            
            # Prepare post data
            post_data = _prepare_post_data(post, analysis_request_id_str)
            
            # Prepare transcript
            transcript, video_length = _prepare_transcript(
                post, analysis_request, video_url_to_index
            )
            
            # Call Gemini
            task_id = str(analysis_request.id)
            user_id = str(analysis_request.user.id) if analysis_request.user else None
            logger.info(f"🚀 [Analysis] Calling Gemini for post {i+1}/{len(all_posts)}")
            
            analyze_kwargs = {
                'platform': analysis_request.platform,
                'task_id': task_id,
                'post_data': post_data,
                'media_images': media_images,
                'video_length': video_length,
                'transcript': transcript,
                'user_id': user_id,
                'analysis_request_id': analysis_request_id_str,  # For logging
                'post_id': str(post.id),  # For logging
            }
            
            ai_result = analyze_post(**analyze_kwargs)
            
            # Extract metadata
            metadata = ai_result.pop('_metadata', {})
            processing_time = metadata.get('processing_time_seconds', 0)
            usage = metadata.get('usage', {})
            
            logger.info(f"✅ [Analysis] Gemini analysis completed for post {i+1} in {processing_time:.2f}s")
            if usage:
                total_tokens = usage.get('total_token_count', 'N/A')
                prompt_tokens = usage.get('prompt_token_count', 'N/A')
                completion_tokens = usage.get('candidates_token_count', 'N/A')
                logger.info(f"📊 [Analysis] Tokens used: {total_tokens} "
                          f"(prompt: {prompt_tokens}, completion: {completion_tokens})")
            
            # Save PostAnalysis
            post_analysis = _save_post_analysis(
                analysis_request, post, ai_result, metadata, task_id
            )
            
            # Create chat session and messages
            _create_chat_session(
                analysis_request, post, post_analysis, metadata, usage, analysis_request_id_str
            )
            
            analysis_results.append({
                'post_id': str(post.id),
                'analysis_id': str(post_analysis.id),
                'is_viral': post_analysis.is_viral,
            })
            
            successful_analyses += 1
            post_analysis_time = time.time() - post_analysis_start
            logger.info(f"💾 [Analysis] Analysis saved for post {i+1} in {post_analysis_time:.2f}s total "
                      f"(viral: {post_analysis.is_viral})")
            
        except Exception as e:
            failed_analyses += 1
            post_analysis_time = time.time() - post_analysis_start
            error_type = type(e).__name__
            logger.error(
                f"❌ [Analysis] Failed to analyze post {i+1}/{len(all_posts)} ({post.id}) "
                f"after {post_analysis_time:.2f}s: {error_type} - {str(e)}",
                exc_info=True,
                extra={'analysis_request_id': analysis_request_id_str, 'post_id': str(post.id), 'post_index': i+1}
            )
            continue
    
    total_analysis_time = time.time() - analysis_start_time
    logger.info(f"🎉 [Analysis] Completed Gemini analysis for {len(all_posts)} posts: "
               f"{successful_analyses} successful, {failed_analyses} failed "
               f"in {total_analysis_time:.2f}s total "
               f"(avg: {total_analysis_time/len(all_posts):.2f}s per post)")
    
    return analysis_results, successful_analyses, failed_analyses


def _prepare_media_images(
    post: Post,
    media_bytes_by_post_id: Dict,
    analysis_request_id_str: str,
) -> Tuple[List[Dict], Dict[str, int]]:
    """Prepare media images for Gemini (images + video frames as bytes)."""
    media_images = []
    video_url_to_index = {}
    
    # Get video media items first to build video_url_to_index mapping
    video_media_list = list(post.media.filter(media_type='video').order_by('created_at'))
    for idx, video_media in enumerate(video_media_list):
        if video_media.source_url:
            video_url_to_index[video_media.source_url] = idx + 1
    
    # Process all media (images + frames)
    for media in post.media.all():
        cached_items = None
        if post.id in media_bytes_by_post_id and media.id in media_bytes_by_post_id[post.id]:
            cached_items = media_bytes_by_post_id[post.id][media.id]
        
        if cached_items:
            # Use cached bytes
            video_index = None
            if media.media_type == 'video_frame' and media.source_url and video_url_to_index:
                video_index = video_url_to_index.get(media.source_url)
            
            for cached_item in cached_items:
                media_images.append({
                    'bytes': cached_item['bytes'],
                    'mime_type': cached_item['mime_type'],
                    'media_type': cached_item.get('media_type', media.media_type),
                    'video_index': video_index,
                    'source_url': media.source_url,
                })
            
            if media.media_type == 'video_frame':
                video_info = f" (Video {video_index})" if video_index else ""
                logger.info(f"✅ [Analysis] Using cached frame bytes ({len(cached_items)} frames, "
                          f"{sum(len(item['bytes']) for item in cached_items)} total bytes){video_info}")
            else:
                logger.info(f"✅ [Analysis] Using cached image bytes ({len(cached_items[0]['bytes'])} bytes)")
        else:
            logger.error(f"❌ [Analysis] No cached bytes found for {media.media_type} "
                        f"(media.id={media.id}, post.id={post.id})")
            logger.warning(f"⚠️ [Analysis] Skipping {media.media_type} - Supabase fallback disabled")
            continue
    
    logger.info(f"📎 [Analysis] Post {post.id} has {len(media_images)} media items (images + frames) as bytes")
    return media_images, video_url_to_index


def _prepare_post_data(post: Post, analysis_request_id_str: str) -> Dict:
    """Prepare post data for Gemini analysis."""
    # Fetch latest comments (top 5)
    latest_comments = []
    try:
        comment_objects = PostComment.objects.filter(post=post).order_by('-created_at')[:5]
        for comment_obj in comment_objects:
            comment_data = comment_obj.comment_data if isinstance(comment_obj.comment_data, dict) else {}
            comment_dict = {
                'text': comment_data.get('comments') or comment_data.get('text') or comment_data.get('comment', ''),
                'username': comment_data.get('user_commenting') or comment_data.get('username') or comment_data.get('author', {}).get('username', 'Unknown'),
                'likes': comment_data.get('likes') or comment_data.get('likeCount', 0),
            }
            if comment_dict['text']:
                latest_comments.append(comment_dict)
        logger.info(f"💬 [Analysis] Fetched {len(latest_comments)} latest comments for post {post.id}")
    except Exception as e:
        logger.warning(f"⚠️ [Analysis] Failed to fetch comments: {e}")
    
    return {
        'username': post.username,
        'caption': post.content,
        'content': post.content,
        'posted_at': post.posted_at.isoformat() if post.posted_at else '',
        'metrics': post.metrics if isinstance(post.metrics, dict) else {},
        'latest_comments': latest_comments,
    }


def _prepare_transcript(
    post: Post,
    analysis_request: PostAnalysisRequest,
    video_url_to_index: Dict[str, int],
) -> Tuple[Optional[str], Optional[int]]:
    """Prepare transcript for Gemini analysis."""
    video_length = None
    transcript = None
    
    # Get ALL video media items
    video_media_list = list(post.media.filter(media_type='video').order_by('created_at'))
    transcript_parts = []
    
    if video_media_list:
        for idx, video_media in enumerate(video_media_list):
            if video_media and video_media.transcript and video_media.transcript.strip():
                if len(video_media_list) > 1:
                    transcript_parts.append(f"[Video {idx + 1} of {len(video_media_list)} Transcript]\n{video_media.transcript.strip()}")
                else:
                    transcript_parts.append(video_media.transcript.strip())
        
        if transcript_parts:
            transcript = '\n\n'.join(transcript_parts)
            logger.info(f"🎥 [Analysis] {analysis_request.platform} post: {len(video_media_list)} video(s), "
                      f"{len(transcript_parts)} transcript(s) available, combined ({len(transcript)} chars)")
        else:
            transcript = None
            logger.info(f"🎥 [Analysis] {analysis_request.platform} post: {len(video_media_list)} video(s) but no transcripts available")
    else:
        # Fallback to Post.transcript (YouTube only)
        transcript_raw = post.transcript or ''
        if transcript_raw and transcript_raw.strip():
            transcript = transcript_raw.strip()
            logger.info(f"🎥 [Analysis] {analysis_request.platform} post: transcript from Post ({len(transcript)} chars) - fallback")
        else:
            transcript = None
            logger.info(f"🎥 [Analysis] {analysis_request.platform} post: no videos or transcripts found")
    
    # Get video_length (YouTube only)
    if analysis_request.platform == 'youtube':
        video_length = post.metrics.get('video_length', 0) if isinstance(post.metrics, dict) else 0
        logger.info(f"🎥 [Analysis] YouTube post: {video_length}s video, transcript: {len(transcript) if transcript else 0} chars")
    
    return transcript, video_length


def _save_post_analysis(
    analysis_request: PostAnalysisRequest,
    post: Post,
    ai_result: Dict,
    metadata: Dict,
    task_id: str,
) -> PostAnalysis:
    """Save PostAnalysis to database."""
    is_viral = ai_result.get('is_viral', False)
    improvements = ai_result.get('improvements', [])
    if is_viral and improvements:
        logger.info(f"✅ [Analysis] Post is viral - clearing improvements array")
        improvements = []
    
    return PostAnalysis.objects.create(
        analysis_request=analysis_request,
        post=post,
        task_id=ai_result.get('task_id', task_id),
        is_viral=is_viral,
        virality_reasoning=ai_result.get('virality_reasoning', ''),
        creator_context=ai_result.get('creator_context', ''),
        quick_takeaways=ai_result.get('quick_takeaways', []),
        content_observation=ai_result.get('content_observation', {}),
        replicable_elements=ai_result.get('replicable_elements', []),
        analysis_data=ai_result.get('analysis', {}),
        improvements=improvements,
        suggestions_for_future_posts=ai_result.get('suggestions_for_future_posts', []),
        viral_formula=ai_result.get('viral_formula', ''),
        metadata_used=ai_result.get('metadata_used', {}),
        llm_model=metadata.get('model', 'gemini-2.5-flash'),
        llm_response_raw=metadata.get('raw_response', ''),
        processing_time_seconds=metadata.get('processing_time_seconds', 0),
        analysis_completed=True,
    )


def _create_chat_session(
    analysis_request: PostAnalysisRequest,
    post: Post,
    post_analysis: PostAnalysis,
    metadata: Dict,
    usage: Dict,
    analysis_request_id_str: str,
) -> None:
    """Create chat session and initial messages (chat-first approach)."""
    try:
        # Create or get chat session
        chat_session, created = ChatSession.objects.get_or_create(
            post_analysis=post_analysis,
            user=analysis_request.user,
            defaults={'status': ChatSession.Status.ACTIVE}
        )
        
        if created:
            logger.info(f"💬 [Analysis] Created chat session {chat_session.id} for post_analysis {post_analysis.id}")
        else:
            logger.info(f"💬 [Analysis] Using existing chat session {chat_session.id} for post_analysis {post_analysis.id}")
        
        # Check if messages already exist (avoid duplicates on retry)
        existing_messages = chat_session.messages.all()
        if existing_messages.count() == 0:
            # Create first user message (the URL)
            user_message = ChatMessage.objects.create(
                session=chat_session,
                role=ChatMessage.Role.USER,
                content=post.url,
            )
            logger.info(f"💬 [Analysis] Created first user message: {user_message.id} (URL: {post.url[:50]}...)")
            
            # Create first AI message (the analysis response)
            ai_response_content = metadata.get('raw_response', '')
            if not ai_response_content:
                logger.warning(f"⚠️ [Analysis] No raw_response in metadata, constructing from structured data")
                ai_response_content = f"# Analysis\n\nAnalysis completed."
            
            ai_message = ChatMessage.objects.create(
                session=chat_session,
                role=ChatMessage.Role.ASSISTANT,
                content=ai_response_content,
                tokens_used=usage.get('total_token_count') if usage else None,
            )
            logger.info(f"💬 [Analysis] Created first AI message: {ai_message.id} ({len(ai_response_content)} chars)")
            
            # Update session metrics (non-blocking, simple DB update)
            chat_session.messages_count = chat_session.messages.count()
            tokens_used_value = usage.get('total_token_count') if usage else None
            if tokens_used_value:
                chat_session.total_tokens = tokens_used_value
            
            # Calculate duration: time from first to last message
            messages = chat_session.messages.order_by('created_at')
            first_msg = messages.first()
            last_msg = messages.last()
            if first_msg and last_msg and first_msg != last_msg:
                duration = (last_msg.created_at - first_msg.created_at).total_seconds()
                chat_session.duration_seconds = duration
            elif first_msg and last_msg:
                # Only one message or same message, duration is 0
                chat_session.duration_seconds = 0.0
            
            chat_session.save(update_fields=['messages_count', 'total_tokens', 'duration_seconds'])
        else:
            logger.info(f"💬 [Analysis] Chat session already has {existing_messages.count()} messages, skipping initial message creation")
            
    except Exception as chat_error:
        logger.error(
            f"❌ [Analysis] Failed to create chat session/messages: {chat_error}",
            exc_info=True,
            extra={'analysis_request_id': analysis_request_id_str, 'post_id': str(post.id)}
        )
        # Don't fail the entire analysis if chat creation fails

