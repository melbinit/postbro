"""
Duplicate Post Checker

Checks which URLs already have posts in the database.
This enables fast path optimization (skip media processing, only update metrics).
"""

import logging
import re
from typing import List, Dict, Optional
from social.models import Post, Platform
from social.services.url_parser import extract_post_id

logger = logging.getLogger(__name__)


def _normalize_string(value: str) -> str:
    """Remove zero-width chars and trim whitespace."""
    if not value:
        return ''
    return re.sub(r'[\u200b-\u200d\uFEFF\u2060]', '', value).strip()


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
    logger.info(f"🔍 [DuplicateCheck] Starting check for {len(urls)} URLs on platform '{platform}'")
    
    try:
        # Map analysis request platform to social Platform model
        platform_name_map = {
            'instagram': 'instagram',
            'x': 'twitter',  # Twitter model uses 'twitter', not 'x'
            'youtube': 'youtube',
        }
        platform_name = platform_name_map.get(platform)
        
        if not platform_name:
            logger.warning(f"⚠️ [DuplicateCheck] Unknown platform '{platform}' for duplicate check")
            return {url: None for url in urls}
        
        platform_obj = Platform.objects.get(name=platform_name)
        
        for url in urls:
            clean_url = _normalize_string(url)
            post_id = extract_post_id(clean_url, platform)
            post_id = _normalize_string(post_id)
            if not post_id:
                existing_posts[url] = None
                logger.warning(f"⚠️ [DuplicateCheck] Could not extract post_id from URL: {url} (platform: {platform})")
                continue
            
            try:
                post = Post.objects.get(
                    platform=platform_obj,
                    platform_post_id__iexact=post_id  # case-insensitive, normalized
                )
                existing_posts[url] = post
                logger.info(f"✅ [DuplicateCheck] Found existing post for {url}: {post.id} (@{post.username})")
            except Post.DoesNotExist:
                existing_posts[url] = None
                logger.info(f"🆕 [DuplicateCheck] New post for {url} (post_id: {post_id})")
            except Post.MultipleObjectsReturned:
                # Shouldn't happen due to unique_together, but handle gracefully
                post = Post.objects.filter(
                    platform=platform_obj,
                    platform_post_id=post_id
                ).first()
                existing_posts[url] = post
                logger.warning(f"⚠️ [DuplicateCheck] Multiple posts found for {url}, using first: {post.id if post else None}")
                
    except Platform.DoesNotExist:
        logger.error(f"❌ [DuplicateCheck] Platform '{platform_name}' not found in database")
        return {url: None for url in urls}
    except Exception as e:
        logger.error(f"❌ [DuplicateCheck] Error checking existing posts (platform={platform}, urls={len(urls)}): {type(e).__name__}: {str(e)}", exc_info=True)
        return {url: None for url in urls}
    
    existing_count = sum(1 for p in existing_posts.values() if p is not None)
    logger.info(f"📊 [DuplicateCheck] Check complete: {existing_count} existing, {len(urls) - existing_count} new")
    return existing_posts

