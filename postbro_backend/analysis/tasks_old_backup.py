"""
Celery Tasks for Analysis Processing

This module contains Celery tasks for processing analysis requests,
including scraping social media data and saving posts to the database.
"""

import os
import logging
import time
import requests
from typing import List, Dict, Optional, Tuple
from celery import shared_task
from django.utils import timezone

from .models import PostAnalysisRequest, AnalysisStatusHistory
from .utils import (
    create_status,
    create_error_status,
    create_partial_success_status,
    estimate_cost,
    calculate_progress_percentage,
    handle_analysis_error,
)
from social.services.url_parser import detect_platform_from_url, extract_post_id
from social.scrapers import BrightDataScraper, TwitterAPIScraper
from social.services.post_saver import PostSaver
from social.models import Post, Platform

logger = logging.getLogger(__name__)


def check_existing_posts(urls: List[str], platform: str) -> Dict[str, Optional[Post]]:
    """
    Check which URLs already have posts in DB.
    This enables fast path optimization (skip media processing, only update metrics).
    
    Args:
        urls: List of post URLs to check
        platform: Platform name ('instagram', 'youtube', 'x')
        
    Returns:
        Dictionary mapping URL to Post instance (or None if post doesn't exist)
    """
    existing_posts = {}
    
    try:
        # Map analysis request platform to social Platform model
        platform_name_map = {
            'instagram': 'instagram',
            'x': 'twitter',  # Twitter model uses 'twitter', not 'x'
            'youtube': 'youtube',
        }
        platform_name = platform_name_map.get(platform)
        
        if not platform_name:
            logger.warning(f"Unknown platform {platform} for duplicate check")
            return {url: None for url in urls}
        
        platform_obj = Platform.objects.get(name=platform_name)
        
        for url in urls:
            post_id = extract_post_id(url, platform)
            if not post_id:
                existing_posts[url] = None
                logger.debug(f"Could not extract post ID from {url}")
                continue
            
            try:
                post = Post.objects.get(
                    platform=platform_obj,
                    platform_post_id=post_id
                )
                existing_posts[url] = post
                logger.info(f"✅ [DuplicateCheck] Found existing post for {url}: {post.id} (@{post.username})")
            except Post.DoesNotExist:
                existing_posts[url] = None
                logger.info(f"🆕 [DuplicateCheck] New post for {url}")
            except Post.MultipleObjectsReturned:
                # Shouldn't happen due to unique_together, but handle gracefully
                post = Post.objects.filter(
                    platform=platform_obj,
                    platform_post_id=post_id
                ).first()
                existing_posts[url] = post
                logger.warning(f"⚠️ [DuplicateCheck] Multiple posts found for {url}, using first: {post.id if post else None}")
                
    except Platform.DoesNotExist:
        logger.error(f"Platform '{platform_name}' not found in database")
        return {url: None for url in urls}
    except Exception as e:
        logger.error(f"Error checking existing posts: {e}", exc_info=True)
        return {url: None for url in urls}
    
    return existing_posts


@shared_task(bind=True, max_retries=3)
def process_analysis_request(self, analysis_request_id: str):
    """
    Main Celery task to process an analysis request.
    
    This task handles:
    - URL parsing and platform detection
    - Scraping social media data
    - Saving posts to database
    - Creating status history entries
    - Error handling with partial failures
    
    Args:
        analysis_request_id: UUID of the PostAnalysisRequest
        
    Returns:
        Dictionary with processing results
        
    Raises:
        Retry exception if retryable error occurs
    """
    analysis_request_id_str = str(analysis_request_id)  # Keep for consistent logging
    
    logger.info(f"🚀 [CeleryTask] Task received - analysis_request_id: {analysis_request_id_str}, task_id: {self.request.id}")
    logger.info(f"📋 [CeleryTask] Task details - retries: {self.request.retries}, max_retries: {self.max_retries}")
    
    start_time = timezone.now()
    api_calls_made = 0
    
    try:
        # Get the analysis request
        logger.info(f"🔍 [CeleryTask] Fetching analysis request from database...")
        analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
        
        logger.info(f"✅ [CeleryTask] Analysis request found: {analysis_request_id}")
        logger.info(f"📊 [CeleryTask] Request details - platform: {analysis_request.platform}, "
                   f"status: {analysis_request.status}, "
                   f"post_urls: {len(analysis_request.post_urls) if analysis_request.post_urls else 0}")
        
        logger.info(f"🚀 [CeleryTask] Starting analysis request {analysis_request_id}")
        
        # Status 1: Request created (already done in view, but ensure it exists)
        try:
            latest_status = analysis_request.status_history.order_by('-created_at').first()
            if not latest_status or latest_status.stage != 'request_created':
                create_status(
                    analysis_request,
                    'request_created',
                    'Analysis request created',
                    metadata={'urls_count': len(analysis_request.post_urls)},
                    progress_percentage=0
                )
        except Exception as e:
            logger.warning(
                f"⚠️ [Analysis] Could not create initial status for analysis_request_id={analysis_request_id_str}: {e}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
        
        # Validate that we have URLs (username support deferred)
        if not analysis_request.post_urls:
            raise ValueError("post_urls is required. Username-based analysis not yet implemented.")
        
        # Status 2: Fetching posts (API calls)
        create_status(
            analysis_request,
            'fetching_posts',
            'Fetching posts...',
            metadata={'urls_count': len(analysis_request.post_urls)},
            progress_percentage=10,
            api_calls_made=0  # Will be updated as we make calls
        )
        
        # Parse URLs and group by platform
        urls_by_platform: Dict[str, List[str]] = {}
        invalid_urls = []
        
        for url in analysis_request.post_urls:
            platform = detect_platform_from_url(url)
            if not platform:
                logger.warning(f"Invalid URL format: {url}")
                invalid_urls.append(url)
                create_error_status(
                    analysis_request,
                    'INVALID_URL',
                    f'Invalid URL format: {url}',
                    retryable=False,
                    actionable_message='Please check the URL format and try again',
                    metadata={'url': url}
                )
                continue
            
            if platform not in urls_by_platform:
                urls_by_platform[platform] = []
            urls_by_platform[platform].append(url)
        
        if not urls_by_platform:
            raise ValueError("No valid URLs found. All URLs were invalid.")
        
        # Scrape posts by platform
        all_posts = []
        failed_urls = []
        succeeded_count = 0
        total_api_calls = 0
        
        # Store media bytes separately (not on Post objects, so they survive refresh_from_db())
        # Structure: {post_id: {media_id: [{'bytes': bytes, 'mime_type': str, 'media_type': str}]}}
        media_bytes_by_post_id = {}
        
        for platform, urls in urls_by_platform.items():
            try:
                logger.info(f"🔍 [DuplicateCheck] Checking {len(urls)} {platform} URLs for existing posts...")
                
                # Check for existing posts BEFORE scraping (optimization)
                existing_posts = check_existing_posts(urls, platform)
                existing_count = sum(1 for p in existing_posts.values() if p is not None)
                new_count = len(urls) - existing_count
                logger.info(f"📊 [DuplicateCheck] Found {existing_count} existing posts, {new_count} new posts")
                
                if platform == 'instagram':
                    scraper = BrightDataScraper()
                    saver = PostSaver(analysis_request, media_bytes_cache=media_bytes_by_post_id)
                    
                    # Process each URL individually to handle fast/slow paths
                    for url in urls:
                        existing_post = existing_posts.get(url)
                        
                        if existing_post:
                            # FAST PATH: Post exists - update metrics only, reuse media
                            logger.info(f"⚡ [FastPath] Post exists for {url}, updating metrics and reusing media...")
                            try:
                                # Call API to get fresh metrics (same API call, but we'll only use metrics)
                                fresh_data = scraper.scrape_instagram_post(url)
                                total_api_calls += 1
                                
                                if fresh_data.get('success'):
                                    # Update metrics only
                                    saver.update_existing_post_metrics(existing_post, fresh_data, 'instagram')
                                    
                                    # Reuse existing media from Supabase
                                    saver.reuse_existing_media(existing_post)
                                    
                                    # Link to analysis request
                                    if not analysis_request.posts.filter(id=existing_post.id).exists():
                                        analysis_request.posts.add(existing_post)
                                        analysis_request.save()
                                    
                                    all_posts.append(existing_post)
                                    succeeded_count += 1
                                    logger.info(f"✅ [FastPath] Successfully updated existing post {existing_post.id}")
                                else:
                                    logger.error(f"❌ [FastPath] Failed to fetch fresh metrics for {url}: {fresh_data.get('error')}")
                                    failed_urls.append(url)
                            except Exception as e:
                                logger.error(f"❌ [FastPath] Error updating existing post {url}: {e}", exc_info=True)
                                failed_urls.append(url)
                        else:
                            # SLOW PATH: New post - full processing
                            logger.info(f"🔄 [FullPath] New post, full processing for {url}")
                            try:
                                results = scraper.scrape_instagram_posts([url])
                                total_api_calls += 1
                                
                                for result in results:
                                    if result.get('error') or not result.get('success', True):
                                        failed_urls.append(result.get('url', 'unknown'))
                                        logger.error(
                                            f"❌ [Analysis] Failed to scrape Instagram post for analysis_request_id={analysis_request_id_str}: {result.get('error')}",
                                            extra={'analysis_request_id': analysis_request_id_str, 'url': result.get('url', 'unknown'), 'platform': 'instagram'}
                                        )
                                    else:
                                        try:
                                            post = saver.save_instagram_post(result)
                                            all_posts.append(post)
                                            
                                            # Link post to analysis request via ManyToMany (enables reuse/caching)
                                            # CRITICAL: This must happen for posts to appear in frontend
                                            logger.info(f"🔗 [Instagram] Linking post {post.id} to analysis {analysis_request.id}")
                                            try:
                                                analysis_request.posts.add(post)
                                                # Force save and refresh to ensure link is persisted
                                                analysis_request.save()
                                                analysis_request.refresh_from_db()
                                                
                                                # Verify the link was created
                                                if analysis_request.posts.filter(id=post.id).exists():
                                                    logger.info(f"✅ [Instagram] Linked post {post.id} to analysis {analysis_request.id}")
                                                else:
                                                    logger.error(f"❌ [Instagram] FAILED to verify post {post.id} link - retrying...")
                                                    # Retry linking with explicit save
                                                    analysis_request.posts.add(post)
                                                    analysis_request.save()
                                                    analysis_request.refresh_from_db()
                                                    if analysis_request.posts.filter(id=post.id).exists():
                                                        logger.info(f"✅ [Instagram] Retry successful: Linked post {post.id} to analysis {analysis_request.id}")
                                                    else:
                                                        logger.error(f"❌❌ [Instagram] Retry FAILED: Post {post.id} still not linked - this is critical!")
                                                        # Last resort: direct database update
                                                        from django.db import connection
                                                        with connection.cursor() as cursor:
                                                            cursor.execute(
                                                                "INSERT INTO analysis_postanalysisrequest_posts (postanalysisrequest_id, post_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                                                [str(analysis_request.id), str(post.id)]
                                                            )
                                                        analysis_request.refresh_from_db()
                                                        if analysis_request.posts.filter(id=post.id).exists():
                                                            logger.info(f"✅ [Instagram] Direct DB insert successful: Linked post {post.id}")
                                                        else:
                                                            logger.error(f"❌❌❌ [Instagram] Even direct DB insert failed!")
                                            except Exception as link_error:
                                                logger.error(f"❌ [Instagram] Failed to link post {post.id} to analysis {analysis_request.id}: {link_error}", exc_info=True)
                                                # Try direct DB insert as fallback
                                                try:
                                                    from django.db import connection
                                                    with connection.cursor() as cursor:
                                                        cursor.execute(
                                                            "INSERT INTO analysis_postanalysisrequest_posts (postanalysisrequest_id, post_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                                            [str(analysis_request.id), str(post.id)]
                                                        )
                                                    analysis_request.refresh_from_db()
                                                    if analysis_request.posts.filter(id=post.id).exists():
                                                        logger.info(f"✅ [Instagram] Fallback DB insert successful: Linked post {post.id}")
                                                    else:
                                                        logger.error(f"❌ [Instagram] Fallback DB insert also failed!")
                                                except Exception as db_error:
                                                    logger.error(f"❌ [Instagram] Fallback DB insert error: {db_error}", exc_info=True)
                                            
                                            # Verify all media has been uploaded before proceeding
                                            media_without_url = post.media.filter(
                                                media_type__in=['image', 'video_thumbnail'],
                                                supabase_url__isnull=True
                                            ).exclude(uploaded_to_supabase=True)
                                            
                                            if media_without_url.exists():
                                                logger.warning(f"Post {post.id} has {media_without_url.count()} media items without supabase_url")
                                            
                                            succeeded_count += 1
                                        except Exception as e:
                                            logger.error(
                                                f"❌ [Analysis] Failed to save Instagram post for analysis_request_id={analysis_request_id_str}: {e}",
                                                exc_info=True,
                                                extra={'analysis_request_id': analysis_request_id_str, 'platform': 'instagram', 'url': result.get('url', 'unknown')}
                                            )
                                            logger.error(
                                                f"   Error type: {type(e).__name__}, Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}",
                                                extra={'analysis_request_id': analysis_request_id_str}
                                            )
                                            failed_urls.append(result.get('url', 'unknown'))
                            except Exception as e:
                                logger.error(
                                    f"❌ [Analysis] Failed to scrape Instagram post {url} for analysis_request_id={analysis_request_id_str}: {e}",
                                    exc_info=True,
                                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'instagram'}
                                )
                                failed_urls.append(url)
                
                elif platform == 'youtube':
                    scraper = BrightDataScraper()
                    saver = PostSaver(analysis_request, media_bytes_cache=media_bytes_by_post_id)
                    
                    # Process each URL individually to handle fast/slow paths
                    for url in urls:
                        existing_post = existing_posts.get(url)
                        
                        if existing_post:
                            # FAST PATH: Post exists - update metrics only, reuse media
                            logger.info(f"⚡ [FastPath] Post exists for {url}, updating metrics and reusing media...")
                            try:
                                # Call API to get fresh metrics
                                fresh_data = scraper.scrape_youtube_video(url)
                                total_api_calls += 1
                                
                                if fresh_data.get('success'):
                                    # Update metrics only
                                    saver.update_existing_post_metrics(existing_post, fresh_data, 'youtube')
                                    
                                    # Reuse existing media from Supabase
                                    saver.reuse_existing_media(existing_post)
                                    
                                    # Link to analysis request
                                    if not analysis_request.posts.filter(id=existing_post.id).exists():
                                        analysis_request.posts.add(existing_post)
                                        analysis_request.save()
                                    
                                    all_posts.append(existing_post)
                                    succeeded_count += 1
                                    logger.info(f"✅ [FastPath] Successfully updated existing post {existing_post.id}")
                                else:
                                    logger.error(f"❌ [FastPath] Failed to fetch fresh metrics for {url}: {fresh_data.get('error')}")
                                    failed_urls.append(url)
                            except Exception as e:
                                logger.error(
                                    f"❌ [Analysis] FastPath error updating existing YouTube post {url} for analysis_request_id={analysis_request_id_str}: {e}",
                                    exc_info=True,
                                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'youtube'}
                                )
                                failed_urls.append(url)
                        else:
                            # SLOW PATH: New post - full processing
                            logger.info(f"🔄 [FullPath] New post, full processing for {url}")
                            try:
                                results = scraper.scrape_youtube_videos([url])
                                total_api_calls += 1
                                
                                for i, result in enumerate(results):
                                    logger.info(f"📊 [YouTube] Processing result {i+1}/{len(results)}")
                                    if result.get('error') or not result.get('success', True):
                                        error_msg = result.get('error', 'Unknown error')
                                        result_url = result.get('url', url)
                                        failed_urls.append(result_url)
                                        logger.error(
                                            f"❌ [Analysis] Failed to scrape YouTube video {result_url} for analysis_request_id={analysis_request_id_str}: {error_msg}",
                                            extra={'analysis_request_id': analysis_request_id_str, 'url': result_url, 'platform': 'youtube'}
                                        )
                                        logger.error(
                                            f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}",
                                            extra={'analysis_request_id': analysis_request_id_str}
                                        )
                                    else:
                                        try:
                                            logger.info(f"💾 [YouTube] Saving video to database...")
                                            post = saver.save_youtube_video(result)
                                            logger.info(f"✅ [YouTube] Video saved: post_id={post.id}, video_id={post.platform_post_id}")
                                            all_posts.append(post)
                                            
                                            # Link post to analysis request via ManyToMany (enables reuse/caching)
                                            # CRITICAL: This must happen for posts to appear in frontend
                                            logger.info(f"🔗 [YouTube] Starting link process for post {post.id} to analysis {analysis_request.id}")
                                            logger.info(f"📊 [YouTube] Pre-link state - analysis_request.id: {analysis_request.id}, post.id: {post.id}")
                                            logger.info(f"📊 [YouTube] Pre-link - analysis_request.posts.count(): {analysis_request.posts.count()}")
                                            
                                            # Check if already linked
                                            if analysis_request.posts.filter(id=post.id).exists():
                                                logger.warning(f"⚠️ [YouTube] Post {post.id} already linked to analysis {analysis_request.id} - skipping")
                                            else:
                                                logger.info(f"🔗 [YouTube] Post {post.id} not linked yet - adding now...")
                                                try:
                                                    analysis_request.posts.add(post)
                                                    logger.info(f"✅ [YouTube] Called analysis_request.posts.add(post) for post {post.id}")
                                                except Exception as add_error:
                                                    logger.error(f"❌ [YouTube] Exception during posts.add(): {type(add_error).__name__}: {str(add_error)}", exc_info=True)
                                                    raise
                                                
                                                # Force save to ensure link is persisted
                                                logger.info(f"💾 [YouTube] Saving analysis_request after adding post...")
                                                try:
                                                    analysis_request.save()
                                                    logger.info(f"✅ [YouTube] analysis_request.save() completed")
                                                except Exception as save_error:
                                                    logger.error(f"❌ [YouTube] Exception during save(): {type(save_error).__name__}: {str(save_error)}", exc_info=True)
                                                    raise
                                                
                                                # Verify the link was created
                                                logger.info(f"🔄 [YouTube] Refreshing analysis_request from DB...")
                                                analysis_request.refresh_from_db()
                                                logger.info(f"📊 [YouTube] Post-link - analysis_request.posts.count(): {analysis_request.posts.count()}")
                                                
                                                # Check if link exists
                                                link_exists = analysis_request.posts.filter(id=post.id).exists()
                                                logger.info(f"🔍 [YouTube] Link verification - post {post.id} exists in analysis_request.posts: {link_exists}")
                                                
                                                if link_exists:
                                                    logger.info(f"✅ [YouTube] SUCCESS: Linked post {post.id} to analysis {analysis_request.id}")
                                                else:
                                                    logger.error(f"❌ [YouTube] FAILED to link post {post.id} to analysis {analysis_request.id} - retrying...")
                                                    logger.info(f"📊 [YouTube] Retry attempt - Current posts count: {analysis_request.posts.count()}")
                                                    
                                                    # Retry linking with more explicit approach
                                                    try:
                                                        # Clear and re-add
                                                        logger.info(f"🔄 [YouTube] Retry: Clearing and re-adding post...")
                                                        analysis_request.posts.remove(post)  # Remove if exists (shouldn't, but safe)
                                                        analysis_request.posts.add(post)
                                                        analysis_request.save()
                                                        analysis_request.refresh_from_db()
                                                        
                                                        retry_link_exists = analysis_request.posts.filter(id=post.id).exists()
                                                        logger.info(f"🔍 [YouTube] Retry verification - post {post.id} exists: {retry_link_exists}")
                                                        
                                                        if retry_link_exists:
                                                            logger.info(f"✅ [YouTube] Retry SUCCESS: Linked post {post.id} to analysis {analysis_request.id}")
                                                        else:
                                                            logger.error(f"❌❌ [YouTube] Retry FAILED: Post {post.id} still not linked to analysis {analysis_request.id}")
                                                            # Last resort: direct SQL insert
                                                            logger.warning(f"🔧 [YouTube] Attempting direct SQL insert as last resort...")
                                                            try:
                                                                from django.db import connection
                                                                with connection.cursor() as cursor:
                                                                    cursor.execute(
                                                                        "INSERT INTO analysis_postanalysisrequest_posts (postanalysisrequest_id, post_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                                                        [str(analysis_request.id), str(post.id)]
                                                                    )
                                                                analysis_request.refresh_from_db()
                                                                sql_link_exists = analysis_request.posts.filter(id=post.id).exists()
                                                                if sql_link_exists:
                                                                    logger.info(f"✅ [YouTube] Direct SQL insert SUCCESS: Post {post.id} now linked")
                                                                else:
                                                                    logger.error(f"❌❌❌ [YouTube] Direct SQL insert also FAILED!")
                                                            except Exception as sql_error:
                                                                logger.error(f"❌❌❌ [YouTube] Direct SQL insert exception: {type(sql_error).__name__}: {str(sql_error)}", exc_info=True)
                                                    except Exception as retry_error:
                                                        logger.error(f"❌ [YouTube] Retry exception: {type(retry_error).__name__}: {str(retry_error)}", exc_info=True)
                                            
                                            succeeded_count += 1
                                            logger.info(f"🎉 [YouTube] Successfully processed video: {result.get('url', 'unknown')}")
                                        except Exception as e:
                                            error_type = type(e).__name__
                                            logger.error(
                                                f"❌ [Analysis] Failed to save YouTube video for analysis_request_id={analysis_request_id_str}: {error_type} - {str(e)}",
                                                exc_info=True,
                                                extra={'analysis_request_id': analysis_request_id_str, 'platform': 'youtube', 'url': result.get('url', 'unknown')}
                                            )
                                            logger.error(
                                                f"   Result keys: {list(result.keys()) if isinstance(result, dict) else 'Not a dict'}",
                                                extra={'analysis_request_id': analysis_request_id_str}
                                            )
                                            failed_urls.append(result.get('url', 'unknown'))
                            except Exception as e:
                                logger.error(
                                    f"❌ [Analysis] Failed to scrape YouTube video {url} for analysis_request_id={analysis_request_id_str}: {e}",
                                    exc_info=True,
                                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'youtube'}
                                )
                                failed_urls.append(url)
                
                elif platform == 'x':
                    scraper = TwitterAPIScraper()
                    saver = PostSaver(analysis_request, media_bytes_cache=media_bytes_by_post_id)
                    
                    # Process each URL individually to handle fast/slow paths
                    for url in urls:
                        existing_post = existing_posts.get(url)
                        
                        if existing_post:
                            # FAST PATH: Post exists - update metrics only, reuse media
                            logger.info(f"⚡ [FastPath] Post exists for {url}, updating metrics and reusing media...")
                            try:
                                # Call API to get fresh metrics
                                fresh_data = scraper.scrape_tweet(url)
                                total_api_calls += 1
                                
                                if fresh_data.get('success'):
                                    # Update metrics only
                                    saver.update_existing_post_metrics(existing_post, fresh_data, 'x')
                                    
                                    # Reuse existing media from Supabase
                                    saver.reuse_existing_media(existing_post)
                                    
                                    # Link to analysis request
                                    if not analysis_request.posts.filter(id=existing_post.id).exists():
                                        analysis_request.posts.add(existing_post)
                                        analysis_request.save()
                                    
                                    all_posts.append(existing_post)
                                    succeeded_count += 1
                                    logger.info(f"✅ [FastPath] Successfully updated existing post {existing_post.id}")
                                else:
                                    logger.error(f"❌ [FastPath] Failed to fetch fresh metrics for {url}: {fresh_data.get('error')}")
                                    failed_urls.append(url)
                            except Exception as e:
                                logger.error(
                                    f"❌ [Analysis] FastPath error updating existing Twitter/X post {url} for analysis_request_id={analysis_request_id_str}: {e}",
                                    exc_info=True,
                                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'x'}
                                )
                                failed_urls.append(url)
                        else:
                            # SLOW PATH: New post - full processing
                            logger.info(f"🔄 [FullPath] New post, full processing for {url}")
                            try:
                                results = scraper.scrape_tweets([url])
                                total_api_calls += 1
                                
                                for result in results:
                                    if result.get('error') or not result.get('success', True):
                                        failed_urls.append(result.get('url', 'unknown'))
                                        logger.error(
                                            f"❌ [Analysis] Failed to scrape Twitter/X tweet for analysis_request_id={analysis_request_id_str}: {result.get('error')}",
                                            extra={'analysis_request_id': analysis_request_id_str, 'url': result.get('url', 'unknown'), 'platform': 'x'}
                                        )
                                    else:
                                        try:
                                            post = saver.save_twitter_tweet(result)
                                            all_posts.append(post)
                                            # Link post to analysis request via ManyToMany (enables reuse/caching)
                                            # CRITICAL: This must happen for posts to appear in frontend
                                            analysis_request.posts.add(post)
                                            logger.info(f"✅ Linked post {post.id} to analysis {analysis_request.id}")
                                            succeeded_count += 1
                                        except Exception as e:
                                            logger.error(
                                                f"❌ [Analysis] Failed to save Twitter/X tweet for analysis_request_id={analysis_request_id_str}: {e}",
                                                exc_info=True,
                                                extra={'analysis_request_id': analysis_request_id_str, 'platform': 'x', 'url': result.get('url', 'unknown')}
                                            )
                                            failed_urls.append(result.get('url', 'unknown'))
                            except Exception as e:
                                logger.error(
                                    f"❌ [Analysis] Failed to scrape Twitter/X tweet {url} for analysis_request_id={analysis_request_id_str}: {e}",
                                    exc_info=True,
                                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'x'}
                                )
                                failed_urls.append(url)
                
                else:
                    logger.error(f"Unsupported platform: {platform}")
                    failed_urls.extend(urls)
            
            except Exception as e:
                # Platform-level error in social collection
                handle_analysis_error(
                    analysis_request,
                    error_stage=PostAnalysisRequest.ErrorStage.SOCIAL_COLLECTION,
                    exception=e,
                    failed_at_stage='fetching_posts',
                    metadata={'platform': platform, 'urls': urls, 'failed_urls': failed_urls}
                )
                failed_urls.extend(urls)
                # Don't return here - continue to check if we have any successful posts
        
        # Calculate cost estimate
        cost_estimate = estimate_cost(
            platform=analysis_request.platform,
            api_calls=total_api_calls,
            operation_type='scraping'
        )
        
        # CRITICAL: Re-verify and re-link all posts before proceeding
        # This ensures posts are linked even if linking failed earlier
        logger.info(f"🔍 [Verification] Re-verifying {len(all_posts)} post(s) are linked to analysis {analysis_request.id}")
        analysis_request.refresh_from_db()
        linked_count_before = analysis_request.posts.count()
        
        for post in all_posts:
            if not analysis_request.posts.filter(id=post.id).exists():
                logger.warning(f"⚠️ [Verification] Post {post.id} is NOT linked - re-linking now...")
                try:
                    analysis_request.posts.add(post)
                except Exception as e:
                    logger.error(f"❌ [Verification] Failed to re-link post {post.id}: {e}")
                    # Try direct DB insert
                    try:
                        from django.db import connection
                        with connection.cursor() as cursor:
                            cursor.execute(
                                "INSERT INTO analysis_postanalysisrequest_posts (postanalysisrequest_id, post_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                [str(analysis_request.id), str(post.id)]
                            )
                        logger.info(f"✅ [Verification] Direct DB insert for post {post.id}")
                    except Exception as db_e:
                        logger.error(f"❌ [Verification] Direct DB insert failed for post {post.id}: {db_e}")
        
        analysis_request.save()
        analysis_request.refresh_from_db()
        linked_count_after = analysis_request.posts.count()
        logger.info(f"📊 [Verification] Linked posts: {linked_count_before} -> {linked_count_after} (expected: {len(all_posts)})")
        
        if linked_count_after != len(all_posts):
            logger.error(f"❌ [Verification] MISMATCH: Expected {len(all_posts)} linked posts, but only {linked_count_after} are linked!")
        
        # Verify all media uploads completed before marking as fetched
        # Refresh posts to get latest media data
        for post in all_posts:
            post.refresh_from_db()
            # Check if any media is still uploading
            pending_media = post.media.filter(
                media_type__in=['image', 'video_thumbnail'],
                supabase_url__isnull=True,
                uploaded_to_supabase=False
            )
            if pending_media.exists():
                logger.warning(f"Post {post.id} has {pending_media.count()} media items still uploading")
        
        # Status 3: Social data fetched (or partial success)
        if failed_urls and succeeded_count > 0:
            # Partial success
            create_partial_success_status(
                analysis_request,
                succeeded=succeeded_count,
                failed=len(failed_urls),
                total=len(analysis_request.post_urls),
                failed_urls=failed_urls,
                succeeded_post_ids=[str(p.id) for p in all_posts]
            )
        elif succeeded_count > 0:
            # Extract username from first post(s) for sidebar display (ChatGPT-like behavior)
            display_name = None
            if all_posts:
                # Get username from first post (most reliable)
                first_post = all_posts[0]
                # Refresh to ensure we have latest data
                first_post.refresh_from_db()
                if first_post and first_post.username:
                    display_name = first_post.username
                    logger.info(f"✅ Extracted display_name from post: {display_name}")
                else:
                    logger.warning(f"⚠️  First post {first_post.id if first_post else 'None'} has no username!")
            
            # Store display_name directly on the model (denormalized for performance)
            # This eliminates the need to query posts just to get the username for sidebar
            if display_name:
                analysis_request.display_name = display_name
                analysis_request.save(update_fields=['display_name'])
                logger.info(f"✅ Saved display_name '{display_name}' to analysis {analysis_request.id}")
            else:
                logger.warning(f"⚠️  No display_name to save for analysis {analysis_request.id}")
            
            # CRITICAL: Verify posts are linked (safety check)
            logger.info(f"🔍 [Safety] Starting post linking verification for analysis {analysis_request.id}")
            logger.info(f"📊 [Safety] all_posts count: {len(all_posts)}")
            logger.info(f"📊 [Safety] all_posts IDs: {[str(p.id) for p in all_posts]}")
            
            analysis_request.refresh_from_db()
            linked_posts_count = analysis_request.posts.count()
            logger.info(f"📊 [Safety] Current linked posts count: {linked_posts_count}")
            logger.info(f"📊 [Safety] Current linked post IDs: {[str(p.id) for p in analysis_request.posts.all()]}")
            
            if linked_posts_count != len(all_posts):
                logger.error(
                    f"⚠️  POSTS NOT PROPERLY LINKED! "
                    f"Expected {len(all_posts)} posts, but only {linked_posts_count} are linked. "
                    f"Re-linking now..."
                )
                # Re-link all posts (safety net)
                for idx, post in enumerate(all_posts):
                    logger.info(f"🔗 [Safety] Processing post {idx+1}/{len(all_posts)}: {post.id}")
                    is_already_linked = analysis_request.posts.filter(id=post.id).exists()
                    logger.info(f"📊 [Safety] Post {post.id} already linked: {is_already_linked}")
                    
                    if not is_already_linked:
                        try:
                            logger.info(f"🔗 [Safety] Adding post {post.id} to analysis_request.posts...")
                            analysis_request.posts.add(post)
                            logger.info(f"✅ [Safety] Called posts.add() for post {post.id}")
                        except Exception as e:
                            logger.error(f"❌ [Safety] Exception during posts.add() for post {post.id}: {type(e).__name__}: {str(e)}", exc_info=True)
                            # Try direct DB insert as last resort
                            logger.warning(f"🔧 [Safety] Attempting direct SQL insert for post {post.id}...")
                            try:
                                from django.db import connection
                                with connection.cursor() as cursor:
                                    cursor.execute(
                                        "INSERT INTO analysis_postanalysisrequest_posts (postanalysisrequest_id, post_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                                        [str(analysis_request.id), str(post.id)]
                                    )
                                logger.info(f"✅ [Safety] Direct DB insert completed for post {post.id}")
                            except Exception as db_e:
                                logger.error(f"❌❌ [Safety] Direct DB insert failed for post {post.id}: {type(db_e).__name__}: {str(db_e)}", exc_info=True)
                
                # Force save to ensure links are persisted
                logger.info(f"💾 [Safety] Saving analysis_request after re-linking...")
                analysis_request.save()
                logger.info(f"🔄 [Safety] Refreshing analysis_request from DB...")
                analysis_request.refresh_from_db()
                final_linked_count = analysis_request.posts.count()
                logger.info(f"📊 [Safety] Final linked posts count: {final_linked_count}")
                logger.info(f"📊 [Safety] Final linked post IDs: {[str(p.id) for p in analysis_request.posts.all()]}")
                
                if final_linked_count == len(all_posts):
                    logger.info(f"✅ [Safety] SUCCESS: Re-linked {len(all_posts)} posts to analysis {analysis_request.id}")
                else:
                    logger.error(f"❌❌ [Safety] Re-linking FAILED! Expected {len(all_posts)}, got {final_linked_count}")
                    # Last resort: try to find posts by URL and link them
                    logger.warning(f"🔍 [Safety] Attempting to find and link posts by URL...")
                    for post in all_posts:
                        if not analysis_request.posts.filter(id=post.id).exists():
                            logger.info(f"🔍 [Safety] Post {post.id} not linked, searching by URL: {post.url}")
                            # Try to find post by URL in case it was created but not linked
                            from social.models import Post
                            matching_posts = Post.objects.filter(url=post.url)
                            logger.info(f"📊 [Safety] Found {matching_posts.count()} posts with URL {post.url}")
                            for matching_post in matching_posts:
                                if not analysis_request.posts.filter(id=matching_post.id).exists():
                                    logger.info(f"🔗 [Safety] Linking matching post {matching_post.id} by URL...")
                                    try:
                                        analysis_request.posts.add(matching_post)
                                        logger.info(f"✅ [Safety] Found and linked post {matching_post.id} by URL")
                                    except Exception as e:
                                        logger.error(f"❌ [Safety] Failed to link post {matching_post.id} by URL: {type(e).__name__}: {str(e)}", exc_info=True)
            else:
                logger.info(f"✅ [Safety] All {len(all_posts)} posts are properly linked to analysis {analysis_request.id}")
            
            # Full success - CREATE STATUS IMMEDIATELY (before frame extraction)
            logger.info(f"📤 Creating social_data_fetched status for {analysis_request.id} with username: {display_name}")
            create_status(
                analysis_request,
                'social_data_fetched',
                f'Fetched {succeeded_count} posts successfully',
                metadata={
                    'posts_count': succeeded_count,
                    'post_ids': [str(p.id) for p in all_posts],
                    'platforms': list(urls_by_platform.keys()),
                    'username': display_name,  # CRITICAL: This updates the sidebar
                },
                progress_percentage=30,
                api_calls_made=total_api_calls,
                cost_estimate=cost_estimate,
            )
            logger.info(f"✅ social_data_fetched status created and sent to frontend for {analysis_request.id}")
            
            # Status: Collecting media (download, frame conversion)
            create_status(
                analysis_request,
                'collecting_media',
                'Collecting media and extracting frames...',
                metadata={
                    'posts_count': succeeded_count,
                    'platforms': list(urls_by_platform.keys()),
                },
                progress_percentage=40,
            )
            
            # Stage 2: Media Extraction & Upload
            try:
                # Extract frames for YouTube videos AFTER social_data_fetched status (so sidebar updates first)
                # But BEFORE displaying_content (so frames are ready for display)
                if analysis_request.platform == 'youtube' and all_posts:
                    from social.services.media_processor import MediaProcessor
                    from social.models import PostMedia
                    
                    logger.info(f"🎬 Starting frame extraction for {len(all_posts)} YouTube video(s)")
                    media_processor = MediaProcessor()
                    for post in all_posts:
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
            except Exception as e:
                # Media extraction error
                handle_analysis_error(
                    analysis_request,
                    error_stage=PostAnalysisRequest.ErrorStage.MEDIA_EXTRACTION,
                    exception=e,
                    failed_at_stage='social_data_fetched',
                    metadata={'posts_count': len(all_posts), 'platform': analysis_request.platform}
                )
                return {
                    'success': False,
                    'error': 'Media extraction failed',
                    'posts_fetched': len(all_posts)
                }
            
            # Note: Transcription happens inside PostSaver when saving posts
            # We'll track it at the analysis request level after all posts are saved
            # Check if any posts have videos that need transcription
            has_videos = any(
                post.media.filter(media_type='video').exists() 
                for post in all_posts
            )
            
            if has_videos:
                # Status: Transcribing audio (Whisper AI)
                create_status(
                    analysis_request,
                    'transcribing',
                    'Transcribing video audio...',
                    metadata={
                        'posts_count': succeeded_count,
                    },
                    progress_percentage=45,
                )
                # Note: Actual transcription happens in PostSaver, this is just a status update
                logger.info(f"📝 Transcription status created for {analysis_request.id}")
        else:
            # Complete failure
            create_error_status(
                analysis_request,
                'ALL_FAILED',
                'Failed to fetch any posts',
                retryable=True,
                actionable_message='Please check your URLs and try again',
                metadata={'failed_urls': failed_urls}
            )
            analysis_request.status = 'failed'
            analysis_request.save()
            return {
                'success': False,
                'error': 'All posts failed to scrape',
                'failed_urls': failed_urls
            }
        
        # Status 4: Displaying content
        # Build post previews safely (handle missing media)
        post_previews = []
        for p in all_posts[:10]:  # Limit to first 10 for preview
            thumbnail_media = p.media.filter(media_type__in=['image', 'video_thumbnail']).first()
            thumbnail = thumbnail_media.source_url if thumbnail_media and thumbnail_media.source_url else None
            
            post_previews.append({
                'id': str(p.id),
                'username': p.username,
                'platform': p.platform.name,
                'thumbnail': thumbnail,
                'caption': p.content[:100] + '...' if len(p.content) > 100 else p.content,
            })
        
        create_status(
            analysis_request,
            'displaying_content',
            'Displaying post previews...',
            metadata={
                'posts': post_previews
            },
            progress_percentage=60,
        )
        
        # Status 5: Analysing (Gemini call)
        create_status(
            analysis_request,
            'analysing',
            'PostBro is analyzing these posts...',
            metadata={
                'analysis_type': 'ai_insights',
                'posts_to_analyze': len(all_posts)
            },
            progress_percentage=70,
        )
        
        # Stage 3: Gemini Analysis
        try:
                # Get the Gemini analysis service
            from analysis.services import get_analysis_service
            from analysis.models import PostAnalysis
            from social.models import PostMedia
            
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
                
                # Get media URLs and fetch bytes from Supabase for Gemini
                # Includes both images AND video frames (all as bytes)
                media_images = []  # List of dicts: {'bytes': bytes, 'mime_type': str}
                
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
                        # Default to jpeg if unknown
                        return 'image/jpeg'
                
                for media in post.media.all():
                    # First try to use cached bytes from separate dict (stored during save process, survives refresh_from_db())
                    cached_items = None
                    if post.id in media_bytes_by_post_id and media.id in media_bytes_by_post_id[post.id]:
                        cached_items = media_bytes_by_post_id[post.id][media.id]
                    
                    if cached_items:
                        # Use cached bytes (already in memory from download/processing - no Supabase fetch needed!)
                        # For video frames: determine which video they belong to (for transcript correlation)
                        video_index = None
                        if media.media_type == 'video_frame' and media.source_url and video_url_to_index:
                            # Match frame's source_url to video's source_url to get video index
                            video_index = video_url_to_index.get(media.source_url)
                        
                        for cached_item in cached_items:
                            media_images.append({
                                'bytes': cached_item['bytes'],
                                'mime_type': cached_item['mime_type'],
                                'media_type': cached_item.get('media_type', media.media_type),
                                'video_index': video_index,  # Add video index for frames (None for images)
                                'source_url': media.source_url,  # Add source_url for debugging
                            })
                        if media.media_type == 'video_frame':
                            video_info = f" (Video {video_index})" if video_index else ""
                            logger.info(f"✅ [Analysis] Using cached frame bytes ({len(cached_items)} frames, {sum(len(item['bytes']) for item in cached_items)} total bytes){video_info}")
                        else:
                            logger.info(f"✅ [Analysis] Using cached image bytes ({len(cached_items[0]['bytes'])} bytes)")
                    else:
                        # FALLBACK COMMENTED OUT FOR TROUBLESHOOTING - Only use cached bytes
                        logger.error(f"❌ [Analysis] No cached bytes found for {media.media_type} (media.id={media.id}, post.id={post.id})")
                        logger.error(f"   Available post IDs in cache: {list(media_bytes_by_post_id.keys())}")
                        if post.id in media_bytes_by_post_id:
                            logger.error(f"   Available media IDs for post {post.id}: {list(media_bytes_by_post_id[post.id].keys())}")
                        logger.warning(f"⚠️ [Analysis] Skipping {media.media_type} - Supabase fallback disabled for troubleshooting")
                        continue
                        
                        # # FALLBACK COMMENTED OUT - Only use cached bytes for now
                        # # Fallback: fetch from Supabase URL (only if bytes not cached - should be rare)
                        # url = media.supabase_url or media.source_url
                        # if url:
                        #     try:
                        #         if media.media_type == 'video_frame':
                        #             logger.warning(f"⚠️ [Analysis] No cached bytes, fetching video frame from Supabase: {url[:100]}...")
                        #         else:
                        #             logger.warning(f"⚠️ [Analysis] No cached bytes, fetching image from Supabase: {url[:100]}...")
                        #         
                        #         response = requests.get(url, timeout=30)
                        #         response.raise_for_status()
                        #         image_bytes = response.content
                        #         
                        #         # ... rest of fallback code ...
                        #     except Exception as e:
                        #         if media.media_type == 'video_frame':
                        #             logger.warning(f"⚠️ [Analysis] Failed to fetch frame from {url}: {e}. Skipping frame.")
                        #         else:
                        #             logger.warning(f"⚠️ [Analysis] Failed to fetch image from {url}: {e}. Skipping image.")
                        #         continue
                
                logger.info(f"📎 [Analysis] Post {i+1} has {len(media_images)} media items (images + frames) as bytes")
                
                # Fetch latest comments (top 5)
                latest_comments = []
                try:
                    from social.models import PostComment
                    comment_objects = PostComment.objects.filter(post=post).order_by('-created_at')[:5]
                    for comment_obj in comment_objects:
                        comment_data = comment_obj.comment_data if isinstance(comment_obj.comment_data, dict) else {}
                        # Normalize comment structure across platforms
                        comment_dict = {
                            'text': comment_data.get('comments') or comment_data.get('text') or comment_data.get('comment', ''),
                            'username': comment_data.get('user_commenting') or comment_data.get('username') or comment_data.get('author', {}).get('username', 'Unknown'),
                            'likes': comment_data.get('likes') or comment_data.get('likeCount', 0),
                        }
                        if comment_dict['text']:  # Only add if text exists
                            latest_comments.append(comment_dict)
                    logger.info(f"💬 [Analysis] Fetched {len(latest_comments)} latest comments for post {i+1}")
                except Exception as e:
                    logger.warning(f"⚠️ [Analysis] Failed to fetch comments: {e}")
                
                # Get post data with unified metrics
                post_data = {
                    'username': post.username,
                    'caption': post.content,
                    'content': post.content,
                    'posted_at': post.posted_at.isoformat() if post.posted_at else '',
                    'metrics': post.metrics if isinstance(post.metrics, dict) else {},
                    'latest_comments': latest_comments,
                }
                
                # Get ALL video transcripts (unified structure for all platforms)
                # Critical: First analysis must be comprehensive - all video transcripts needed for follow-up chat context
                video_length = None
                transcript = None
                
                # Get ALL video media items (handle multiple videos in a single post - Instagram/Twitter can have multiple)
                # Create a mapping: video source_url -> video_index for frame-to-video correlation
                video_media_list = list(post.media.filter(media_type='video').order_by('created_at'))
                video_url_to_index = {}  # Map video source_url to its index (1-based)
                transcript_parts = []
                
                if video_media_list:
                    for idx, video_media in enumerate(video_media_list):
                        # Map video URL to index (for correlating frames with videos)
                        if video_media.source_url:
                            video_url_to_index[video_media.source_url] = idx + 1
                        
                        if video_media and video_media.transcript and video_media.transcript.strip():
                            # Skip empty or failed transcripts
                            if len(video_media_list) > 1:
                                # Multiple videos: label each transcript clearly
                                transcript_parts.append(f"[Video {idx + 1} of {len(video_media_list)} Transcript]\n{video_media.transcript.strip()}")
                            else:
                                # Single video: no label needed
                                transcript_parts.append(video_media.transcript.strip())
                    
                    if transcript_parts:
                        transcript = '\n\n'.join(transcript_parts)
                        logger.info(f"🎥 [Analysis] {analysis_request.platform} post: {len(video_media_list)} video(s), {len(transcript_parts)} transcript(s) available, combined ({len(transcript)} chars)")
                    else:
                        transcript = None
                        logger.info(f"🎥 [Analysis] {analysis_request.platform} post: {len(video_media_list)} video(s) but no transcripts available (skipped empty/failed)")
                else:
                    # Fallback to Post.transcript if no PostMedia videos (backward compatibility - YouTube only)
                    transcript_raw = post.transcript or ''
                    if transcript_raw and transcript_raw.strip():
                        transcript = transcript_raw.strip()
                        logger.info(f"🎥 [Analysis] {analysis_request.platform} post: transcript from Post ({len(transcript)} chars) - fallback")
                    else:
                        transcript = None
                        logger.info(f"🎥 [Analysis] {analysis_request.platform} post: no videos or transcripts found")
                
                # Get video_length from Post.metrics (YouTube only - this is post-level metric, not media-specific)
                if analysis_request.platform == 'youtube':
                    video_length = post.metrics.get('video_length', 0) if isinstance(post.metrics, dict) else 0
                    logger.info(f"🎥 [Analysis] YouTube post: {video_length}s video, transcript: {len(transcript) if transcript else 0} chars")
                
                # Call Gemini for analysis
                task_id = str(analysis_request.id)
                user_id = str(analysis_request.user.id) if analysis_request.user else None
                logger.info(f"🚀 [Analysis] Calling Gemini for post {i+1}/{len(all_posts)}")
                
                # Build arguments for Gemini
                analyze_kwargs = {
                    'platform': analysis_request.platform,
                    'task_id': task_id,
                    'post_data': post_data,
                    'media_images': media_images,  # Pass image + frame bytes (all media as bytes)
                    'video_length': video_length,
                    'transcript': transcript,
                    'user_id': user_id,  # Pass user_id for analytics tracking
                }
                
                ai_result = analyze_post(**analyze_kwargs)
                
                # Extract metadata
                metadata = ai_result.pop('_metadata', {})
                processing_time = metadata.get('processing_time_seconds', 0)
                usage = metadata.get('usage', {})
                
                logger.info(f"✅ [Analysis] Gemini analysis completed for post {i+1} in {processing_time:.2f}s")
                if usage:
                    # Handle Gemini usage format
                    total_tokens = usage.get('total_token_count', 'N/A')
                    prompt_tokens = usage.get('prompt_token_count', 'N/A')
                    completion_tokens = usage.get('candidates_token_count', 'N/A')
                    logger.info(f"📊 [Analysis] Tokens used: {total_tokens} "
                              f"(prompt: {prompt_tokens}, "
                              f"completion: {completion_tokens})")
                
                # Save analysis to database
                # CRITICAL: Ensure improvements is empty if post is viral
                is_viral = ai_result.get('is_viral', False)
                improvements = ai_result.get('improvements', [])
                if is_viral and improvements:
                    logger.info(f"✅ [Analysis] Post is viral - clearing improvements array")
                    improvements = []
                
                post_analysis = PostAnalysis.objects.create(
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
                    processing_time_seconds=processing_time,
                    analysis_completed=True,  # Mark as completed when first Gemini call is done
                )
                
                # CHAT-FIRST APPROACH: Create ChatSession and first messages
                # The first user message is the URL, first AI message is the analysis response
                try:
                    from .models import ChatSession, ChatMessage
                    
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
                            content=post.url,  # The URL the user submitted
                        )
                        logger.info(f"💬 [Analysis] Created first user message: {user_message.id} (URL: {post.url[:50]}...)")
                        
                        # Create first AI message (the analysis response)
                        # Use llm_response_raw if available (full markdown response), otherwise construct from structured data
                        ai_response_content = metadata.get('raw_response', '')
                        if not ai_response_content:
                            # Fallback: construct from structured data (for backward compatibility)
                            # This shouldn't happen if we're using v2, but just in case
                            logger.warning(f"⚠️ [Analysis] No raw_response in metadata, constructing from structured data")
                            ai_response_content = f"# Analysis\n\n{ai_result.get('virality_reasoning', 'Analysis completed.')}"
                        
                        ai_message = ChatMessage.objects.create(
                            session=chat_session,
                            role=ChatMessage.Role.ASSISTANT,
                            content=ai_response_content,
                            tokens_used=usage.get('total_tokens') if usage else None,  # Use 'usage' from metadata, not 'usage_info'
                        )
                        logger.info(f"💬 [Analysis] Created first AI message: {ai_message.id} ({len(ai_response_content)} chars)")
                    else:
                        logger.info(f"💬 [Analysis] Chat session already has {existing_messages.count()} messages, skipping initial message creation")
                        
                except Exception as chat_error:
                    logger.error(
                        f"❌ [Analysis] Failed to create chat session/messages for analysis_request_id={analysis_request_id_str}: {chat_error}",
                        exc_info=True,
                        extra={'analysis_request_id': analysis_request_id_str, 'post_id': str(post.id)}
                    )
                    # Don't fail the entire analysis if chat creation fails
                
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
                    f"❌ [Analysis] Failed to analyze post {i+1}/{len(all_posts)} ({post.id}) for analysis_request_id={analysis_request_id_str} "
                    f"after {post_analysis_time:.2f}s: {error_type} - {str(e)}",
                    exc_info=True,
                    extra={'analysis_request_id': analysis_request_id_str, 'post_id': str(post.id), 'post_index': i+1}
                )
                # Continue with other posts even if one fails
                continue
            
            total_analysis_time = time.time() - analysis_start_time
            logger.info(f"🎉 [Analysis] Completed Gemini analysis for {len(all_posts)} posts: "
                   f"{successful_analyses} successful, {failed_analyses} failed "
                   f"in {total_analysis_time:.2f}s total "
                   f"(avg: {total_analysis_time/len(all_posts):.2f}s per post)")
        
            # Store analysis results in analysis_request
            analysis_request.results = {
                'analyses': analysis_results,
                'total_posts': len(all_posts),
                'analyzed_posts': len(analysis_results),
            }
            analysis_request.save(update_fields=['results'])
            
            logger.info(f"✅ Completed AI analysis for {len(analysis_results)}/{len(all_posts)} posts")
        except Exception as e:
            # Gemini analysis error (if entire analysis section fails catastrophically)
            handle_analysis_error(
                analysis_request,
                error_stage=PostAnalysisRequest.ErrorStage.GEMINI_ANALYSIS,
                exception=e,
                failed_at_stage='collecting_media',
                metadata={'posts_count': len(all_posts), 'successful_analyses': successful_analyses if 'successful_analyses' in locals() else 0}
            )
            return {
                'success': False,
                'error': 'Gemini analysis failed',
                'posts_fetched': len(all_posts),
                'successful_analyses': successful_analyses if 'successful_analyses' in locals() else 0
            }
        
        # Status 6: Complete
        duration = (timezone.now() - start_time).total_seconds()
        create_status(
            analysis_request,
            'analysis_complete',
            'Analysis complete!',
            metadata={
                'posts_analyzed': len(all_posts),
                'duration_seconds': duration,
                'api_calls_made': total_api_calls,
            },
            progress_percentage=100,
            api_calls_made=total_api_calls,
            cost_estimate=cost_estimate,
        )
        
        # Update analysis request status to completed
        analysis_request.status = PostAnalysisRequest.Status.COMPLETED
        analysis_request.completed_at = timezone.now()
        analysis_request.save(update_fields=['status', 'completed_at'])
        logger.info(f"✅ Updated analysis {analysis_request.id} status to completed")
        
        logger.info(
            f"Completed analysis request {analysis_request_id}: "
            f"{succeeded_count} posts saved, {len(failed_urls)} failed"
        )
        
        return {
            'success': True,
            'posts_saved': succeeded_count,
            'posts_failed': len(failed_urls),
            'post_ids': [str(p.id) for p in all_posts],
            'failed_urls': failed_urls,
            'duration_seconds': duration,
            'api_calls_made': total_api_calls,
            'cost_estimate': float(cost_estimate),
        }
        
    except PostAnalysisRequest.DoesNotExist:
        logger.error(
            f"❌ [Analysis] Analysis request not found: analysis_request_id={analysis_request_id_str}",
            extra={'analysis_request_id': analysis_request_id_str}
        )
        return {
            'success': False,
            'error': 'Analysis request not found'
        }
    
    except ValueError as e:
        # Validation errors - don't retry
        logger.error(
            f"❌ [Analysis] Validation error for analysis_request_id={analysis_request_id_str}: {str(e)}",
            extra={'analysis_request_id': analysis_request_id_str}
        )
        try:
            analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
            create_error_status(
                analysis_request,
                'VALIDATION_ERROR',
                str(e),
                retryable=False,
                actionable_message='Please check your input and try again',
            )
        except:
            pass
        return {
            'success': False,
            'error': str(e)
        }
    
    except Exception as e:
        # Unexpected error - use handle_analysis_error for proper tracking
        try:
            analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
            # Determine error stage based on what we know
            error_stage = PostAnalysisRequest.ErrorStage.SOCIAL_COLLECTION  # Default
            failed_at_stage = 'request_created'
            
            # Try to determine stage from status history
            last_status = analysis_request.status_history.filter(is_error=False).last()
            if last_status:
                if last_status.stage in ['social_data_fetched', 'collecting_media']:
                    error_stage = PostAnalysisRequest.ErrorStage.MEDIA_EXTRACTION
                    failed_at_stage = 'social_data_fetched'
                elif last_status.stage == 'analysing':
                    error_stage = PostAnalysisRequest.ErrorStage.GEMINI_ANALYSIS
                    failed_at_stage = 'collecting_media'
            
            handle_analysis_error(
                analysis_request,
                error_stage=error_stage,
                exception=e,
                failed_at_stage=failed_at_stage,
                metadata={'unexpected_error': True}
            )
        except Exception as inner_e:
            logger.exception(
                f"❌ [Analysis] Unexpected error processing analysis_request_id={analysis_request_id_str}: {str(e)}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
            logger.error(
                f"❌ [Analysis] Also failed to handle error: {str(inner_e)}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
        
        return {
            'success': False,
            'error': str(e),
        }
