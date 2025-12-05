"""
Media Processor Service

This module handles processing of social media content:
- Extracting frames from videos using FFmpeg and yt-dlp
- Downloading images with proper headers
- Uploading media to Supabase Storage
- Smart upload strategy (immediate vs lazy)
"""

import os
import subprocess
import requests
import logging
import tempfile
import json
import base64
from typing import List, Optional, Tuple
from io import BytesIO

from django.conf import settings
from supabase import create_client, Client
from social.services.whisper_service import transcribe_audio_with_whisper

logger = logging.getLogger(__name__)


class MediaProcessor:
    """
    Service to process media files for social media posts.
    
    Handles:
    - Video frame extraction (YouTube, Instagram, Twitter)
    - Image downloading with browser headers
    - Supabase Storage uploads
    - Smart upload strategy (immediate vs lazy)
    """
    
    def __init__(self):
        """Initialize Supabase client and configuration."""
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_ROLE_KEY') or os.getenv('SUPABASE_SECRET_KEY')
        self.bucket_name = os.getenv('SUPABASE_STORAGE_BUCKET', 'post-media')
        
        if not self.supabase_url or not self.supabase_key:
            logger.warning(
                "Supabase Storage not configured. Media uploads will be skipped. "
                "Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY environment variables."
            )
            self.supabase = None
        else:
            try:
                self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
                logger.info(f"MediaProcessor initialized with bucket: {self.bucket_name}")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                self.supabase = None
    
    def should_upload_immediately(self, platform: str, media_type: str, source_url: str) -> bool:
        """
        Determine if media should be uploaded immediately or lazily.
        
        Strategy:
        - All images: Upload immediately (to get base64 for GPT-4o)
        - Video frames: Always upload immediately (needed for Gemini, small files)
        
        Args:
            platform: Platform name ('instagram', 'youtube', 'twitter', 'x')
            media_type: Media type ('image', 'video', 'video_frame')
            source_url: Original media URL
            
        Returns:
            True if should upload immediately, False for lazy upload
        """
        # Always upload video frames immediately (small, needed for Gemini)
        if media_type == 'video_frame':
            return True
        
        # All images: Upload immediately (to get base64 for GPT-4o)
        if media_type == 'image':
            return True
        
        # Instagram videos: Extract frames immediately (needed for Gemini)
        if platform == 'instagram' and media_type == 'video':
            return True  # Will extract frames, not upload video itself
        
        # Twitter images: Lazy upload (URLs don't expire)
        if platform == 'twitter' and media_type == 'image':
            return False
        
        # Default: upload immediately (safe)
        return True
    
    def extract_youtube_frames(
        self,
        video_id: str,
        num_frames: int = 5,
        quality: int = 2
    ) -> List[bytes]:
        """
        Extract frames from YouTube video using yt-dlp and FFmpeg.
        
        Fast approach: Gets video URL and extracts frames directly (no full download).
        If extraction fails, returns empty list (graceful failure - doesn't block analysis).
        
        Args:
            video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
            num_frames: Number of frames to extract (default: 5)
            quality: JPEG quality (1-31, lower = better, default: 2)
            
        Returns:
            List of frame image data (bytes) - empty list if extraction fails
        """
        frames = []
        
        try:
            # Get video duration using yt-dlp
            duration = self._get_youtube_duration(video_id)
            if duration is None:
                logger.warning(f"Could not get duration for YouTube video {video_id}, using default extraction")
                # Use default frame times if duration unknown
                frame_times = [0, 10, 20, 30, 40]
            else:
                # Calculate frame positions (0%, 25%, 50%, 75%, 100%)
                if num_frames == 1:
                    frame_times = [duration / 2]
                else:
                    # Avoid extracting at exact end (FFmpeg can't handle boundary)
                    # Cap at duration - 0.1s to avoid encoder errors
                    max_time = max(0.1, duration - 0.1)
                    frame_times = [max_time * (i / (num_frames - 1)) for i in range(num_frames)]
            
            # Extract each frame (fast - uses URL directly)
            for i, time in enumerate(frame_times):
                try:
                    frame_data = self._extract_youtube_frame(video_id, time, quality)
                    if frame_data:
                        frames.append(frame_data)
                        logger.debug(f"Extracted frame {i+1}/{num_frames} at {time:.2f}s from YouTube {video_id}")
                except Exception as e:
                    logger.warning(f"Failed to extract frame {i+1} at {time:.2f}s: {e}")
                    continue
            
            if frames:
                logger.info(f"Successfully extracted {len(frames)} frames from YouTube video {video_id}")
            else:
                logger.warning(f"Could not extract any frames from YouTube video {video_id} - continuing without frames")
            
            return frames  # Return empty list if all failed - graceful failure
            
        except Exception as e:
            # Graceful failure - log and return empty list (don't block analysis)
            logger.warning(f"Frame extraction failed for YouTube video {video_id}: {e} - continuing without frames")
            return []
    
    def _get_youtube_duration(self, video_id: str) -> Optional[float]:
        """
        Get YouTube video duration using yt-dlp.
        
        Args:
            video_id: YouTube video ID
            
        Returns:
            Duration in seconds, or None if failed
        """
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-warnings',
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
                duration = data.get('duration')
                if duration:
                    return float(duration)
            
            return None
            
        except (subprocess.TimeoutExpired, json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Could not get YouTube video duration: {e}")
            return None
        except Exception as e:
            logger.warning(f"Unexpected error getting YouTube duration: {e}")
            return None
    
    def _extract_youtube_frame(
        self,
        video_id: str,
        time: float,
        quality: int = 2
    ) -> Optional[bytes]:
        """
        Extract a single frame from YouTube video at specific time.
        
        Fast approach: Gets video stream URL and extracts frame immediately.
        If URL expires or fails, returns None (graceful failure).
        
        Args:
            video_id: YouTube video ID
            time: Time in seconds
            quality: JPEG quality (1-31, lower = better)
            
        Returns:
            Frame image data as bytes, or None if failed
        """
        try:
            # Step 1: Get video stream URL using yt-dlp (fast - no download)
            ytdlp_cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]',  # Get 720p or lower (faster)
                '-g',  # Get URL only (don't download)
                '--no-warnings',
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            ytdlp_result = subprocess.run(
                ytdlp_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            video_stream_url = ytdlp_result.stdout.strip()
            if not video_stream_url:
                logger.warning(f"No video stream URL returned for YouTube {video_id}")
                return None
            
            # Step 2: Extract frame using FFmpeg (immediate - before URL expires)
            ffmpeg_cmd = [
                'ffmpeg',
                '-ss', str(time),      # Seek to time
                '-i', video_stream_url, # Input URL
                '-vframes', '1',        # Extract 1 frame
                '-q:v', str(quality),   # Quality (2 = high quality)
                '-f', 'image2',         # Output format
                '-vcodec', 'mjpeg',     # Codec
                '-timeout', '5000000',  # 5 second timeout (microseconds)
                'pipe:1'                # Output to stdout
            ]
            
            ffmpeg_result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                timeout=10,  # Short timeout - fail fast
                check=True
            )
            
            if not ffmpeg_result.stdout:
                return None
            
            frame_bytes = ffmpeg_result.stdout
            
            # Validate frame bytes are actually a valid image using PIL
            try:
                from PIL import Image
                from io import BytesIO
                pil_image = Image.open(BytesIO(frame_bytes))
                pil_image.verify()  # Verify the image is valid
                # Reopen after verify (verify() closes the image)
                pil_image = Image.open(BytesIO(frame_bytes))
                logger.info(f"✅ [MediaProcessor] PIL validated YouTube frame at {time}s as {pil_image.format} ({pil_image.size[0]}x{pil_image.size[1]}, {len(frame_bytes)} bytes)")
                logger.info(f"   📊 Bytes first 20 (hex): {frame_bytes[:20].hex()}")
                logger.info(f"   📊 Bytes last 20 (hex): {frame_bytes[-20:].hex()}")
            except Exception as pil_error:
                logger.error(f"❌ [MediaProcessor] PIL validation failed for YouTube frame at {time}s: {pil_error}")
                logger.error(f"   Bytes length: {len(frame_bytes)}")
                logger.error(f"   First 100 bytes (hex): {frame_bytes[:100].hex()}")
                return None
            
            return frame_bytes
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout extracting frame at {time}s from YouTube {video_id}")
            return None
        except subprocess.CalledProcessError as e:
            # Don't log full error - just warning (graceful failure)
            logger.debug(f"Could not extract frame at {time}s from YouTube {video_id}")
            return None
        except Exception as e:
            logger.debug(f"Error extracting frame at {time}s from YouTube {video_id}: {e}")
            return None
    
    def extract_video_frames(
        self,
        video_url: str,
        num_frames: int = 5,
        quality: int = 2
    ) -> List[bytes]:
        """
        Extract frames from video URL (Instagram, Twitter videos).
        
        Args:
            video_url: Direct video URL
            num_frames: Number of frames to extract
            quality: JPEG quality (1-31, lower = better)
            
        Returns:
            List of frame image data (bytes)
        """
        frames = []
        
        try:
            # Get video duration
            duration = self._get_video_duration(video_url)
            if duration is None:
                logger.warning(f"Could not get duration for video {video_url}, using default")
                frame_times = [0, 10, 20, 30, 40]
            else:
                if num_frames == 1:
                    frame_times = [duration / 2]
                else:
                    # Avoid extracting at exact end (FFmpeg can't handle boundary)
                    # Cap at duration - 0.1s to avoid encoder errors
                    max_time = max(0.1, duration - 0.1)
                    frame_times = [max_time * (i / (num_frames - 1)) for i in range(num_frames)]
            
            # Extract each frame
            for i, time in enumerate(frame_times):
                try:
                    frame_data = self._extract_single_frame(video_url, time, quality)
                    if frame_data:
                        frames.append(frame_data)
                        logger.debug(f"Extracted frame {i+1}/{num_frames} at {time:.2f}s")
                except Exception as e:
                    logger.error(f"Failed to extract frame {i+1}: {e}")
                    continue
            
            if not frames:
                raise ValueError(f"Failed to extract any frames from {video_url}")
            
            logger.info(f"Successfully extracted {len(frames)} frames from {video_url}")
            return frames
            
        except Exception as e:
            logger.error(f"Failed to extract frames from {video_url}: {e}")
            raise
    
    def _get_video_duration(self, video_url: str) -> Optional[float]:
        """Get video duration using FFprobe."""
        try:
            cmd = [
                'ffprobe',
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return float(result.stdout.strip())
            
            return None
            
        except (subprocess.TimeoutExpired, ValueError) as e:
            logger.warning(f"Could not get video duration: {e}")
            return None
    
    def _extract_single_frame(
        self,
        video_url: str,
        time: float,
        quality: int = 2
    ) -> Optional[bytes]:
        """Extract a single frame at specific time from video URL."""
        try:
            cmd = [
                'ffmpeg',
                '-ss', str(time),
                '-i', video_url,
                '-vframes', '1',
                '-q:v', str(quality),
                '-f', 'image2',
                '-vcodec', 'mjpeg',
                'pipe:1'
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,
                check=True
            )
            
            if not result.stdout:
                return None
            
            frame_bytes = result.stdout
            
            # Validate frame bytes are actually a valid image using PIL
            try:
                from PIL import Image
                from io import BytesIO
                pil_image = Image.open(BytesIO(frame_bytes))
                pil_image.verify()  # Verify the image is valid
                # Reopen after verify (verify() closes the image)
                pil_image = Image.open(BytesIO(frame_bytes))
                logger.info(f"✅ [MediaProcessor] PIL validated video frame at {time}s as {pil_image.format} ({pil_image.size[0]}x{pil_image.size[1]}, {len(frame_bytes)} bytes)")
                logger.info(f"   📊 Bytes first 20 (hex): {frame_bytes[:20].hex()}")
                logger.info(f"   📊 Bytes last 20 (hex): {frame_bytes[-20:].hex()}")
            except Exception as pil_error:
                logger.error(f"❌ [MediaProcessor] PIL validation failed for video frame at {time}s: {pil_error}")
                logger.error(f"   Bytes length: {len(frame_bytes)}")
                logger.error(f"   First 100 bytes (hex): {frame_bytes[:100].hex()}")
                return None
            
            return frame_bytes
            
        except subprocess.TimeoutExpired:
            logger.error(f"FFmpeg timeout extracting frame at {time}s")
            return None
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.error(f"FFmpeg error extracting frame: {error_msg}")
            return None
    
    def download_image(self, image_url: str, timeout: int = 30) -> Optional[bytes]:
        """
        Download image from URL with browser headers to avoid blocking.
        
        Args:
            image_url: URL of the image
            timeout: Request timeout in seconds
            
        Returns:
            Image data as bytes, or None if failed
        """
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.instagram.com/',
                'Accept-Encoding': 'gzip, deflate, br',
            }
            
            response = requests.get(image_url, headers=headers, timeout=timeout, stream=True)
            response.raise_for_status()
            
            # Verify it's an image
            content_type = response.headers.get('content-type', '')
            if not content_type.startswith('image/'):
                logger.warning(f"URL {image_url} is not an image (content-type: {content_type})")
                return None
            
            image_bytes = response.content
            
            # Validate bytes are actually a valid image using PIL (catches HTML, corrupted data, etc.)
            try:
                from PIL import Image
                from io import BytesIO
                pil_image = Image.open(BytesIO(image_bytes))
                pil_image.verify()  # Verify the image is valid
                # Reopen after verify (verify() closes the image)
                pil_image = Image.open(BytesIO(image_bytes))
                logger.info(f"✅ [MediaProcessor] PIL validated downloaded image as {pil_image.format} ({pil_image.size[0]}x{pil_image.size[1]}, {len(image_bytes)} bytes)")
                logger.info(f"   📊 Bytes first 20 (hex): {image_bytes[:20].hex()}")
                logger.info(f"   📊 Bytes last 20 (hex): {image_bytes[-20:].hex()}")
            except Exception as pil_error:
                logger.error(f"❌ [MediaProcessor] PIL validation failed for downloaded image from {image_url}: {pil_error}")
                logger.error(f"   Bytes length: {len(image_bytes)}, content-type: {content_type}")
                logger.error(f"   First 100 bytes (hex): {image_bytes[:100].hex()}")
                logger.error(f"   First 200 chars (text): {image_bytes[:200].decode('utf-8', errors='ignore')}")
                return None
            
            return image_bytes
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download image from {image_url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading image: {e}")
            return None
    
    def upload_to_supabase(
        self,
        file_data: bytes,
        filename: str,
        content_type: str = 'image/jpeg'
    ) -> Optional[str]:
        """
        Upload file to Supabase Storage.
        
        Args:
            file_data: File data as bytes
            filename: Filename/path in bucket
            content_type: MIME type of the file
            
        Returns:
            Public URL of uploaded file, or None if failed
        """
        if not self.supabase:
            logger.warning("Supabase not configured, skipping upload")
            return None
        
        try:
            # Upload to Supabase Storage
            response = self.supabase.storage.from_(self.bucket_name).upload(
                path=filename,
                file=file_data,
                file_options={
                    "content-type": content_type,
                    "upsert": "true"  # Overwrite if exists
                }
            )
            
            # Get public URL
            public_url = self.supabase.storage.from_(self.bucket_name).get_public_url(filename)
            
            logger.info(f"Uploaded {filename} to Supabase Storage: {public_url}")
            return public_url
            
        except Exception as e:
            logger.error(f"Failed to upload {filename} to Supabase Storage: {e}")
            return None
    
    def process_youtube_video(
        self,
        video_id: str,
        post_id: str,
        num_frames: int = 5
    ) -> Tuple[List[str], List[bytes]]:
        """
        Complete YouTube video processing: extract frames, upload to Supabase, return URLs + bytes.
        
        Args:
            video_id: YouTube video ID
            post_id: Post ID for filename
            num_frames: Number of frames to extract
            
        Returns:
            Tuple of (frame_urls, frame_bytes_list) - both lists have same length
        """
        frame_urls = []
        frame_bytes_list = []
        
        try:
            # Extract frames as bytes
            frames = self.extract_youtube_frames(video_id, num_frames)
            
            # Upload each frame and keep bytes
            for i, frame_data in enumerate(frames):
                filename = f"frames/{post_id}/frame_{i+1}.jpg"
                public_url = self.upload_to_supabase(
                    file_data=frame_data,
                    filename=filename,
                    content_type='image/jpeg'
                )
                
                if public_url:
                    frame_urls.append(public_url)
                    frame_bytes_list.append(frame_data)  # Keep raw bytes!
            
            logger.info(f"Processed {len(frame_urls)} frames for YouTube video {video_id} (kept {len(frame_bytes_list)} bytes)")
            return frame_urls, frame_bytes_list
            
        except Exception as e:
            logger.error(f"Failed to process YouTube video {video_id}: {e}")
            return [], []
    
    def process_video_frames(
        self,
        video_url: str,
        post_id: str,
        num_frames: int = 5
    ) -> Tuple[List[str], List[bytes]]:
        """
        Extract frames from video URL, upload to Supabase, and return URLs + bytes.
        
        Args:
            video_url: Video URL (Instagram, Twitter)
            post_id: Post ID for filename
            num_frames: Number of frames to extract
            
        Returns:
            Tuple of (frame_urls, frame_bytes_list) - both lists have same length
        """
        frame_urls = []
        frame_bytes_list = []
        
        try:
            # Extract frames as bytes
            frames = self.extract_video_frames(video_url, num_frames)
            
            # Upload each frame and keep bytes
            for i, frame_data in enumerate(frames):
                filename = f"frames/{post_id}/frame_{i+1}.jpg"
                public_url = self.upload_to_supabase(
                    file_data=frame_data,
                    filename=filename,
                    content_type='image/jpeg'
                )
                
                if public_url:
                    frame_urls.append(public_url)
                    frame_bytes_list.append(frame_data)  # Keep raw bytes!
            
            logger.info(f"Processed {len(frame_urls)} frames for video {video_url} (kept {len(frame_bytes_list)} bytes)")
            return frame_urls, frame_bytes_list
            
        except Exception as e:
            logger.error(f"Failed to process video frames from {video_url}: {e}")
            return [], []
    
    def process_image(
        self,
        image_url: str,
        post_id: str,
        media_index: int = 0
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[bytes]]:
        """
        Download image, upload to Supabase Storage, convert to base64, and return raw bytes.
        
        Args:
            image_url: URL of the image
            post_id: Post ID for filename
            media_index: Index of media item (for multiple images)
            
        Returns:
            Tuple of (supabase_url, base64_data, base64_mime_type, raw_bytes) or (None, None, None, None) if failed
        """
        try:
            # Download image ONCE - keep bytes in memory
            image_data = self.download_image(image_url)
            if not image_data:
                return None, None, None, None
            
            # Detect content type
            content_type = self._detect_content_type(image_url, image_data)
            
            # Generate filename
            extension = self._get_extension_from_content_type(content_type) or 'jpg'
            filename = f"images/{post_id}/image_{media_index}.{extension}"
            
            # Upload to Supabase
            public_url = self.upload_to_supabase(
                file_data=image_data,
                filename=filename,
                content_type=content_type
            )
            
            # Convert to base64 for GPT-4o (while we have the image_data in memory)
            # This avoids re-downloading the image later!
            base64_data = base64.b64encode(image_data).decode('utf-8')
            
            # Return Supabase URL, base64 data, content type, AND raw bytes (for Gemini)
            return public_url, base64_data, content_type, image_data
            
        except Exception as e:
            logger.error(f"Failed to process image {image_url}: {e}")
            return None
    
    def _detect_content_type(self, url: str, data: bytes) -> str:
        """Detect content type from URL or file data."""
        # Try from URL extension
        url_lower = url.lower()
        if url_lower.endswith('.png'):
            return 'image/png'
        elif url_lower.endswith('.gif'):
            return 'image/gif'
        elif url_lower.endswith('.webp'):
            return 'image/webp'
        
        # Try from file header
        if data.startswith(b'\x89PNG'):
            return 'image/png'
        elif data.startswith(b'GIF'):
            return 'image/gif'
        elif data.startswith(b'RIFF') and b'WEBP' in data[:12]:
            return 'image/webp'
        
        # Default to JPEG
        return 'image/jpeg'
    
    def _get_extension_from_content_type(self, content_type: str) -> Optional[str]:
        """Get file extension from content type."""
        mapping = {
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/webp': 'webp',
        }
        return mapping.get(content_type)
    
    def extract_audio_from_youtube(
        self,
        video_id: str,
        max_duration: int = 180
    ) -> Optional[bytes]:
        """
        Extract first N seconds of audio from YouTube video and convert to MP3.
        
        Uses yt-dlp to get video stream URL, then FFmpeg to extract audio.
        Similar approach to frame extraction for consistency.
        
        Args:
            video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
            max_duration: Maximum duration in seconds to extract (default: 180 = 3 minutes)
            
        Returns:
            Audio data as bytes (MP3), or None if failed
        """
        try:
            # Step 1: Get video stream URL using yt-dlp (same as frame extraction)
            ytdlp_cmd = [
                'yt-dlp',
                '-f', 'best[height<=720]',  # Get 720p or lower (faster)
                '-g',  # Get URL only (don't download)
                '--no-warnings',
                f'https://www.youtube.com/watch?v={video_id}'
            ]
            
            ytdlp_result = subprocess.run(
                ytdlp_cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            
            video_stream_url = ytdlp_result.stdout.strip()
            if not video_stream_url:
                logger.warning(f"No video stream URL returned for YouTube {video_id}")
                return None
            
            # Step 2: Extract audio using FFmpeg (immediate - before URL expires)
            # -ss 0: Start from beginning
            # -t {max_duration}: Extract up to max_duration seconds
            # -vn: No video
            # -acodec libmp3lame: MP3 codec
            # -ar 16000: Sample rate 16kHz (good for speech)
            # -ac 1: Mono (smaller file)
            # -f mp3: Output format
            # pipe:1: Output to stdout
            
            ffmpeg_cmd = [
                'ffmpeg',
                '-ss', '0',  # Start from beginning
                '-i', video_stream_url,  # Input video stream URL
                '-t', str(max_duration),  # Extract up to max_duration seconds
                '-vn',  # No video
                '-acodec', 'libmp3lame',  # MP3 codec
                '-ar', '16000',  # Sample rate 16kHz (good for speech)
                '-ac', '1',  # Mono (smaller file)
                '-f', 'mp3',  # Output format
                '-timeout', '5000000',  # 5 second timeout (microseconds)
                'pipe:1'  # Output to stdout
            ]
            
            ffmpeg_result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                timeout=60,  # 60 second timeout
                check=True
            )
            
            if ffmpeg_result.stdout:
                audio_bytes = ffmpeg_result.stdout
                logger.info(f"✅ Extracted {len(audio_bytes)} bytes of audio (max {max_duration}s) from YouTube {video_id}")
                return audio_bytes
            
            return None
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout extracting audio from YouTube {video_id} (max {max_duration}s)")
            return None
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.warning(f"Error extracting audio from YouTube {video_id}: {error_msg[:200]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error extracting audio from YouTube {video_id}: {e}")
            return None
    
    def extract_audio_from_video(
        self,
        video_url: str,
        max_duration: int = 180,
        output_format: str = 'mp3'
    ) -> Optional[bytes]:
        """
        Extract first N seconds of audio from video URL and convert to MP3.
        
        Args:
            video_url: Direct video URL (Instagram, Twitter, YouTube)
            max_duration: Maximum duration in seconds to extract (default: 180 = 3 minutes)
            output_format: Audio format ('mp3', 'wav', etc.)
            
        Returns:
            Audio data as bytes (MP3), or None if failed
        """
        try:
            # Use FFmpeg to extract audio
            # -ss 0: Start from beginning
            # -t {max_duration}: Extract up to max_duration seconds
            # -vn: No video
            # -acodec libmp3lame: MP3 codec
            # -ar 16000: Sample rate 16kHz (good for speech, smaller file)
            # -ac 1: Mono (smaller file, fine for speech)
            # -f mp3: Output format
            # pipe:1: Output to stdout
            
            cmd = [
                'ffmpeg',
                '-ss', '0',  # Start from beginning
                '-i', video_url,  # Input video URL
                '-t', str(max_duration),  # Extract up to max_duration seconds
                '-vn',  # No video
                '-acodec', 'libmp3lame',  # MP3 codec
                '-ar', '16000',  # Sample rate 16kHz (good for speech)
                '-ac', '1',  # Mono (smaller file)
                '-f', 'mp3',  # Output format
                '-y',  # Overwrite output file (not needed for pipe, but safe)
                'pipe:1'  # Output to stdout
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=60,  # 60 second timeout (should be enough for 3 min extraction)
                check=True
            )
            
            if result.stdout:
                audio_bytes = result.stdout
                logger.info(f"✅ Extracted {len(audio_bytes)} bytes of audio (max {max_duration}s) from {video_url[:100]}")
                return audio_bytes
            
            return None
            
        except subprocess.TimeoutExpired:
            logger.warning(f"Timeout extracting audio from {video_url[:100]} (max {max_duration}s)")
            return None
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr.decode() if e.stderr else str(e)
            logger.warning(f"FFmpeg error extracting audio: {error_msg[:200]}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error extracting audio from {video_url[:100]}: {e}")
            return None
    
    
    def extract_and_transcribe_video(
        self,
        video_url: str,
        max_duration: int = 180,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract audio from video and transcribe using Whisper AI.
        
        Convenience method that combines audio extraction and transcription.
        
        Args:
            video_url: Direct video URL
            max_duration: Maximum duration in seconds to extract (default: 180 = 3 minutes)
            language: Optional language code for transcription
            
        Returns:
            Transcribed text, or None if failed
        """
        try:
            # Extract audio
            audio_bytes = self.extract_audio_from_video(video_url, max_duration)
            if not audio_bytes:
                logger.warning(f"Could not extract audio from {video_url[:100]}, skipping transcription")
                return None
            
            # Transcribe using Whisper service
            transcript = transcribe_audio_with_whisper(audio_bytes, language)
            return transcript
            
        except Exception as e:
            logger.error(f"Failed to extract and transcribe video {video_url[:100]}: {e}")
            return None
    
    def extract_and_transcribe_youtube(
        self,
        video_id: str,
        max_duration: int = 180,
        language: Optional[str] = None
    ) -> Optional[str]:
        """
        Extract audio from YouTube video and transcribe using Whisper AI.
        
        Convenience method for YouTube videos that combines audio extraction and transcription.
        
        Args:
            video_id: YouTube video ID
            max_duration: Maximum duration in seconds to extract (default: 180 = 3 minutes)
            language: Optional language code for transcription
            
        Returns:
            Transcribed text, or None if failed
        """
        try:
            # Extract audio from YouTube
            audio_bytes = self.extract_audio_from_youtube(video_id, max_duration)
            if not audio_bytes:
                logger.warning(f"Could not extract audio from YouTube {video_id}, skipping transcription")
                return None
            
            # Transcribe using Whisper service
            transcript = transcribe_audio_with_whisper(audio_bytes, language)
            return transcript
            
        except Exception as e:
            logger.error(f"Failed to extract and transcribe YouTube {video_id}: {e}")
            return None



