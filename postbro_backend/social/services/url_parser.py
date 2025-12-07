"""
URL parsing utilities for social media platforms
"""
import re
from typing import Optional


def detect_platform_from_url(url: str) -> Optional[str]:
    """
    Detect the social media platform from a URL.
    
    Args:
        url: The URL to analyze
        
    Returns:
        Platform name ('instagram', 'x', 'youtube') or None if unknown
    """
    if not url:
        return None
    
    url_lower = url.lower().strip()
    
    # Instagram patterns
    instagram_patterns = [
        r'instagram\.com',
        r'instagr\.am',
    ]
    for pattern in instagram_patterns:
        if re.search(pattern, url_lower):
            return 'instagram'
    
    # X/Twitter patterns
    x_patterns = [
        r'x\.com',
        r'twitter\.com',
    ]
    for pattern in x_patterns:
        if re.search(pattern, url_lower):
            return 'x'
    
    # YouTube patterns
    youtube_patterns = [
        r'youtube\.com',
        r'youtu\.be',
    ]
    for pattern in youtube_patterns:
        if re.search(pattern, url_lower):
            return 'youtube'
    
    return None


def extract_post_id(url: str, platform: Optional[str] = None) -> Optional[str]:
    """
    Extract the post ID from a social media URL.
    
    Args:
        url: The URL to extract post ID from
        platform: Platform name ('instagram', 'x', 'youtube') or None to auto-detect
        
    Returns:
        Post ID string or None if not found
    """
    if not url:
        return None
    
    # Auto-detect platform if not provided
    if not platform:
        platform = detect_platform_from_url(url)
    
    if not platform:
        return None
    
    # Don't lowercase - preserve original case of IDs
    # Use case-insensitive regex for domain matching only
    url = url.strip()
    
    # Instagram post ID extraction
    # Examples:
    # https://www.instagram.com/p/ABC123/
    # https://www.instagram.com/reel/ABC123/
    if platform == 'instagram':
        patterns = [
            r'instagram\.com/p/([A-Za-z0-9_-]+)',
            r'instagram\.com/reel/([A-Za-z0-9_-]+)',
            r'instagr\.am/p/([A-Za-z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
    
    # X/Twitter post ID extraction
    # Examples:
    # https://x.com/username/status/1234567890
    # https://twitter.com/username/status/1234567890
    elif platform == 'x':
        patterns = [
            r'(?:x|twitter)\.com/\w+/status/(\d+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                return match.group(1)
    
    # YouTube video ID extraction - handles all formats
    # Examples:
    # https://www.youtube.com/watch?v=VIDEO_ID
    # https://youtu.be/VIDEO_ID
    # https://www.youtube.com/shorts/VIDEO_ID
    # https://m.youtube.com/watch?v=VIDEO_ID (mobile)
    # https://youtube.com/embed/VIDEO_ID (embed)
    # https://youtube.com/watch?v=VIDEO_ID&t=123&feature=share (with params)
    elif platform == 'youtube':
        # Try patterns in order of specificity
        patterns = [
            # Shorts URLs (most specific)
            r'youtube\.com/shorts/([A-Za-z0-9_-]{11})',
            # Embed URLs
            r'youtube\.com/embed/([A-Za-z0-9_-]{11})',
            # Standard watch URLs (with or without extra params)
            r'(?:youtube\.com/watch\?v=|youtu\.be/)([A-Za-z0-9_-]{11})',
            # Mobile URLs
            r'm\.youtube\.com/watch\?v=([A-Za-z0-9_-]{11})',
            # URL fragments (after # or &)
            r'[#&]v=([A-Za-z0-9_-]{11})',
        ]
        for pattern in patterns:
            match = re.search(pattern, url, re.IGNORECASE)
            if match:
                video_id = match.group(1)
                # Validate it's exactly 11 chars (YouTube ID standard length)
                if len(video_id) == 11:
                    return video_id
    
    return None

