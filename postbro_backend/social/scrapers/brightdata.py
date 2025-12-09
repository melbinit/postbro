"""
BrightData Scraper

This module provides scrapers for Instagram and YouTube using BrightData API.
BrightData is a web scraping platform that handles proxy rotation and
anti-bot measures automatically.
"""

import os
import json
import logging
import time
from typing import List, Dict, Optional
from django.conf import settings
import requests
from requests.exceptions import RequestException, Timeout
from analytics.tasks import log_external_api_call

logger = logging.getLogger(__name__)


class BrightDataScraper:
    """
    BrightData API scraper for Instagram and YouTube.
    
    This scraper handles:
    - Instagram post scraping
    - YouTube video scraping
    - Error handling and retries
    - Rate limit management
    """
    
    def __init__(self):
        """
        Initialize BrightData scraper with API credentials.
        
        Raises:
            ValueError: If required environment variables are not set
        """
        self.api_token = os.getenv('BRIGHTDATA_API_TOKEN')
        self.instagram_dataset_id = os.getenv('BRIGHTDATA_INSTAGRAM_DATASET_ID')
        self.youtube_dataset_id = os.getenv('BRIGHTDATA_YOUTUBE_DATASET_ID')
        self.base_url = "https://api.brightdata.com/datasets/v3/scrape"
        self.timeout = 120  # 2 minutes timeout for long-running requests
        
        # Validate configuration
        if not self.api_token:
            raise ValueError("BRIGHTDATA_API_TOKEN environment variable is required")
        if not self.instagram_dataset_id:
            raise ValueError("BRIGHTDATA_INSTAGRAM_DATASET_ID environment variable is required")
        if not self.youtube_dataset_id:
            raise ValueError("BRIGHTDATA_YOUTUBE_DATASET_ID environment variable is required")
    
    def _make_request(
        self,
        dataset_id: str,
        input_data: List[Dict],
        timeout: Optional[int] = None,
        user_id: Optional[str] = None,
        operation: str = 'scrape',
        analysis_request_id: Optional[str] = None,  # For linking to analysis request in logs
    ) -> Dict:
        """
        Make a request to BrightData API.
        
        Args:
            dataset_id: BrightData dataset ID
            input_data: List of input objects for the scraper
            timeout: Request timeout in seconds (default: self.timeout)
            user_id: User ID for tracking (optional)
            operation: Operation name for tracking (e.g., 'scrape_instagram', 'scrape_youtube')
            
        Returns:
            API response as dictionary
            
        Raises:
            RequestException: If the API request fails
            ValueError: If the response is invalid
        """
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }
        
        data = json.dumps({"input": input_data})
        request_size = len(data.encode('utf-8'))
        
        url = f"{self.base_url}?dataset_id={dataset_id}&notify=false&include_errors=true"
        timeout = timeout or self.timeout
        
        start_time = time.time()
        status_code = 200
        error_message = None
        response_size = None
        
        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                timeout=timeout
            )
            response.raise_for_status()
            status_code = response.status_code
            response_size = len(response.content)
            
            result = response.json()
            
            # Log the raw response for debugging
            logger.debug(f"BrightData raw response type: {type(result)}")
            if isinstance(result, list):
                logger.debug(f"BrightData response is list with {len(result)} items")
                if len(result) > 0:
                    logger.debug(f"First item keys: {list(result[0].keys()) if isinstance(result[0], dict) else 'Not a dict'}")
            elif isinstance(result, dict):
                logger.debug(f"BrightData response is dict with keys: {list(result.keys())}")
            
            # BrightData returns array, get first item
            if isinstance(result, list) and len(result) > 0:
                return result[0]
            elif isinstance(result, dict):
                return result
            else:
                logger.error(f"Unexpected BrightData response format: {type(result)}, value: {result}")
                raise ValueError(f"Unexpected response format: {type(result)}")
        
        except Timeout:
            logger.error(f"BrightData API timeout after {timeout}s")
            status_code = 504
            error_message = f"Request timeout after {timeout} seconds"
            response_time_ms = int((time.time() - start_time) * 1000)
            # Log failed API call (no cost for failed requests)
            try:
                log_external_api_call.delay(
                    user_id=user_id,
                    service='brightdata',
                    endpoint=url,
                    method='POST',
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    cost_estimate=None,  # No cost for failed requests
                    request_size_bytes=request_size,
                    error_message=error_message,
                    metadata={
                        'dataset_id': dataset_id,
                        'operation': operation,
                        'analysis_request_id': analysis_request_id,  # Link to analysis request
                    }
                )
            except Exception:
                pass
            raise RequestException(error_message)
        
        except requests.exceptions.HTTPError as e:
            logger.error(f"BrightData API HTTP error: {e.response.status_code} - {e.response.text}")
            status_code = e.response.status_code
            error_message = e.response.text[:1000] if e.response.text else str(e)
            response_time_ms = int((time.time() - start_time) * 1000)
            # Log failed API call (no cost for failed requests)
            try:
                log_external_api_call.delay(
                    user_id=user_id,
                    service='brightdata',
                    endpoint=url,
                    method='POST',
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    cost_estimate=None,  # No cost for failed requests
                    request_size_bytes=request_size,
                    response_size_bytes=len(e.response.content) if e.response.content else None,
                    error_message=error_message,
                    metadata={
                        'dataset_id': dataset_id,
                        'operation': operation,
                        'analysis_request_id': analysis_request_id,  # Link to analysis request
                    }
                )
            except Exception:
                pass
            raise RequestException(f"API request failed: {status_code}")
        
        except requests.exceptions.RequestException as e:
            logger.error(f"BrightData API request error: {str(e)}")
            status_code = 500
            error_message = str(e)[:1000]
            response_time_ms = int((time.time() - start_time) * 1000)
            # Log failed API call (no cost for failed requests)
            try:
                log_external_api_call.delay(
                    user_id=user_id,
                    service='brightdata',
                    endpoint=url,
                    method='POST',
                    status_code=status_code,
                    response_time_ms=response_time_ms,
                    cost_estimate=None,  # No cost for failed requests
                    request_size_bytes=request_size,
                    error_message=error_message,
                    metadata={
                        'dataset_id': dataset_id,
                        'operation': operation,
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
                        service='brightdata',
                        endpoint=url,
                        method='POST',
                        status_code=status_code,
                        response_time_ms=response_time_ms,
                        cost_estimate=None,  # Cost tracking removed - check dashboard instead
                        request_size_bytes=request_size,
                        response_size_bytes=response_size,
                        metadata={
                        'dataset_id': dataset_id,
                        'operation': operation,
                        'analysis_request_id': analysis_request_id,  # Link to analysis request
                    }
                    )
                except Exception:
                    pass
    
    def scrape_instagram_post(self, url: str, analysis_request_id: Optional[str] = None) -> Dict:
        """
        Scrape a single Instagram post.
        
        Args:
            url: Instagram post URL (e.g., https://www.instagram.com/p/ABC123/)
            
        Returns:
            Dictionary containing Instagram post data
            
        Raises:
            RequestException: If scraping fails
            ValueError: If URL is invalid
            
        Example:
            >>> scraper = BrightDataScraper()
            >>> data = scraper.scrape_instagram_post('https://www.instagram.com/p/ABC123/')
            >>> print(data['likes'])
            1234
        """
        if not url or 'instagram.com' not in url.lower():
            raise ValueError(f"Invalid Instagram URL: {url}")
        
        logger.info(f"Scraping Instagram post: {url}")
        
        input_data = [{"url": url}]
        # Get user_id from context if available (passed from analysis task)
        user_id = getattr(self, '_current_user_id', None)
        result = self._make_request(
            self.instagram_dataset_id, 
            input_data, 
            timeout=60,
            user_id=user_id,
            operation='scrape_instagram_post',
            analysis_request_id=analysis_request_id
        )
        
        # Log the result before processing
        logger.debug(f"BrightData result for {url}: keys={list(result.keys()) if isinstance(result, dict) else 'Not a dict'}")
        
        # Check if result is empty or malformed
        if not result or not isinstance(result, dict):
            logger.error(f"BrightData returned invalid result for {url}: {result}")
            return {
                'success': False,
                'error': 'Invalid response from BrightData',
                'url': url,
                'raw_response': str(result)
            }
        
        # Add success flag
        result['success'] = True
        result['url'] = url
        
        return result
    
    def scrape_instagram_posts(self, urls: List[str], analysis_request_id: Optional[str] = None) -> List[Dict]:
        """
        Scrape multiple Instagram posts.
        
        Args:
            urls: List of Instagram post URLs
            analysis_request_id: Optional analysis request ID for logging
            
        Returns:
            List of dictionaries containing post data or error information
            
        Example:
            >>> scraper = BrightDataScraper()
            >>> results = scraper.scrape_instagram_posts([
            ...     'https://www.instagram.com/p/ABC123/',
            ...     'https://www.instagram.com/p/XYZ789/'
            ... ])
            >>> len(results)
            2
        """
        results = []
        
        for url in urls:
            try:
                post_data = self.scrape_instagram_post(url, analysis_request_id=analysis_request_id)
                results.append(post_data)
            except Exception as e:
                logger.error(f"Failed to scrape Instagram post {url}: {str(e)}")
                results.append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
        
        return results
    
    def scrape_youtube_video(self, url: str, analysis_request_id: Optional[str] = None) -> Dict:
        """
        Scrape a single YouTube video.
        
        Args:
            url: YouTube video URL (e.g., https://www.youtube.com/watch?v=ABC123)
            
        Returns:
            Dictionary containing YouTube video data including transcript
            
        Raises:
            RequestException: If scraping fails
            ValueError: If URL is invalid
            
        Example:
            >>> scraper = BrightDataScraper()
            >>> data = scraper.scrape_youtube_video('https://www.youtube.com/watch?v=ABC123')
            >>> print(data['title'])
            'Video Title'
        """
        if not url or 'youtube.com' not in url.lower() and 'youtu.be' not in url.lower():
            raise ValueError(f"Invalid YouTube URL: {url}")
        
        logger.info(f"Scraping YouTube video: {url}")
        
        input_data = [{
            "url": url,
            "country": "",
            "transcription_language": ""
        }]
        
        # Get user_id from context if available (passed from analysis task)
        user_id = getattr(self, '_current_user_id', None)
        # YouTube scraping can take longer, use extended timeout
        result = self._make_request(
            self.youtube_dataset_id, 
            input_data, 
            timeout=180,
            user_id=user_id,
            operation='scrape_youtube_video',
            analysis_request_id=analysis_request_id
        )
        
        # Add success flag
        result['success'] = True
        result['url'] = url
        
        return result
    
    def scrape_youtube_videos(self, urls: List[str], analysis_request_id: Optional[str] = None) -> List[Dict]:
        """
        Scrape multiple YouTube videos.
        
        Args:
            urls: List of YouTube video URLs
            
        Returns:
            List of dictionaries containing video data or error information
            
        Example:
            >>> scraper = BrightDataScraper()
            >>> results = scraper.scrape_youtube_videos([
            ...     'https://www.youtube.com/watch?v=ABC123',
            ...     'https://www.youtube.com/watch?v=XYZ789'
            ... ])
            >>> len(results)
            2
        """
        results = []
        
        for url in urls:
            try:
                video_data = self.scrape_youtube_video(url, analysis_request_id=analysis_request_id)
                results.append(video_data)
            except Exception as e:
                logger.error(f"Failed to scrape YouTube video {url}: {str(e)}")
                results.append({
                    'url': url,
                    'error': str(e),
                    'success': False
                })
        
        return results

