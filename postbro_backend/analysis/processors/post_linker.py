"""
Post Linker

Centralized logic for linking posts to analysis requests.
Handles verification, retries, and fallback mechanisms.
"""

import logging
from typing import List
from analysis.models import PostAnalysisRequest
from social.models import Post

logger = logging.getLogger(__name__)


def link_post_to_analysis(analysis_request: PostAnalysisRequest, post: Post, platform: str = None) -> bool:
    """
    Link a post to an analysis request with verification and retry logic.
    
    Args:
        analysis_request: The analysis request to link to
        post: The post to link
        platform: Platform name for logging (optional)
        
    Returns:
        bool: True if successfully linked, False otherwise
    """
    platform_label = f"[{platform.upper()}]" if platform else ""
    
    # Check if already linked
    if analysis_request.posts.filter(id=post.id).exists():
        logger.info(f"✅ {platform_label} Post {post.id} already linked to analysis {analysis_request.id}")
        return True
    
    logger.info(f"🔗 {platform_label} Linking post {post.id} to analysis {analysis_request.id}")
    
    try:
        # First attempt: standard Django ORM
        analysis_request.posts.add(post)
        analysis_request.save()
        analysis_request.refresh_from_db()
        
        # Verify the link was created
        if analysis_request.posts.filter(id=post.id).exists():
            logger.info(f"✅ {platform_label} Linked post {post.id} to analysis {analysis_request.id}")
            return True
        else:
            logger.warning(f"⚠️ {platform_label} Link verification failed - retrying...")
            
            # Retry: remove and re-add
            analysis_request.posts.remove(post)  # Safe even if not exists
            analysis_request.posts.add(post)
            analysis_request.save()
            analysis_request.refresh_from_db()
            
            if analysis_request.posts.filter(id=post.id).exists():
                logger.info(f"✅ {platform_label} Retry successful: Linked post {post.id}")
                return True
            else:
                logger.error(f"❌❌ {platform_label} Retry FAILED: Post {post.id} still not linked")
                # Fallback to direct DB insert
                return _link_post_direct_db(analysis_request, post, platform_label)
                
    except Exception as link_error:
        logger.error(
            f"❌ {platform_label} Failed to link post {post.id} to analysis {analysis_request.id}: {link_error}",
            exc_info=True
        )
        # Fallback to direct DB insert
        return _link_post_direct_db(analysis_request, post, platform_label)


def _link_post_direct_db(analysis_request: PostAnalysisRequest, post: Post, platform_label: str) -> bool:
    """
    Direct database insert as last resort fallback.
    
    Args:
        analysis_request: The analysis request
        post: The post to link
        platform_label: Platform label for logging
        
    Returns:
        bool: True if successfully linked, False otherwise
    """
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO analysis_postanalysisrequest_posts (postanalysisrequest_id, post_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                [str(analysis_request.id), str(post.id)]
            )
        analysis_request.refresh_from_db()
        
        if analysis_request.posts.filter(id=post.id).exists():
            logger.info(f"✅ {platform_label} Direct DB insert successful: Linked post {post.id}")
            return True
        else:
            logger.error(f"❌❌❌ {platform_label} Direct DB insert also FAILED for post {post.id}")
            return False
    except Exception as db_error:
        logger.error(f"❌ {platform_label} Direct DB insert error: {db_error}", exc_info=True)
        return False


def verify_and_relink_posts(analysis_request: PostAnalysisRequest, expected_posts: List[Post]) -> int:
    """
    Verify all posts are linked and re-link any missing ones.
    
    Args:
        analysis_request: The analysis request
        expected_posts: List of posts that should be linked
        
    Returns:
        int: Number of posts successfully linked/verified
    """
    logger.info(f"🔍 [Verification] Verifying {len(expected_posts)} post(s) are linked to analysis {analysis_request.id}")
    
    analysis_request.refresh_from_db()
    linked_count_before = analysis_request.posts.count()
    
    linked_count = 0
    for post in expected_posts:
        if analysis_request.posts.filter(id=post.id).exists():
            linked_count += 1
        else:
            logger.warning(f"⚠️ [Verification] Post {post.id} is NOT linked - re-linking now...")
            if link_post_to_analysis(analysis_request, post):
                linked_count += 1
    
    analysis_request.save()
    analysis_request.refresh_from_db()
    linked_count_after = analysis_request.posts.count()
    
    logger.info(f"📊 [Verification] Linked posts: {linked_count_before} -> {linked_count_after} (expected: {len(expected_posts)})")
    
    if linked_count_after != len(expected_posts):
        logger.error(f"❌ [Verification] MISMATCH: Expected {len(expected_posts)} linked posts, but only {linked_count_after} are linked!")
    
    return linked_count
