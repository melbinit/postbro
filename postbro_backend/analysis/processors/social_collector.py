"""
Social Media Collector

Handles scraping and collection of posts from different social media platforms.
Supports fast path (existing posts) and slow path (new posts) for optimization.
"""

import logging
import re
from typing import List, Dict, Tuple, Optional
from analysis.models import PostAnalysisRequest
from analysis.processors.duplicate_checker import check_existing_posts
from analysis.processors.post_linker import link_post_to_analysis
from social.scrapers import BrightDataScraper, TwitterAPIScraper
from social.services.post_saver import PostSaver
from social.models import Post

logger = logging.getLogger(__name__)


def collect_social_posts(
    analysis_request: PostAnalysisRequest,
    urls_by_platform: Dict[str, List[str]],
    media_bytes_by_post_id: Dict,
) -> Tuple[List[Post], List[str], int, set]:
    """
    Collect posts from social media platforms.
    
    Args:
        analysis_request: The analysis request
        urls_by_platform: Dictionary mapping platform to list of URLs
        media_bytes_by_post_id: Cache for media bytes (passed to PostSaver)
        
    Returns:
        Tuple of (all_posts, failed_urls, total_api_calls, fast_path_post_ids)
    """
    analysis_request_id_str = str(analysis_request.id)
    all_posts = []
    failed_urls = []
    total_api_calls = 0
    fast_path_post_ids = set()  # Track fast path posts across ALL platforms
    
    for platform, urls in urls_by_platform.items():
        try:
            logger.info(f"🔍 [DuplicateCheck] Checking {len(urls)} {platform} URLs for existing posts...")
            
            # Check for existing posts BEFORE scraping (optimization)
            existing_posts = check_existing_posts(urls, platform)
            existing_count = sum(1 for p in existing_posts.values() if p is not None)
            new_count = len(urls) - existing_count
            logger.info(f"📊 [DuplicateCheck] Found {existing_count} existing posts, {new_count} new posts")
            
            if platform == 'instagram':
                posts, failed, api_calls, fast_path_ids = _collect_instagram_posts(
                    analysis_request, urls, existing_posts, media_bytes_by_post_id, analysis_request_id_str
                )
                all_posts.extend(posts)
                failed_urls.extend(failed)
                total_api_calls += api_calls
                fast_path_post_ids.update(fast_path_ids)
                
            elif platform == 'youtube':
                posts, failed, api_calls, fast_path_ids = _collect_youtube_posts(
                    analysis_request, urls, existing_posts, media_bytes_by_post_id, analysis_request_id_str
                )
                all_posts.extend(posts)
                failed_urls.extend(failed)
                total_api_calls += api_calls
                fast_path_post_ids.update(fast_path_ids)
                
            elif platform == 'x':
                posts, failed, api_calls, fast_path_ids = _collect_twitter_posts(
                    analysis_request, urls, existing_posts, media_bytes_by_post_id, analysis_request_id_str
                )
                all_posts.extend(posts)
                failed_urls.extend(failed)
                total_api_calls += api_calls
                fast_path_post_ids.update(fast_path_ids)
                
            else:
                logger.error(f"Unsupported platform: {platform}")
                failed_urls.extend(urls)
                
        except Exception as e:
            logger.error(
                f"❌ [SocialCollector] Platform-level error for {platform}: {e}",
                exc_info=True,
                extra={'analysis_request_id': analysis_request_id_str, 'platform': platform}
            )
            failed_urls.extend(urls)
    
    return all_posts, failed_urls, total_api_calls, fast_path_post_ids


def _collect_instagram_posts(
    analysis_request: PostAnalysisRequest,
    urls: List[str],
    existing_posts: Dict[str, Optional[Post]],
    media_bytes_by_post_id: Dict,
    analysis_request_id_str: str,
) -> Tuple[List[Post], List[str], int, set]:
    """Collect Instagram posts (fast path + slow path)."""
    scraper = BrightDataScraper()
    saver = PostSaver(analysis_request, media_bytes_cache=media_bytes_by_post_id)
    
    all_posts = []
    failed_urls = []
    api_calls = 0
    fast_path_post_ids = set()
    
    # Clean URLs - remove zero-width characters that can come from copy-paste
    def clean_url(url: str) -> str:
        """Remove zero-width chars (ZWSP, ZWNJ, ZWJ, BOM, WJ) and trim"""
        return re.sub(r'[\u200b-\u200d\uFEFF\u2060]', '', url).strip()
    
    for url in urls:
        # Clean the URL before processing
        url = clean_url(url)
        existing_post = existing_posts.get(url)
        
        if existing_post:
            # FAST PATH: Post exists - update metrics only, reuse media
            logger.info(f"⚡ [FastPath] Post exists for {url}, updating metrics and reusing media...")
            try:
                fresh_data = scraper.scrape_instagram_post(url, analysis_request_id=analysis_request_id_str)
                api_calls += 1
                
                if fresh_data.get('success'):
                    saver.update_existing_post_metrics(existing_post, fresh_data, 'instagram')
                    saver.reuse_existing_media(existing_post)
                    
                    if link_post_to_analysis(analysis_request, existing_post, 'instagram'):
                        all_posts.append(existing_post)
                        fast_path_post_ids.add(existing_post.id)
                        logger.info(f"✅ [FastPath] Successfully updated existing post {existing_post.id}")
                    else:
                        logger.warning(f"⚠️ [FastPath] Post updated but linking failed for {existing_post.id}")
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
                # TEMPORARY: Removed analysis_request_id for retry testing
                results = scraper.scrape_instagram_posts([url])
                api_calls += 1
                
                for result in results:
                    if result.get('error') or not result.get('success', True):
                        failed_urls.append(result.get('url', 'unknown'))
                        logger.error(
                            f"❌ [Analysis] Failed to scrape Instagram post: {result.get('error')}",
                            extra={'analysis_request_id': analysis_request_id_str, 'url': result.get('url', 'unknown'), 'platform': 'instagram'}
                        )
                    else:
                        try:
                            post = saver.save_instagram_post(result)
                            all_posts.append(post)
                            
                            # Link post to analysis request
                            if link_post_to_analysis(analysis_request, post, 'instagram'):
                                # Verify media uploads
                                media_without_url = post.media.filter(
                                    media_type__in=['image', 'video_thumbnail'],
                                    supabase_url__isnull=True
                                ).exclude(uploaded_to_supabase=True)
                                
                                if media_without_url.exists():
                                    logger.warning(f"Post {post.id} has {media_without_url.count()} media items without supabase_url")
                            else:
                                logger.error(f"❌ [Instagram] Failed to link post {post.id}")
                                
                        except Exception as e:
                            logger.error(
                                f"❌ [Analysis] Failed to save Instagram post: {e}",
                                exc_info=True,
                                extra={'analysis_request_id': analysis_request_id_str, 'platform': 'instagram', 'url': result.get('url', 'unknown')}
                            )
                            failed_urls.append(result.get('url', 'unknown'))
            except Exception as e:
                logger.error(
                    f"❌ [Analysis] Failed to scrape Instagram post {url}: {e}",
                    exc_info=True,
                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'instagram'}
                )
                failed_urls.append(url)
    
    return all_posts, failed_urls, api_calls, fast_path_post_ids


def _collect_youtube_posts(
    analysis_request: PostAnalysisRequest,
    urls: List[str],
    existing_posts: Dict[str, Optional[Post]],
    media_bytes_by_post_id: Dict,
    analysis_request_id_str: str,
) -> Tuple[List[Post], List[str], int, set]:
    """Collect YouTube posts (fast path + slow path)."""
    scraper = BrightDataScraper()
    saver = PostSaver(analysis_request, media_bytes_cache=media_bytes_by_post_id)
    
    all_posts = []
    failed_urls = []
    api_calls = 0
    fast_path_post_ids = set()
    
    for url in urls:
        existing_post = existing_posts.get(url)
        
        if existing_post:
            # FAST PATH: Post exists - update metrics only, reuse media
            logger.info(f"⚡ [FastPath] Post exists for {url}, updating metrics and reusing media...")
            try:
                fresh_data = scraper.scrape_youtube_video(url, analysis_request_id=analysis_request_id_str)
                api_calls += 1
                
                if fresh_data.get('success'):
                    saver.update_existing_post_metrics(existing_post, fresh_data, 'youtube')
                    saver.reuse_existing_media(existing_post)
                    
                    if link_post_to_analysis(analysis_request, existing_post, 'youtube'):
                        all_posts.append(existing_post)
                        fast_path_post_ids.add(existing_post.id)
                        logger.info(f"✅ [FastPath] Successfully updated existing post {existing_post.id}")
                    else:
                        logger.warning(f"⚠️ [FastPath] Post updated but linking failed for {existing_post.id}")
                else:
                    logger.error(f"❌ [FastPath] Failed to fetch fresh metrics for {url}: {fresh_data.get('error')}")
                    failed_urls.append(url)
            except Exception as e:
                logger.error(
                    f"❌ [Analysis] FastPath error updating existing YouTube post {url}: {e}",
                    exc_info=True,
                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'youtube'}
                )
                failed_urls.append(url)
        else:
            # SLOW PATH: New post - full processing
            logger.info(f"🔄 [FullPath] New post, full processing for {url}")
            try:
                results = scraper.scrape_youtube_videos([url], analysis_request_id=analysis_request_id_str)
                api_calls += 1
                
                for i, result in enumerate(results):
                    logger.info(f"📊 [YouTube] Processing result {i+1}/{len(results)}")
                    if result.get('error') or not result.get('success', True):
                        error_msg = result.get('error', 'Unknown error')
                        result_url = result.get('url', url)
                        failed_urls.append(result_url)
                        logger.error(
                            f"❌ [Analysis] Failed to scrape YouTube video {result_url}: {error_msg}",
                            extra={'analysis_request_id': analysis_request_id_str, 'url': result_url, 'platform': 'youtube'}
                        )
                    else:
                        try:
                            logger.info(f"💾 [YouTube] Saving video to database...")
                            post = saver.save_youtube_video(result)
                            logger.info(f"✅ [YouTube] Video saved: post_id={post.id}, video_id={post.platform_post_id}")
                            all_posts.append(post)
                            
                            # Link post to analysis request
                            if link_post_to_analysis(analysis_request, post, 'youtube'):
                                logger.info(f"🎉 [YouTube] Successfully processed video: {result.get('url', 'unknown')}")
                            else:
                                logger.error(f"❌ [YouTube] Failed to link post {post.id}")
                                
                        except Exception as e:
                            error_type = type(e).__name__
                            logger.error(
                                f"❌ [Analysis] Failed to save YouTube video: {error_type} - {str(e)}",
                                exc_info=True,
                                extra={'analysis_request_id': analysis_request_id_str, 'platform': 'youtube', 'url': result.get('url', 'unknown')}
                            )
                            failed_urls.append(result.get('url', 'unknown'))
            except Exception as e:
                logger.error(
                    f"❌ [Analysis] Failed to scrape YouTube video {url}: {e}",
                    exc_info=True,
                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'youtube'}
                )
                failed_urls.append(url)
    
    return all_posts, failed_urls, api_calls, fast_path_post_ids


def _collect_twitter_posts(
    analysis_request: PostAnalysisRequest,
    urls: List[str],
    existing_posts: Dict[str, Optional[Post]],
    media_bytes_by_post_id: Dict,
    analysis_request_id_str: str,
) -> Tuple[List[Post], List[str], int, set]:
    """Collect Twitter/X posts (fast path + slow path)."""
    scraper = TwitterAPIScraper()
    saver = PostSaver(analysis_request, media_bytes_cache=media_bytes_by_post_id)
    
    all_posts = []
    failed_urls = []
    api_calls = 0
    fast_path_post_ids = set()
    
    for url in urls:
        existing_post = existing_posts.get(url)
        
        if existing_post:
            # FAST PATH: Post exists - update metrics only, reuse media
            logger.info(f"⚡ [FastPath] Post exists for {url}, updating metrics and reusing media...")
            try:
                fresh_data = scraper.scrape_tweet(url, analysis_request_id=analysis_request_id_str)
                api_calls += 1
                
                if fresh_data.get('success'):
                    saver.update_existing_post_metrics(existing_post, fresh_data, 'x')
                    saver.reuse_existing_media(existing_post)
                    
                    if link_post_to_analysis(analysis_request, existing_post, 'x'):
                        all_posts.append(existing_post)
                        fast_path_post_ids.add(existing_post.id)
                        logger.info(f"✅ [FastPath] Successfully updated existing post {existing_post.id}")
                    else:
                        logger.warning(f"⚠️ [FastPath] Post updated but linking failed for {existing_post.id}")
                else:
                    logger.error(f"❌ [FastPath] Failed to fetch fresh metrics for {url}: {fresh_data.get('error')}")
                    failed_urls.append(url)
            except Exception as e:
                logger.error(
                    f"❌ [Analysis] FastPath error updating existing Twitter/X post {url}: {e}",
                    exc_info=True,
                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'x'}
                )
                failed_urls.append(url)
        else:
            # SLOW PATH: New post - full processing
            logger.info(f"🔄 [FullPath] New post, full processing for {url}")
            try:
                results = scraper.scrape_tweets([url], analysis_request_id=analysis_request_id_str)
                api_calls += 1
                
                for result in results:
                    if result.get('error') or not result.get('success', True):
                        failed_urls.append(result.get('url', 'unknown'))
                        logger.error(
                            f"❌ [Analysis] Failed to scrape Twitter/X tweet: {result.get('error')}",
                            extra={'analysis_request_id': analysis_request_id_str, 'url': result.get('url', 'unknown'), 'platform': 'x'}
                        )
                    else:
                        try:
                            post = saver.save_twitter_tweet(result)
                            all_posts.append(post)
                            
                            # Link post to analysis request
                            if link_post_to_analysis(analysis_request, post, 'x'):
                                logger.info(f"✅ Linked post {post.id} to analysis {analysis_request.id}")
                            else:
                                logger.error(f"❌ [Twitter] Failed to link post {post.id}")
                                
                        except Exception as e:
                            logger.error(
                                f"❌ [Analysis] Failed to save Twitter/X tweet: {e}",
                                exc_info=True,
                                extra={'analysis_request_id': analysis_request_id_str, 'platform': 'x', 'url': result.get('url', 'unknown')}
                            )
                            failed_urls.append(result.get('url', 'unknown'))
            except Exception as e:
                logger.error(
                    f"❌ [Analysis] Failed to scrape Twitter/X tweet {url}: {e}",
                    exc_info=True,
                    extra={'analysis_request_id': analysis_request_id_str, 'url': url, 'platform': 'x'}
                )
                failed_urls.append(url)
    
    return all_posts, failed_urls, api_calls, fast_path_post_ids

