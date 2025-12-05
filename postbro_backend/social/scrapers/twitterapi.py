"""
TwitterAPI.io Scraper

This module provides a scraper for Twitter/X posts using TwitterAPI.io.
TwitterAPI.io is a third-party API service that provides access to Twitter data.
"""

import os
import logging
import re
import time
from typing import List, Dict, Optional
import requests
from requests.exceptions import RequestException, Timeout
from analytics.tasks import log_external_api_call

logger = logging.getLogger(__name__)


class TwitterAPIScraper:
    """
    TwitterAPI.io scraper for Twitter/X posts.
    
    This scraper handles:
    - Tweet scraping by URL
    - Error handling and retries
    - Rate limit management
    """
    
    def __init__(self):
        """
        Initialize TwitterAPI scraper with API credentials.
        
        Raises:
            ValueError: If required environment variables are not set
        """
        self.api_key = os.getenv('TWITTERAPI_IO_KEY')
        self.base_url = "https://api.twitterapi.io/twitter/tweets"
        self.timeout = 30
        
        if not self.api_key:
            raise ValueError("TWITTERAPI_IO_KEY environment variable is required")
    
    def extract_tweet_id(self, url: str) -> Optional[str]:
        """
        Extract tweet ID from Twitter/X URL.
        
        Args:
            url: Twitter/X post URL
            
        Returns:
            Tweet ID or None if extraction fails
            
        Examples:
            >>> scraper = TwitterAPIScraper()
            >>> scraper.extract_tweet_id('https://x.com/user/status/123456')
            '123456'
            >>> scraper.extract_tweet_id('https://twitter.com/user/status/789012')
            '789012'
        """
        if not url:
            return None
        
        # Pattern: /status/TWEET_ID
        match = re.search(r'/status/(\d+)', url)
        return match.group(1) if match else None
    
    def _make_request(
        self, 
        tweet_id: str, 
        user_id: Optional[str] = None,
        url: Optional[str] = None,
        analysis_request_id: Optional[str] = None,  # For linking to analysis request in logs
    ) -> Dict:
        """
        Make a request to TwitterAPI.io.
        
        Args:
            tweet_id: Twitter tweet ID
            user_id: User ID for tracking (optional)
            url: Original tweet URL for tracking (optional)
            
        Returns:
            API response as dictionary
            
        Raises:
            RequestException: If the API request fails
            ValueError: If the response is invalid
        """
        headers = {"X-API-Key": self.api_key}
        params = {"tweet_ids": tweet_id}
        
        start_time = time.time()
        status_code = 200
        error_message = None
        response_size = None
        request_size = len(str(params).encode('utf-8'))
        
        try:
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            status_code = response.status_code
            response_size = len(response.content)
            
            result = response.json()
            
            # TwitterAPI returns {tweets: [...]}
            if 'tweets' in result and len(result['tweets']) > 0:
                return result['tweets'][0]
            elif 'status' in result and result.get('status') == 'success':
                # Empty result but successful
                raise ValueError(f"No tweet data returned for ID: {tweet_id}")
            else:
                raise ValueError(f"Unexpected response format: {result}")
        
        except Timeout:
            logger.error(f"TwitterAPI.io timeout after {self.timeout}s")
            status_code = 504
            error_message = f"Request timeout after {self.timeout} seconds"
            response_time_ms = int((time.time() - start_time) * 1000)
            # Log failed API call
            try:
                log_external_api_call.delay(
                    user_id=user_id,
                    service='twitterapi',
                    endpoint=self.base_url,
                    method='GET',
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    cost_estimate=None,  # Cost tracking removed - check dashboard instead
                    request_size_bytes=request_size,
                    error_message=error_message,
                    metadata={
                        'tweet_id': tweet_id,
                        'url': url,
                        'analysis_request_id': analysis_request_id,  # Link to analysis request
                    }
                )
            except Exception:
                pass
            raise RequestException(error_message)
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"TwitterAPI.io HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            error_message = e.response.text[:1000] if e.response.text else str(e)
            response_time_ms = int((time.time() - start_time) * 1000)
            # Log failed API call
            try:
                log_external_api_call.delay(
                    user_id=user_id,
                    service='twitterapi',
                    endpoint=self.base_url,
                    method='GET',
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    cost_estimate=None,  # Cost tracking removed - check dashboard instead
                    request_size_bytes=request_size,
                    response_size_bytes=len(e.response.content) if e.response.content else None,
                    error_message=error_message,
                    metadata={
                        'tweet_id': tweet_id,
                        'url': url,
                        'analysis_request_id': analysis_request_id,  # Link to analysis request
                    }
                )
            except Exception:
                pass
            raise RequestException(f"API request failed: {status_code}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"TwitterAPI.io request error: {str(e)}")
            status_code = 500
            error_message = str(e)[:1000]
            response_time_ms = int((time.time() - start_time) * 1000)
            # Log failed API call
            try:
                log_external_api_call.delay(
                    user_id=user_id,
                    service='twitterapi',
                    endpoint=self.base_url,
                    method='GET',
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    cost_estimate=None,  # Cost tracking removed - check dashboard instead
                    request_size_bytes=request_size,
                    error_message=error_message,
                    metadata={
                        'tweet_id': tweet_id,
                        'url': url,
                        'analysis_request_id': analysis_request_id,  # Link to analysis request
                    }
                )
            except Exception:
                pass
            raise RequestException(f"Request failed: {str(e)}")
        
        finally:
            # Log successful API call
            if status_code == 200:
                response_time_ms = int((time.time() - start_time) * 1000)
                try:
                    log_external_api_call.delay(
                        user_id=user_id,
                        service='twitterapi',
                        endpoint=self.base_url,
                        method='GET',
                        status_code=status_code,
                        response_time_ms=response_time_ms,
                        cost_estimate=None,  # Cost tracking removed - check dashboard instead
                        request_size_bytes=request_size,
                        response_size_bytes=response_size,
                        metadata={
                        'tweet_id': tweet_id,
                        'url': url,
                        'analysis_request_id': analysis_request_id,  # Link to analysis request
                    }
                    )
                except Exception:
                    pass
    
    def scrape_tweet(self, url: str, analysis_request_id: Optional[str] = None) -> Dict:
        """
        Scrape a single tweet.
        
        Args:
            url: Twitter/X post URL (e.g., https://x.com/user/status/123456)
            
        Returns:
            Dictionary containing tweet data
            
        Raises:
            RequestException: If scraping fails
            ValueError: If URL is invalid or tweet ID cannot be extracted
            
        Example:
            >>> scraper = TwitterAPIScraper()
            >>> data = scraper.scrape_tweet('https://x.com/user/status/123456')
            >>> print(data['text'])
            'Tweet content'
        """
        if not url:
            raise ValueError("URL cannot be empty")
        
        # Validate URL format
        if 'x.com' not in url.lower() and 'twitter.com' not in url.lower():
            raise ValueError(f"Invalid Twitter/X URL: {url}")
        
        tweet_id = self.extract_tweet_id(url)
        if not tweet_id:
            raise ValueError(f"Could not extract tweet ID from URL: {url}")
        
        logger.info(f"Scraping Twitter/X tweet: {url} (ID: {tweet_id})")
        
        # Get user_id from context if available (passed from analysis task)
        user_id = getattr(self, '_current_user_id', None)
        result = self._make_request(tweet_id, user_id=user_id, url=url, analysis_request_id=analysis_request_id)
        
        # Add success flag and original URL
        result['success'] = True
        result['url'] = url
        result['tweet_id'] = tweet_id
        
        return result
    
    def scrape_tweets(self, urls: List[str], analysis_request_id: Optional[str] = None) -> List[Dict]:
        """
        Scrape multiple tweets.
        
        Args:
            urls: List of Twitter/X post URLs
            
        Returns:
            List of dictionaries containing tweet data or error information
            
        Example:
            >>> scraper = TwitterAPIScraper()
            >>> results = scraper.scrape_tweets([
            ...     'https://x.com/user/status/123456',
            ...     'https://x.com/user/status/789012'
            ... ])
            >>> len(results)
            2
        """
        results = []
        
        for url in urls:
            try:
                tweet_data = self.scrape_tweet(url, analysis_request_id=analysis_request_id)
                results.append(tweet_data)
            except Exception as e:
                logger.error(f"Failed to scrape Twitter/X tweet {url}: {str(e)}")
                results.append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
        
        return results
