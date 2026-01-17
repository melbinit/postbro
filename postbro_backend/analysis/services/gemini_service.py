"""
Gemini AI Service for Post Analysis
Uses Gemini 2.5 Flash to analyze social media posts
"""

import os
import json
import logging
import time
from typing import Dict, List, Optional

# Try new SDK first, fallback to traditional
try:
    from google import genai
    from google.genai import types
    USE_NEW_SDK = True
except ImportError:
    try:
        import google.generativeai as genai
        USE_NEW_SDK = False
    except ImportError:
        raise ImportError(
            "Neither 'google-genai' nor 'google-generativeai' package is installed.\n"
            "Install with: pip install google-genai\n"
            "Or: pip install google-generativeai"
        )

from analytics.tasks import log_external_api_call
from .prompt_utils import get_system_prompt, build_user_prompt

logger = logging.getLogger(__name__)

# Load Gemini API key
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY_1') or os.getenv('GEMINI_API_KEY')
if not GEMINI_API_KEY:
    logger.warning("GEMINI_API_KEY_1 or GEMINI_API_KEY not found in environment")

# Initialize client based on SDK version
if USE_NEW_SDK:
    client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
else:
    if GEMINI_API_KEY:
        genai.configure(api_key=GEMINI_API_KEY)
    client = None  # Traditional SDK doesn't use a client object


def analyze_post_with_gemini(
    platform: str,
    task_id: str,
    post_data: Dict,
    media_images: List[Dict],  # List of dicts: [{'bytes': bytes, 'mime_type': str}, ...] (includes images + video frames)
    video_length: Optional[int] = None,
    transcript: Optional[str] = None,
    user_id: Optional[str] = None,
    analysis_request_id: Optional[str] = None,  # For linking to analysis request in logs
    post_id: Optional[str] = None,  # For linking to post in logs
) -> Dict:
    """
    Analyze a post using Gemini 2.5 Flash
    
    Args:
        platform: Platform name (instagram, x, youtube)
        task_id: Task ID for this analysis
        post_data: Post data dictionary with username, caption, metrics, etc.
        media_images: List of media dicts with 'bytes' and 'mime_type' keys (includes images + video frames)
        video_length: Video length in seconds (for YouTube)
        transcript: Video transcript (for YouTube)
    
    Returns:
        Dictionary with analysis results matching the JSON schema
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")
    
    start_time = time.time()
    response_text = ""  # Initialize for error handling
    
    try:
        # Build prompts using shared utilities
        system_prompt = get_system_prompt()
        # Build user prompt without media URLs (we'll pass images directly)
        user_prompt = build_user_prompt(
            platform=platform,
            task_id=task_id,
            username=post_data.get('username', ''),
            caption=post_data.get('caption', '') or post_data.get('content', ''),
            posted_at=post_data.get('posted_at', ''),
            metrics=post_data.get('metrics', {}),
            latest_comments=post_data.get('latest_comments', []),
            media_urls=[],  # Empty - we pass images + frames directly as bytes
            video_length=video_length,
            transcript=transcript,
        )
        
        # Initialize Gemini model
        model_name = 'gemini-2.5-flash'
        logger.info(f"🤖 [Gemini] Initializing model: {model_name} for task {task_id}")
        logger.info(f"📝 [Gemini] System prompt length: {len(system_prompt)} chars")
        logger.info(f"📝 [Gemini] User prompt length: {len(user_prompt)} chars")
        
        # v2 prompt outputs conversational markdown (no JSON instruction needed)
        enhanced_system_prompt = system_prompt
        
        # Initialize model based on SDK version
        if USE_NEW_SDK:
            # New SDK - model is accessed via client
            model = None  # Will use client.models.generate_content directly
        else:
            # Traditional SDK
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=enhanced_system_prompt
            )
        
        # Call Gemini with retry logic for rate limits
        logger.info(f"🚀 [Gemini] Calling Gemini API for post analysis (task_id: {task_id}, platform: {platform})")
        api_call_start = time.time()
        
        max_retries = 3
        retry_delay = 10  # seconds
        response = None
        api_error = None
        status_code = 200
        
        # Get user_id from post_data if available (for tracking)
        user_id = post_data.get('user_id') if isinstance(post_data, dict) else None
        
        for attempt in range(max_retries):
            try:
                # v2 prompt already includes markdown format instructions - no JSON instruction needed
                # The v2.txt prompt explicitly says "DO NOT return JSON" and asks for markdown
                enhanced_user_prompt = user_prompt  # Use prompt as-is from v2.txt
                
                # Build content array: text prompt + labeled media parts
                if USE_NEW_SDK:
                    # New SDK: Match playground script exactly - download bytes and send as Part objects
                    # Playground format: contents = image_parts + [user_prompt] (mixing Part objects with string)
                    image_parts = []
                    
                    if media_images:
                        # Count images vs frames
                        image_count = sum(1 for img in media_images if img.get('media_type') != 'video_frame')
                        frame_count = sum(1 for img in media_images if img.get('media_type') == 'video_frame')
                        logger.info(f"🖼️ [Gemini] Preparing {image_count} image(s) and {frame_count} video frame(s) for analysis")
                        
                        # Track video frame counts per video for labeling
                        video_frame_counts = {}  # video_index -> count
                        image_count = 0
                        
                        for idx, img_data in enumerate(media_images):
                            image_bytes = img_data['bytes']
                            mime_type = img_data.get('mime_type', 'image/jpeg')  # Default to JPEG like playground
                            media_type = img_data.get('media_type', 'image')
                            video_index = img_data.get('video_index')  # Which video this frame belongs to (if frame)
                            
                            # Validate bytes before sending
                            if not image_bytes or len(image_bytes) == 0:
                                logger.warning(f"⚠️ [Gemini] Skipping empty {media_type} bytes")
                                continue
                            
                            # Validate with PIL (silent unless error)
                            try:
                                from PIL import Image
                                from io import BytesIO
                                pil_image = Image.open(BytesIO(image_bytes))
                                pil_image.verify()
                                pil_image = Image.open(BytesIO(image_bytes))
                            except Exception as pil_error:
                                logger.error(f"❌ [Gemini] PIL validation failed for {media_type}: {pil_error}")
                                logger.error(f"   Bytes length: {len(image_bytes)}, first 200 chars: {image_bytes[:200].decode('utf-8', errors='ignore')}")
                                continue
                            
                            # Detect MIME type from magic bytes, default to JPEG
                            if image_bytes.startswith(b'\xff\xd8\xff'):  # JPEG
                                mime_type = 'image/jpeg'
                            elif image_bytes.startswith(b'\x89PNG\r\n\x1a\n'):  # PNG
                                mime_type = 'image/png'
                            elif image_bytes.startswith(b'GIF87a') or image_bytes.startswith(b'GIF89a'):  # GIF
                                mime_type = 'image/gif'
                            elif image_bytes.startswith(b'RIFF') and b'WEBP' in image_bytes[:20]:  # WEBP
                                mime_type = 'image/webp'
                            else:
                                mime_type = 'image/jpeg'  # Default to JPEG
                            
                            # Create label text before media item (for Gemini to understand context)
                            if media_type == 'video_frame':
                                # Track frame count per video
                                if video_index not in video_frame_counts:
                                    video_frame_counts[video_index] = 0
                                video_frame_counts[video_index] += 1
                                frame_num = video_frame_counts[video_index]
                                
                                # Count total frames for this video
                                total_frames_for_video = sum(1 for img in media_images if img.get('video_index') == video_index and img.get('media_type') == 'video_frame')
                                
                                if video_index:
                                    label_text = f"\n[Video {video_index} - Frame {frame_num} of {total_frames_for_video}]\n"
                                else:
                                    label_text = f"\n[Video Frame {frame_num} of {total_frames_for_video}]\n"
                                
                                # Add label as text Part before the frame
                                image_parts.append(types.Part.from_text(text=label_text))
                            else:
                                # For images, add simple label
                                image_count += 1
                                total_images = sum(1 for img in media_images if img.get('media_type') != 'video_frame')
                                label_text = f"\n[Image {image_count} of {total_images}]\n"
                                image_parts.append(types.Part.from_text(text=label_text))
                            
                            # Create Part.from_bytes exactly like playground script
                            try:
                                # Validate minimum size (at least 100 bytes for a valid image)
                                if len(image_bytes) < 100:
                                    logger.warning(f"⚠️ [Gemini] Image too small ({len(image_bytes)} bytes), skipping {media_type}")
                                    continue
                                
                                image_part = types.Part.from_bytes(
                                    data=image_bytes,
                                    mime_type=mime_type
                                )
                                image_parts.append(image_part)
                            except Exception as part_error:
                                logger.error(f"❌ [Gemini] Failed to create Part.from_bytes for {media_type}: {part_error}")
                                logger.error(f"   Bytes length: {len(image_bytes)}, mime_type: {mime_type}, first 20 bytes (hex): {image_bytes[:20].hex()}")
                                continue
                    
                    # Build contents exactly like playground: image_parts + [user_prompt]
                    contents = image_parts + [enhanced_user_prompt]
                    
                    logger.info(f"📤 [Gemini] Sending {len(image_parts)} media parts + 1 text prompt to Gemini API")
                    
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=contents,
                        config=types.GenerateContentConfig(
                            system_instruction=enhanced_system_prompt,
                            temperature=0.4,
                            # v2 outputs markdown, not JSON
                            # response_mime_type='text/plain',  # Not needed - default is text
                        ),
                        )
                    except Exception as api_error:
                        logger.error(f"❌ [Gemini] API call failed: {api_error}")
                        logger.error(f"   Media parts: {len(image_parts)}, contents length: {len(contents)}")
                        raise
                else:
                    # Traditional SDK: Use inline_data format with base64
                    parts = [{'text': enhanced_user_prompt}]
                    
                    if media_images:
                        # Count images vs frames
                        image_count = sum(1 for img in media_images if img.get('media_type') != 'video_frame')
                        frame_count = sum(1 for img in media_images if img.get('media_type') == 'video_frame')
                        logger.info(f"🖼️ [Gemini] Including {image_count} image(s) and {frame_count} video frame(s) as base64 (traditional SDK)")
                        
                        import base64
                        image_idx = 0
                        frame_idx = 0
                        for img_data in media_images:
                            image_bytes = img_data['bytes']
                            mime_type = img_data['mime_type']
                            media_type = img_data.get('media_type', 'image')
                            
                            # Add text label before each media item to distinguish images from frames
                            if media_type == 'video_frame':
                                frame_idx += 1
                                parts.append({'text': f"\n[Video Frame {frame_idx} of {frame_count}]\n"})
                            else:
                                image_idx += 1
                                parts.append({'text': f"\n[Image {image_idx} of {image_count}]\n"})
                            
                            # Encode bytes to base64 for inline_data format
                            base64_data = base64.b64encode(image_bytes).decode('utf-8')
                            parts.append({
                                'inline_data': {
                                    'mime_type': mime_type,
                                    'data': base64_data
                                }
                            })
                    
                    # Build contents array with parts
                    contents = [{'parts': parts}]
                    
                    response = model.generate_content(
                        contents,  # Pass array with text + images
                        generation_config=genai.GenerationConfig(
                            # v2 outputs markdown, not JSON
                            # response_mime_type="text/plain",  # Not needed - default is text
                            temperature=0.4,
                        )
                    )
                api_call_time = time.time() - api_call_start
                logger.info(f"✅ [Gemini] API call completed in {api_call_time:.2f}s (attempt {attempt + 1})")
                break  # Success, exit retry loop
            except Exception as api_error:
                error_str = str(api_error).lower()
                api_call_time = time.time() - api_call_start
                
                # Determine status code from error
                if '429' in error_str or 'quota' in error_str or 'rate limit' in error_str:
                    status_code = 429
                elif '401' in error_str or 'unauthorized' in error_str:
                    status_code = 401
                elif '403' in error_str or 'forbidden' in error_str:
                    status_code = 403
                else:
                    status_code = 500
                
                # Check if it's a rate limit/quota error
                if '429' in error_str or 'quota' in error_str or 'rate limit' in error_str or 'resourceexhausted' in error_str:
                    if attempt < max_retries - 1:
                        # Extract retry delay from error if available
                        if 'retry in' in error_str:
                            try:
                                import re
                                delay_match = re.search(r'retry in ([\d.]+)s', error_str)
                                if delay_match:
                                    retry_delay = float(delay_match.group(1)) + 2  # Add 2s buffer
                            except:
                                pass
                        
                        logger.warning(f"⚠️ [Gemini] Rate limit/quota error (attempt {attempt + 1}/{max_retries}). Retrying in {retry_delay}s...")
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        logger.error(f"❌ [Gemini] Rate limit/quota error after {max_retries} attempts")
                        # Log failed API call
                        try:
                            log_external_api_call.delay(
                                user_id=user_id,
                                service='gemini',
                                endpoint=f'/v1/models/{model_name}:generateContent',
                                method='POST',
                                status_code=status_code,
                                response_time_ms=int(api_call_time * 1000),
                                error_message=str(api_error)[:1000],
                                metadata={
                                    'task_id': task_id,
                                    'platform': platform,
                                    'attempt': attempt + 1,
                                    'analysis_request_id': analysis_request_id,
                                    'post_id': post_id,
                                }
                            )
                        except Exception:
                            pass
                        raise
                else:
                    # Not a rate limit error, raise immediately
                    # Log failed API call
                    try:
                        log_external_api_call.delay(
                            user_id=user_id,
                            service='gemini',
                            endpoint=f'/v1/models/{model_name}:generateContent',
                            method='POST',
                            status_code=status_code,
                            response_time_ms=int(api_call_time * 1000),
                            error_message=str(api_error)[:1000],
                            metadata={
                                'task_id': task_id,
                                'platform': platform,
                                'analysis_request_id': analysis_request_id,
                                'post_id': post_id,
                            }
                        )
                    except Exception:
                        pass
                    raise
        
        if not response:
            raise ValueError("Failed to get response from Gemini API after retries")
        
        # Extract usage metadata if available
        usage_info = {}
        if hasattr(response, 'usage_metadata'):
            usage_info = {
                'prompt_tokens': getattr(response.usage_metadata, 'prompt_token_count', 0),
                'candidates_tokens': getattr(response.usage_metadata, 'candidates_token_count', 0),
                'total_tokens': getattr(response.usage_metadata, 'total_token_count', 0),
            }
            logger.info(f"📊 [Gemini] Token usage: {usage_info['total_tokens']} total "
                      f"({usage_info['prompt_tokens']} prompt + {usage_info['candidates_tokens']} response)")
        else:
            logger.warning("⚠️ [Gemini] Usage metadata not available in response")
        
        # Check if response has valid text content before accessing it
        if not hasattr(response, 'text') or response.text is None or not response.text.strip():
            # Response is empty or blocked - gather diagnostic information
            logger.error("❌ [Gemini] Response text is empty or None")
            
            # Log the full response object for debugging
            logger.error(f"🔍 [Gemini] Full response object type: {type(response)}")
            logger.error(f"🔍 [Gemini] Response attributes: {dir(response)}")
            
            # Try to extract finish_reason and safety info
            finish_reason = None
            safety_info = []
            blocked_reasons = []
            
            try:
                if hasattr(response, 'candidates') and response.candidates:
                    candidate = response.candidates[0]
                    logger.error(f"🔍 [Gemini] Candidate attributes: {dir(candidate)}")
                    
                    # Get finish reason
                    if hasattr(candidate, 'finish_reason'):
                        finish_reason = str(candidate.finish_reason)
                        logger.error(f"🔍 [Gemini] Finish reason: {finish_reason}")
                    
                    # Get safety ratings
                    if hasattr(candidate, 'safety_ratings'):
                        for rating in candidate.safety_ratings:
                            category = getattr(rating, 'category', 'UNKNOWN')
                            probability = getattr(rating, 'probability', 'UNKNOWN')
                            blocked = getattr(rating, 'blocked', False)
                            
                            rating_info = f"{category}: {probability} (blocked={blocked})"
                            safety_info.append(rating_info)
                            
                            if blocked or str(probability) in ['HIGH', 'MEDIUM']:
                                blocked_reasons.append(f"{category}:{probability}")
                        
                        logger.error(f"🔍 [Gemini] Safety ratings: {safety_info}")
                    
                    # Get content if available
                    if hasattr(candidate, 'content'):
                        content = candidate.content
                        logger.error(f"🔍 [Gemini] Content type: {type(content)}")
                        if hasattr(content, 'parts'):
                            logger.error(f"🔍 [Gemini] Content parts: {len(content.parts)} parts")
                            for i, part in enumerate(content.parts):
                                logger.error(f"🔍 [Gemini] Part {i}: {dir(part)}")
                else:
                    logger.error("🔍 [Gemini] No candidates in response")
                    
                # Try to get prompt_feedback if available
                if hasattr(response, 'prompt_feedback'):
                    feedback = response.prompt_feedback
                    logger.error(f"🔍 [Gemini] Prompt feedback: {feedback}")
                    if hasattr(feedback, 'block_reason'):
                        block_reason = str(feedback.block_reason)
                        logger.error(f"🔍 [Gemini] Prompt block reason: {block_reason}")
                        blocked_reasons.append(f"PROMPT_BLOCKED:{block_reason}")
                    if hasattr(feedback, 'safety_ratings'):
                        logger.error(f"🔍 [Gemini] Prompt safety ratings: {feedback.safety_ratings}")
            except Exception as inspect_error:
                logger.error(f"❌ [Gemini] Error inspecting response: {inspect_error}")
            
            # Build detailed error message
            error_msg = "Gemini returned empty response. "
            
            if finish_reason:
                error_msg += f"Finish reason: {finish_reason}. "
                
                # Map finish reasons to user-friendly messages
                if 'SAFETY' in finish_reason:
                    error_msg += "Content was blocked by safety filters. "
                elif 'MAX_TOKENS' in finish_reason or 'LENGTH' in finish_reason:
                    error_msg += "Response exceeded token limit. "
                elif 'RECITATION' in finish_reason:
                    error_msg += "Content too similar to training data. "
                elif 'OTHER' in finish_reason:
                    error_msg += "Generation stopped for other reasons. "
            
            if blocked_reasons:
                error_msg += f"Blocked reasons: {', '.join(blocked_reasons)}. "
            
            if safety_info:
                error_msg += f"Safety check results: {'; '.join(safety_info)}. "
            
            if not finish_reason and not blocked_reasons:
                error_msg += "Possible causes: content policy violation, safety filters, or API error. "
            
            error_msg += "The post content may have triggered Gemini's safety filters or content policies."
            
            logger.error(f"❌ [Gemini] {error_msg}")
            
            # Log the failed API call with detailed information
            api_call_time = time.time() - api_call_start
            try:
                log_external_api_call.delay(
                    user_id=user_id,
                    service='gemini',
                    endpoint=f'/v1/models/{model_name}:generateContent',
                    method='POST',
                    status_code=200,  # API returned 200 but content was blocked
                    response_time_ms=int(api_call_time * 1000),
                    error_message=error_msg[:1000],
                    metadata={
                        'task_id': task_id,
                        'platform': platform,
                        'analysis_request_id': analysis_request_id,
                        'post_id': post_id,
                        'finish_reason': finish_reason,
                        'blocked_reasons': blocked_reasons,
                        'safety_ratings': safety_info,
                        'error_type': 'empty_response',
                    }
                )
            except Exception:
                pass
            
            raise ValueError(error_msg)
        
        # v2 outputs markdown (not JSON) - save as raw response
        response_text = response.text.strip()
        original_response = response_text  # Full markdown response
        logger.info(f"📄 [Gemini] Received response: {len(response_text)} chars")
        
        # Log successful API call
        api_call_time = time.time() - api_call_start
        try:
            log_external_api_call.delay(
                user_id=user_id,
                service='gemini',
                endpoint=f'/v1/models/{model_name}:generateContent',
                method='POST',
                status_code=200,
                response_time_ms=int(api_call_time * 1000),
                cost_estimate=None,
                request_size_bytes=len(enhanced_user_prompt.encode('utf-8')) if 'enhanced_user_prompt' in locals() else None,
                response_size_bytes=len(response_text.encode('utf-8')) if response_text else None,
                metadata={
                    'task_id': task_id,
                    'platform': platform,
                    'model': model_name,
                    'usage': usage_info,
                    'analysis_request_id': analysis_request_id,  # Link to analysis request
                    'post_id': post_id,  # Link to post
                }
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        # v2 outputs markdown - we don't parse JSON anymore
        # Create minimal structured data for PostAnalysis (backward compatibility)
        # The full markdown will be saved as the first AI message
        parse_start = time.time()
        analysis_result = {
            'task_id': task_id,
            'is_viral': False,  # Default - can't determine from markdown easily
            'virality_reasoning': 'Analysis provided in markdown format',
            'quick_takeaways': [],
            'content_observation': {},
            'replicable_elements': [],
            'analysis': {
                'platform': platform,
                'strengths': [],
                'weaknesses': [],
                'deep_analysis': {}
            },
            'improvements': [],
            'suggestions_for_future_posts': [],
            'viral_formula': '',
            'metadata_used': {
                'platform': platform,
                'username': post_data.get('username', ''),
            }
        }
        parse_time = time.time() - parse_start
        logger.info(f"✅ [Gemini] Markdown response processed in {parse_time:.3f}s (no JSON parsing needed)")
        
        # v2 outputs markdown - structured fields are minimal/defaults
        logger.info(f"✅ [Gemini] Using minimal structured data for PostAnalysis (full markdown saved as chat message)")
        
        processing_time = time.time() - start_time
        logger.info(f"🎉 [Gemini] Analysis completed successfully in {processing_time:.2f}s total "
                    f"(API: {api_call_time:.2f}s, Parse: {parse_time:.3f}s)")
        
        # Add processing metadata
        analysis_result['_metadata'] = {
            'processing_time_seconds': processing_time,
            'api_call_time_seconds': api_call_time,
            'parse_time_seconds': parse_time,
            'model': model_name,  # Will be 'gemini-2.5-flash'
            'raw_response': original_response,
            'usage': usage_info,
        }
        
        return analysis_result
        
    except Exception as e:
        processing_time = time.time() - start_time
        error_type = type(e).__name__
        logger.error(f"❌ [Gemini] Error after {processing_time:.2f}s: {error_type} - {str(e)}")
        
        # Log response details if available
        if 'response' in locals() and response:
            try:
                logger.error(f"🔍 [Gemini] Response object available for inspection")
                logger.error(f"🔍 [Gemini] Response type: {type(response)}")
                if hasattr(response, 'text'):
                    logger.error(f"🔍 [Gemini] Response.text exists: {response.text is not None}")
                    if response.text:
                        logger.error(f"🔍 [Gemini] Response.text length: {len(response.text)}")
                        logger.error(f"🔍 [Gemini] Response preview: {response.text[:500]}...")
                else:
                    logger.error(f"🔍 [Gemini] Response has no 'text' attribute")
                
                # Log candidates info if available
                if hasattr(response, 'candidates'):
                    logger.error(f"🔍 [Gemini] Candidates count: {len(response.candidates) if response.candidates else 0}")
                    if response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, 'finish_reason'):
                            logger.error(f"🔍 [Gemini] Finish reason: {candidate.finish_reason}")
            except Exception as inspect_error:
                logger.error(f"❌ [Gemini] Error inspecting response object: {inspect_error}")
        elif 'response_text' in locals() and response_text:
            logger.error(f"   Response preview: {response_text[:500]}...")
        
        raise