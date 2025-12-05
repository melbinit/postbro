"""
Shared Prompt Utilities for AI Analysis Services

This module provides shared functions for building prompts for Gemini service.
"""

import os
import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def load_prompt_template() -> str:
    """
    Load the Gemini prompt template.
    
    Returns:
        Prompt template content as string
    """
    # Get the analysis app directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Use v2 prompt for chat-first approach (conversational markdown output)
    prompt_filename = 'v2.txt'
    
    prompt_path = os.path.join(current_dir, '..', 'prompts', prompt_filename)
    prompt_path = os.path.abspath(prompt_path)
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"✅ Loaded prompt template from {prompt_path} ({len(content)} chars)")
            return content
    except FileNotFoundError:
        logger.error(f"❌ Prompt template not found at {prompt_path}")
        return ""
    except Exception as e:
        logger.error(f"❌ Error loading prompt template: {e}")
        return ""


def get_system_prompt() -> str:
    """
    Extract system prompt from template
    
    Returns:
        System prompt string
    """
    template = load_prompt_template()
    
    # Extract system prompt section (before "🟩 USER PROMPT")
    system_prompt_start = template.find("🟦 SYSTEM PROMPT")
    user_prompt_start = template.find("🟩 USER PROMPT")
    
    if system_prompt_start == -1 or user_prompt_start == -1:
        logger.error("Could not find system prompt section in template")
        return ""
    
    system_prompt = template[system_prompt_start:user_prompt_start]
    # Remove the header line
    system_prompt = '\n'.join(system_prompt.split('\n')[1:]).strip()
    
    return system_prompt


def build_user_metrics_section(
    platform: str,
    username: str,
    metrics: Dict[str, Any],
) -> str:
    """
    Build unified user metrics section for prompt.
    Only includes fields that exist (omits missing data).
    
    Args:
        platform: Platform name (instagram, x, youtube)
        username: Post author username
        metrics: Post.metrics JSONField dict (can be None or empty)
    
    Returns:
        Formatted user metrics string
    """
    if not metrics or not isinstance(metrics, dict):
        return f"Username: @{username}"
    
    lines = []
    
    # Username (always present)
    lines.append(f"Username: @{username}")
    
    # Platform-specific user metrics
    if platform == 'instagram':
        if metrics.get('followers'):
            lines.append(f"Followers: {metrics['followers']:,}")
        if metrics.get('following') is not None:
            lines.append(f"Following: {metrics['following']:,}")
        if metrics.get('posts_count'):
            lines.append(f"Posts Count: {metrics['posts_count']:,}")
        if metrics.get('is_verified'):
            lines.append("Verified: Yes")
        # Bio/description not typically in post metrics for Instagram
    
    elif platform == 'twitter' or platform == 'x':
        author = metrics.get('author', {})
        if isinstance(author, dict):
            # Twitter uses 'followers' not 'followersCount'
            if author.get('followers'):
                lines.append(f"Followers: {author['followers']:,}")
            if author.get('following') is not None:
                lines.append(f"Following: {author['following']:,}")
            if author.get('statusesCount'):
                lines.append(f"Posts Count: {author['statusesCount']:,}")
            if author.get('isVerified') or author.get('isBlueVerified'):
                lines.append("Verified: Yes")
            if author.get('description'):
                lines.append(f"Bio: {author['description']}")
            if author.get('location'):
                lines.append(f"Location: {author['location']}")
    
    elif platform == 'youtube':
        # YouTube stores subscriber count directly in metrics, not in channel sub-object
        if metrics.get('subscribers'):
            lines.append(f"Subscribers: {metrics['subscribers']:,}")
        if metrics.get('verified'):
            lines.append("Verified: Yes")
        # Description is stored in post.content for YouTube, not in metrics
    
    return '\n'.join(lines) if lines else "Username: @{username}"


def build_post_metrics_section(
    platform: str,
    metrics: Dict[str, Any],
    caption: str,
    posted_at: str,
    latest_comments: List[Dict[str, Any]],
) -> str:
    """
    Build unified post metrics section for prompt.
    Only includes fields that exist (omits missing data).
    
    Args:
        platform: Platform name (instagram, x, youtube)
        metrics: Post.metrics JSONField dict (can be None or empty)
        caption: Post caption/content
        posted_at: Post timestamp
        latest_comments: List of comment dicts with username, text, likes
    
    Returns:
        Formatted post metrics string
    """
    if not metrics or not isinstance(metrics, dict):
        metrics = {}
    
    lines = []
    
    # Likes
    likes = metrics.get('likes') or metrics.get('likeCount')
    if likes:
        lines.append(f"Likes: {likes:,}")
    
    # Views/Impressions
    views = metrics.get('views') or metrics.get('viewCount') or metrics.get('impressions')
    if views:
        lines.append(f"Views: {views:,}")
    
    # Video Plays (YouTube specific)
    if platform == 'youtube':
        video_plays = metrics.get('video_plays') or metrics.get('playCount')
        if video_plays:
            lines.append(f"Video Plays: {video_plays:,}")
    
    # Comments
    comments = metrics.get('comments') or metrics.get('commentCount')
    if comments:
        lines.append(f"Comments: {comments:,}")
    
    # Replies (Twitter/X)
    if platform == 'twitter' or platform == 'x':
        replies = metrics.get('replies') or metrics.get('replyCount')
        if replies:
            lines.append(f"Replies: {replies:,}")
        retweets = metrics.get('retweets') or metrics.get('retweetCount')
        if retweets:
            lines.append(f"Retweets: {retweets:,}")
        quotes = metrics.get('quotes') or metrics.get('quoteCount')
        if quotes:
            lines.append(f"Quotes: {quotes:,}")
        bookmarks = metrics.get('bookmarks') or metrics.get('bookmarkCount')
        if bookmarks:
            lines.append(f"Bookmarks: {bookmarks:,}")
    
    # Media Count
    media_count = metrics.get('media_count') or metrics.get('mediaCount')
    if media_count:
        lines.append(f"Media Count: {media_count}")
    
    # Caption/Description/Tweet Text
    if caption:
        lines.append(f"Caption/Description/Tweet Text: {caption}")
    
    # Posted At
    if posted_at:
        lines.append(f"Posted At: {posted_at}")
    
    # Latest Comments (Top 5)
    if latest_comments:
        lines.append("Latest Comments (Top 5):")
        for i, comment in enumerate(latest_comments[:5], 1):
            comment_text = comment.get('text') or comment.get('comments') or comment.get('comment', '')
            comment_username = comment.get('username') or comment.get('user_commenting') or comment.get('author', {}).get('username', 'Unknown')
            comment_likes = comment.get('likes') or comment.get('likeCount', 0)
            
            if comment_text:
                if comment_likes:
                    lines.append(f"  {i}. @{comment_username}: \"{comment_text}\" ({comment_likes} likes)")
                else:
                    lines.append(f"  {i}. @{comment_username}: \"{comment_text}\"")
    
    return '\n'.join(lines) if lines else "No metrics available"


def build_user_prompt(
    platform: str,
    task_id: str,
    username: str,
    caption: str,
    posted_at: str,
    metrics: Dict[str, Any],
    latest_comments: List[Dict[str, Any]],
    media_urls: List[str],
    video_length: Optional[int] = None,
    transcript: Optional[str] = None,
) -> str:
    """
    Build the user prompt from template with actual post data
    
    Args:
        platform: Platform name (instagram, x, youtube)
        task_id: Task ID for this analysis
        username: Post author username
        caption: Post caption/content
        posted_at: Post timestamp
        metrics: Post.metrics JSONField dict
        latest_comments: List of comment dicts with username, text, likes
        media_urls: List of media URLs (note: images + frames are sent as bytes, not URLs)
        video_length: Video length in seconds (for YouTube)
        transcript: Video transcript (for YouTube)
    
    Returns:
        Formatted user prompt string
    """
    template = load_prompt_template()
    
    # Extract user prompt section (after "🟩 USER PROMPT")
    user_prompt_start = template.find("🟩 USER PROMPT")
    if user_prompt_start == -1:
        logger.error("Could not find user prompt section in template")
        return ""
    
    user_prompt = template[user_prompt_start:].split("## INSTRUCTIONS")[0]
    
    # Build unified metrics sections
    user_metrics = build_user_metrics_section(platform, username, metrics)
    post_metrics = build_post_metrics_section(platform, metrics, caption, posted_at, latest_comments)
    
    # Handle conditional sections (simple string replacement - not Django templates)
    # Remove {{#if youtube}} sections if not YouTube
    if platform != 'youtube':
        # Remove YouTube-specific section
        user_prompt = re.sub(
            r'\{\{#if youtube\}\}.*?\{\{/if\}\}',
            '',
            user_prompt,
            flags=re.DOTALL
        )
    else:
        # Replace {{#if youtube}}...{{/if}} with content (remove conditionals)
        youtube_match = re.search(
            r'\{\{#if youtube\}\}(.*?)\{\{/if\}\}',
            user_prompt,
            flags=re.DOTALL
        )
        if youtube_match:
            youtube_content = youtube_match.group(1)
            user_prompt = user_prompt.replace(youtube_match.group(0), youtube_content)
    
    # Handle transcript conditional section
    if transcript and transcript.strip():
        # Replace {{#if transcript}}...{{/if}} with actual content
        transcript_section_match = re.search(
            r'\{\{#if transcript\}\}(.*?)\{\{/if\}\}',
            user_prompt,
            flags=re.DOTALL
        )
        if transcript_section_match:
            transcript_template = transcript_section_match.group(1)
            # Replace {{transcript}} inside the section
            transcript_content = transcript_template.replace('{{transcript}}', transcript.strip())
            user_prompt = user_prompt.replace(transcript_section_match.group(0), transcript_content)
    else:
        # Remove transcript section if no transcript
        user_prompt = re.sub(
            r'\{\{#if transcript\}\}.*?\{\{/if\}\}',
            '',
            user_prompt,
            flags=re.DOTALL
        )
    
    # Replace template variables
    replacements = {
        '{{platform}}': platform,
        '{{task_id}}': task_id,
        '{{requested_datetime}}': datetime.now().isoformat(),
        '{{username}}': username or 'Unknown',
        '{{user_metrics}}': user_metrics,
        '{{post_metrics}}': post_metrics,
        '{{caption}}': caption or 'No caption',
        '{{posted_at}}': posted_at or 'Unknown',
        '{{media_urls}}': '\n'.join(media_urls) if media_urls else 'No media',
        '{{video_length}}': str(video_length) if video_length else 'N/A',
        '{{frames}}': 'Video frames included in media (sent as bytes)',  # Frames now sent as bytes in media_images
    }
    
    for key, value in replacements.items():
        user_prompt = user_prompt.replace(key, str(value))
    
    return user_prompt



This module provides shared functions for building prompts for Gemini service.
"""

import os
import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


def load_prompt_template() -> str:
    """
    Load the Gemini prompt template.
    
    Returns:
        Prompt template content as string
    """
    # Get the analysis app directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Use v2 prompt for chat-first approach (conversational markdown output)
    prompt_filename = 'v2.txt'
    
    prompt_path = os.path.join(current_dir, '..', 'prompts', prompt_filename)
    prompt_path = os.path.abspath(prompt_path)
    
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"✅ Loaded prompt template from {prompt_path} ({len(content)} chars)")
            return content
    except FileNotFoundError:
        logger.error(f"❌ Prompt template not found at {prompt_path}")
        return ""
    except Exception as e:
        logger.error(f"❌ Error loading prompt template: {e}")
        return ""


def get_system_prompt() -> str:
    """
    Extract system prompt from template
    
    Returns:
        System prompt string
    """
    template = load_prompt_template()
    
    # Extract system prompt section (before "🟩 USER PROMPT")
    system_prompt_start = template.find("🟦 SYSTEM PROMPT")
    user_prompt_start = template.find("🟩 USER PROMPT")
    
    if system_prompt_start == -1 or user_prompt_start == -1:
        logger.error("Could not find system prompt section in template")
        return ""
    
    system_prompt = template[system_prompt_start:user_prompt_start]
    # Remove the header line
    system_prompt = '\n'.join(system_prompt.split('\n')[1:]).strip()
    
    return system_prompt


def build_user_metrics_section(
    platform: str,
    username: str,
    metrics: Dict[str, Any],
) -> str:
    """
    Build unified user metrics section for prompt.
    Only includes fields that exist (omits missing data).
    
    Args:
        platform: Platform name (instagram, x, youtube)
        username: Post author username
        metrics: Post.metrics JSONField dict (can be None or empty)
    
    Returns:
        Formatted user metrics string
    """
    if not metrics or not isinstance(metrics, dict):
        return f"Username: @{username}"
    
    lines = []
    
    # Username (always present)
    lines.append(f"Username: @{username}")
    
    # Platform-specific user metrics
    if platform == 'instagram':
        if metrics.get('followers'):
            lines.append(f"Followers: {metrics['followers']:,}")
        if metrics.get('following') is not None:
            lines.append(f"Following: {metrics['following']:,}")
        if metrics.get('posts_count'):
            lines.append(f"Posts Count: {metrics['posts_count']:,}")
        if metrics.get('is_verified'):
            lines.append("Verified: Yes")
        # Bio/description not typically in post metrics for Instagram
    
    elif platform == 'twitter' or platform == 'x':
        author = metrics.get('author', {})
        if isinstance(author, dict):
            # Twitter uses 'followers' not 'followersCount'
            if author.get('followers'):
                lines.append(f"Followers: {author['followers']:,}")
            if author.get('following') is not None:
                lines.append(f"Following: {author['following']:,}")
            if author.get('statusesCount'):
                lines.append(f"Posts Count: {author['statusesCount']:,}")
            if author.get('isVerified') or author.get('isBlueVerified'):
                lines.append("Verified: Yes")
            if author.get('description'):
                lines.append(f"Bio: {author['description']}")
            if author.get('location'):
                lines.append(f"Location: {author['location']}")
    
    elif platform == 'youtube':
        # YouTube stores subscriber count directly in metrics, not in channel sub-object
        if metrics.get('subscribers'):
            lines.append(f"Subscribers: {metrics['subscribers']:,}")
        if metrics.get('verified'):
            lines.append("Verified: Yes")
        # Description is stored in post.content for YouTube, not in metrics
    
    return '\n'.join(lines) if lines else "Username: @{username}"


def build_post_metrics_section(
    platform: str,
    metrics: Dict[str, Any],
    caption: str,
    posted_at: str,
    latest_comments: List[Dict[str, Any]],
) -> str:
    """
    Build unified post metrics section for prompt.
    Only includes fields that exist (omits missing data).
    
    Args:
        platform: Platform name (instagram, x, youtube)
        metrics: Post.metrics JSONField dict (can be None or empty)
        caption: Post caption/content
        posted_at: Post timestamp
        latest_comments: List of comment dicts with username, text, likes
    
    Returns:
        Formatted post metrics string
    """
    if not metrics or not isinstance(metrics, dict):
        metrics = {}
    
    lines = []
    
    # Likes
    likes = metrics.get('likes') or metrics.get('likeCount')
    if likes:
        lines.append(f"Likes: {likes:,}")
    
    # Views/Impressions
    views = metrics.get('views') or metrics.get('viewCount') or metrics.get('impressions')
    if views:
        lines.append(f"Views: {views:,}")
    
    # Video Plays (YouTube specific)
    if platform == 'youtube':
        video_plays = metrics.get('video_plays') or metrics.get('playCount')
        if video_plays:
            lines.append(f"Video Plays: {video_plays:,}")
    
    # Comments
    comments = metrics.get('comments') or metrics.get('commentCount')
    if comments:
        lines.append(f"Comments: {comments:,}")
    
    # Replies (Twitter/X)
    if platform == 'twitter' or platform == 'x':
        replies = metrics.get('replies') or metrics.get('replyCount')
        if replies:
            lines.append(f"Replies: {replies:,}")
        retweets = metrics.get('retweets') or metrics.get('retweetCount')
        if retweets:
            lines.append(f"Retweets: {retweets:,}")
        quotes = metrics.get('quotes') or metrics.get('quoteCount')
        if quotes:
            lines.append(f"Quotes: {quotes:,}")
        bookmarks = metrics.get('bookmarks') or metrics.get('bookmarkCount')
        if bookmarks:
            lines.append(f"Bookmarks: {bookmarks:,}")
    
    # Media Count
    media_count = metrics.get('media_count') or metrics.get('mediaCount')
    if media_count:
        lines.append(f"Media Count: {media_count}")
    
    # Caption/Description/Tweet Text
    if caption:
        lines.append(f"Caption/Description/Tweet Text: {caption}")
    
    # Posted At
    if posted_at:
        lines.append(f"Posted At: {posted_at}")
    
    # Latest Comments (Top 5)
    if latest_comments:
        lines.append("Latest Comments (Top 5):")
        for i, comment in enumerate(latest_comments[:5], 1):
            comment_text = comment.get('text') or comment.get('comments') or comment.get('comment', '')
            comment_username = comment.get('username') or comment.get('user_commenting') or comment.get('author', {}).get('username', 'Unknown')
            comment_likes = comment.get('likes') or comment.get('likeCount', 0)
            
            if comment_text:
                if comment_likes:
                    lines.append(f"  {i}. @{comment_username}: \"{comment_text}\" ({comment_likes} likes)")
                else:
                    lines.append(f"  {i}. @{comment_username}: \"{comment_text}\"")
    
    return '\n'.join(lines) if lines else "No metrics available"


def build_user_prompt(
    platform: str,
    task_id: str,
    username: str,
    caption: str,
    posted_at: str,
    metrics: Dict[str, Any],
    latest_comments: List[Dict[str, Any]],
    media_urls: List[str],
    video_length: Optional[int] = None,
    transcript: Optional[str] = None,
) -> str:
    """
    Build the user prompt from template with actual post data
    
    Args:
        platform: Platform name (instagram, x, youtube)
        task_id: Task ID for this analysis
        username: Post author username
        caption: Post caption/content
        posted_at: Post timestamp
        metrics: Post.metrics JSONField dict
        latest_comments: List of comment dicts with username, text, likes
        media_urls: List of media URLs (note: images + frames are sent as bytes, not URLs)
        video_length: Video length in seconds (for YouTube)
        transcript: Video transcript (for YouTube)
    
    Returns:
        Formatted user prompt string
    """
    template = load_prompt_template()
    
    # Extract user prompt section (after "🟩 USER PROMPT")
    user_prompt_start = template.find("🟩 USER PROMPT")
    if user_prompt_start == -1:
        logger.error("Could not find user prompt section in template")
        return ""
    
    user_prompt = template[user_prompt_start:].split("## INSTRUCTIONS")[0]
    
    # Build unified metrics sections
    user_metrics = build_user_metrics_section(platform, username, metrics)
    post_metrics = build_post_metrics_section(platform, metrics, caption, posted_at, latest_comments)
    
    # Handle conditional sections (simple string replacement - not Django templates)
    # Remove {{#if youtube}} sections if not YouTube
    if platform != 'youtube':
        # Remove YouTube-specific section
        user_prompt = re.sub(
            r'\{\{#if youtube\}\}.*?\{\{/if\}\}',
            '',
            user_prompt,
            flags=re.DOTALL
        )
    else:
        # Replace {{#if youtube}}...{{/if}} with content (remove conditionals)
        youtube_match = re.search(
            r'\{\{#if youtube\}\}(.*?)\{\{/if\}\}',
            user_prompt,
            flags=re.DOTALL
        )
        if youtube_match:
            youtube_content = youtube_match.group(1)
            user_prompt = user_prompt.replace(youtube_match.group(0), youtube_content)
    
    # Handle transcript conditional section
    if transcript and transcript.strip():
        # Replace {{#if transcript}}...{{/if}} with actual content
        transcript_section_match = re.search(
            r'\{\{#if transcript\}\}(.*?)\{\{/if\}\}',
            user_prompt,
            flags=re.DOTALL
        )
        if transcript_section_match:
            transcript_template = transcript_section_match.group(1)
            # Replace {{transcript}} inside the section
            transcript_content = transcript_template.replace('{{transcript}}', transcript.strip())
            user_prompt = user_prompt.replace(transcript_section_match.group(0), transcript_content)
    else:
        # Remove transcript section if no transcript
        user_prompt = re.sub(
            r'\{\{#if transcript\}\}.*?\{\{/if\}\}',
            '',
            user_prompt,
            flags=re.DOTALL
        )
    
    # Replace template variables
    replacements = {
        '{{platform}}': platform,
        '{{task_id}}': task_id,
        '{{requested_datetime}}': datetime.now().isoformat(),
        '{{username}}': username or 'Unknown',
        '{{user_metrics}}': user_metrics,
        '{{post_metrics}}': post_metrics,
        '{{caption}}': caption or 'No caption',
        '{{posted_at}}': posted_at or 'Unknown',
        '{{media_urls}}': '\n'.join(media_urls) if media_urls else 'No media',
        '{{video_length}}': str(video_length) if video_length else 'N/A',
        '{{frames}}': 'Video frames included in media (sent as bytes)',  # Frames now sent as bytes in media_images
    }
    
    for key, value in replacements.items():
        user_prompt = user_prompt.replace(key, str(value))
    
    return user_prompt

