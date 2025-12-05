import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

def scrape_instagram(
    type: str = "posts/date_range", 
    username: Optional[str] = None, 
    post_urls: Optional[List[str]] = None, 
    date_range: Optional[Tuple[str, str]] = None
) -> Dict[str, Any]:
    """
    Dummy Instagram scraping function
    """
    print(f"Scraping Instagram - Type: {type}, Username: {username}, Post URLs: {post_urls}, Date Range: {date_range}")
    
    # Mock response data
    mock_data = {
        "platform": "instagram",
        "scraped_at": datetime.now().isoformat(),
        "posts": []
    }
    
    if post_urls:
        # Mock data for specific post URLs
        for i, url in enumerate(post_urls):
            mock_data["posts"].append({
                "url": url,
                "post_id": f"ig_post_{i+1}",
                "username": username or "unknown_user",
                "caption": f"This is a mock Instagram post caption {i+1}",
                "likes": 1000 + (i * 100),
                "comments": 50 + (i * 10),
                "shares": 20 + (i * 5),
                "posted_at": "2024-01-15T10:30:00Z",
                "media_type": "image",
                "engagement_rate": 0.05 + (i * 0.01)
            })
    elif username and date_range:
        # Mock data for username and date range
        start_date, end_date = date_range
        mock_data["username"] = username
        mock_data["date_range"] = {"start": start_date, "end": end_date}
        
        # Generate 5 mock posts
        for i in range(5):
            mock_data["posts"].append({
                "url": f"https://instagram.com/p/mock_post_{i+1}/",
                "post_id": f"ig_post_{i+1}",
                "username": username,
                "caption": f"Mock Instagram post from {username} - Post {i+1}",
                "likes": 2000 + (i * 200),
                "comments": 100 + (i * 20),
                "shares": 50 + (i * 10),
                "posted_at": "2024-01-15T10:30:00Z",
                "media_type": "image",
                "engagement_rate": 0.08 + (i * 0.02)
            })
    
    return mock_data

def scrape_x(
    type: str = "posts/date_range", 
    username: Optional[str] = None, 
    post_urls: Optional[List[str]] = None, 
    date_range: Optional[Tuple[str, str]] = None
) -> Dict[str, Any]:
    """
    Dummy X (Twitter) scraping function
    """
    print(f"Scraping X - Type: {type}, Username: {username}, Post URLs: {post_urls}, Date Range: {date_range}")
    
    # Mock response data
    mock_data = {
        "platform": "x",
        "scraped_at": datetime.now().isoformat(),
        "posts": []
    }
    
    if post_urls:
        # Mock data for specific post URLs
        for i, url in enumerate(post_urls):
            mock_data["posts"].append({
                "url": url,
                "post_id": f"x_post_{i+1}",
                "username": username or "unknown_user",
                "content": f"This is a mock X post content {i+1} #mock #test",
                "likes": 500 + (i * 50),
                "retweets": 100 + (i * 20),
                "replies": 30 + (i * 5),
                "quotes": 15 + (i * 3),
                "posted_at": "2024-01-15T10:30:00Z",
                "engagement_rate": 0.03 + (i * 0.005)
            })
    elif username and date_range:
        # Mock data for username and date range
        start_date, end_date = date_range
        mock_data["username"] = username
        mock_data["date_range"] = {"start": start_date, "end": end_date}
        
        # Generate 5 mock posts
        for i in range(5):
            mock_data["posts"].append({
                "url": f"https://x.com/{username}/status/mock_post_{i+1}",
                "post_id": f"x_post_{i+1}",
                "username": username,
                "content": f"Mock X post from @{username} - Post {i+1} #mock #test",
                "likes": 1000 + (i * 100),
                "retweets": 200 + (i * 40),
                "replies": 60 + (i * 10),
                "quotes": 30 + (i * 6),
                "posted_at": "2024-01-15T10:30:00Z",
                "engagement_rate": 0.05 + (i * 0.01)
            })
    
    return mock_data 