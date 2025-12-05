"""
Chat Streaming Service for PostBro

Handles streaming chat responses from Gemini following best practices:
1. Save user message IMMEDIATELY (before API call)
2. Stream chunks to frontend in real-time
3. Accumulate full response in backend
4. Save AI response AFTER streaming completes
"""

import os
import logging
import time
import json
from typing import Generator, Dict, Optional
from django.core.exceptions import PermissionDenied, ObjectDoesNotExist

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
            "Neither 'google-genai' nor 'google.generativeai' package is installed.\n"
            "Install with: pip install google-genai\n"
            "Or: pip install google-generativeai"
        )

from analytics.tasks import log_external_api_call
from .chat_context_builder import build_chat_prompt, get_system_prompt
from ..models import ChatSession, ChatMessage
from accounts.utils import increment_usage

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
    client = None


def stream_chat_message(session_id: str, user_message: str, user_id: str) -> Generator[str, None, Dict]:
    """
    Stream chat response from Gemini following best practices.
    
    Flow:
    1. Save user message IMMEDIATELY (before API call)
    2. Stream chunks to frontend (yield each chunk)
    3. Accumulate full response in backend
    4. Save AI response AFTER streaming completes
    
    Args:
        session_id: ChatSession UUID
        user_message: User's message text
        user_id: User ID for validation and analytics
    
    Yields:
        JSON strings in SSE format: "data: {...}\n\n"
        - Chunks: {"chunk": "text", "type": "chunk"}
        - Done: {"done": True, "message_id": "...", "tokens_used": 123}
        - Error: {"error": "message", "type": "error"}
    
    Returns:
        Dictionary with final message data (after streaming completes)
    """
    if not GEMINI_API_KEY:
        yield f"data: {json.dumps({'error': 'GEMINI_API_KEY not configured', 'type': 'error'})}\n\n"
        return
    
    if not user_message or not user_message.strip():
        yield f"data: {json.dumps({'error': 'Message cannot be empty', 'type': 'error'})}\n\n"
        return
    
    start_time = time.time()
    full_response = ""  # Accumulate full response
    tokens_used = None
    user_msg = None
    assistant_msg = None
    
    try:
        # Get chat session with related objects
        session = ChatSession.objects.select_related(
            'post_analysis',
            'post_analysis__post',
            'post_analysis__post__platform',
            'user'
        ).prefetch_related('messages').get(id=session_id)
        
        # Validate user owns the session
        if str(session.user.id) != str(user_id):
            yield f"data: {json.dumps({'error': 'Permission denied', 'type': 'error'})}\n\n"
            return
        
        # Get post (via post_analysis for now, will be direct post link later)
        post = session.post_analysis.post
        
        # Get previous messages (ordered by created_at)
        chat_history = session.messages.all().order_by('created_at')
        
        # ============================================
        # STEP 1: Save User Message IMMEDIATELY
        # ============================================
        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_message.strip(),
            tokens_used=None  # User messages don't use tokens
        )
        
        logger.info(f"💾 [ChatStream] Saved user message immediately: {user_msg.id}")
        
        # Increment question usage (questions are tracked per user, platform doesn't matter)
        # Use the post's platform for consistency
        platform = post.platform.name.lower() if post.platform else 'instagram'
        increment_usage(session.user, platform, 'questions_asked')
        logger.info(f"📊 [ChatStream] Incremented question usage for user {user_id}")
        
        # Build chat prompt
        system_prompt = get_system_prompt()
        user_prompt = build_chat_prompt(
            post=post,
            user_message=user_message.strip(),
            chat_history=chat_history
        )
        
        logger.info(f"💬 [ChatStream] Starting stream for session {session_id}")
        logger.info(f"📝 [ChatStream] System prompt length: {len(system_prompt)} chars")
        logger.info(f"📝 [ChatStream] User prompt length: {len(user_prompt)} chars")
        logger.info(f"📝 [ChatStream] Chat history: {chat_history.count()} previous messages")
        
        # ============================================
        # STEP 2: Start Streaming from Gemini
        # ============================================
        model_name = 'gemini-2.5-flash'
        
        if USE_NEW_SDK:
            # New SDK - use streaming API
            # The new SDK accepts strings directly in contents array (like playground script)
            contents = [user_prompt]
            
            # Use generate_content_stream for streaming
            response_stream = client.models.generate_content_stream(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                ),
            )
            
            # ============================================
            # STEP 3: Process Stream Chunks
            # ============================================
            chunk_count = 0
            for chunk in response_stream:
                # Extract text from chunk
                if hasattr(chunk, 'text') and chunk.text:
                    text_chunk = chunk.text
                    full_response += text_chunk
                    chunk_count += 1
                    
                    logger.info(f"📤 [ChatStream] Sending chunk #{chunk_count}, length: {len(text_chunk)} chars, total: {len(full_response)} chars")
                    logger.debug(f"📤 [ChatStream] Chunk content preview: {text_chunk[:50]}...")
                    
                    # Yield chunk to frontend (real-time)
                    chunk_data = json.dumps({'chunk': text_chunk, 'type': 'chunk'})
                    logger.debug(f"📤 [ChatStream] Chunk JSON length: {len(chunk_data)}")
                    yield f"data: {chunk_data}\n\n"
                else:
                    logger.debug(f"⚠️ [ChatStream] Chunk has no text attribute or empty text")
                
                # Extract token usage if available
                if hasattr(chunk, 'usage_metadata') and chunk.usage_metadata:
                    usage = chunk.usage_metadata
                    tokens_used = getattr(usage, 'total_token_count', None)
                    if tokens_used:
                        logger.info(f"📊 [ChatStream] Token usage from chunk: {tokens_used}")
            
            logger.info(f"📊 [ChatStream] Total chunks sent: {chunk_count}")
        else:
            # Traditional SDK - check if streaming is supported
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt
            )
            
            # Traditional SDK may not support streaming, fallback to non-streaming
            response = model.generate_content(
                contents=user_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,
                )
            )
            
            response_text = response.text
            full_response = response_text
            
            # Extract token usage
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                tokens_used = getattr(usage, 'total_token_count', None)
            
            # For non-streaming SDK, send full response as single chunk
            yield f"data: {json.dumps({'chunk': full_response, 'type': 'chunk'})}\n\n"
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ [ChatStream] Stream completed in {processing_time:.2f}s")
        logger.info(f"📊 [ChatStream] Response length: {len(full_response)} chars")
        if tokens_used:
            logger.info(f"📊 [ChatStream] Tokens used: {tokens_used}")
        
        # ============================================
        # STEP 4: Save AI Response AFTER Streaming Completes
        # ============================================
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=full_response,  # Full accumulated text
            tokens_used=tokens_used
        )
        
        # Update session metrics (non-blocking, simple DB update)
        session.messages_count = session.messages.count()
        if tokens_used:
            session.total_tokens = (session.total_tokens or 0) + tokens_used
        
        # Calculate duration: time from first to last message
        messages = session.messages.order_by('created_at')
        first_message = messages.first()
        last_message = messages.last()
        if first_message and last_message and first_message != last_message:
            duration = (last_message.created_at - first_message.created_at).total_seconds()
            session.duration_seconds = duration
        elif first_message and last_message:
            # Only one message, duration is 0
            session.duration_seconds = 0.0
        
        session.save(update_fields=['updated_at', 'messages_count', 'total_tokens', 'duration_seconds'])
        
        logger.info(f"💾 [ChatStream] Saved assistant message after streaming: {assistant_msg.id}")
        
        # Log API call for analytics (async, non-blocking)
        try:
            usage_info = {}
            if tokens_used:
                usage_info = {
                    'total_tokens': tokens_used,
                    'candidates_tokens': tokens_used,  # Chat responses are output tokens
                }
            
            log_external_api_call.delay(
                user_id=user_id,
                service='gemini',
                endpoint=f'/v1/models/gemini-2.5-flash:streamGenerateContent',
                method='POST',
                status_code=200,
                response_time_ms=int(processing_time * 1000),
                cost_estimate=None,  # Calculate in admin app
                response_size_bytes=len(full_response.encode('utf-8')) if full_response else None,
                metadata={
                    'model': 'gemini-2.5-flash',
                    'usage': usage_info,
                    'chat_session_id': str(session_id),  # Link to chat session
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ [ChatStream] Failed to log API call: {e}")
        
        # Yield final message
        final_data = {
            'done': True,
            'type': 'done',
            'message_id': str(assistant_msg.id),
            'tokens_used': tokens_used,
            'processing_time_seconds': processing_time
        }
        yield f"data: {json.dumps(final_data)}\n\n"
        
        return {
            'user_message': {
                'id': str(user_msg.id),
                'role': user_msg.role,
                'content': user_msg.content,
                'created_at': user_msg.created_at.isoformat(),
            },
            'assistant_message': {
                'id': str(assistant_msg.id),
                'role': assistant_msg.role,
                'content': assistant_msg.content,
                'tokens_used': assistant_msg.tokens_used,
                'created_at': assistant_msg.created_at.isoformat(),
            },
            'processing_time_seconds': processing_time,
        }
        
    except ChatSession.DoesNotExist:
        logger.error(f"❌ [ChatStream] Session not found: {session_id}")
        yield f"data: {json.dumps({'error': 'Chat session not found', 'type': 'error'})}\n\n"
        return
    
    except PermissionDenied:
        yield f"data: {json.dumps({'error': 'Permission denied', 'type': 'error'})}\n\n"
        return
    
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ [ChatStream] Error processing message after {processing_time:.2f}s: {e}", exc_info=True)
        
        # If we have partial response, save it
        if full_response and user_msg:
            try:
                assistant_msg = ChatMessage.objects.create(
                    session=session,
                    role=ChatMessage.Role.ASSISTANT,
                    content=f"{full_response}\n\n[Error: Stream interrupted - {str(e)}]",
                    tokens_used=None
                )
                logger.info(f"💾 [ChatStream] Saved partial response due to error: {assistant_msg.id}")
            except:
                pass
        
        # Log failed API call
        try:
            log_external_api_call.delay(
                user_id=user_id,
                service='gemini',
                endpoint=f'/v1/models/gemini-2.5-flash:streamGenerateContent',
                method='POST',
                status_code=500,
                response_time_ms=int((time.time() - start_time) * 1000),
                error_message=str(e)[:1000],
                metadata={
                    'model': 'gemini-2.5-flash',
                    'chat_session_id': str(session_id),  # Link to chat session
                }
            )
        except Exception as log_error:
            logger.warning(f"⚠️ [ChatStream] Failed to log error: {log_error}")
        
        yield f"data: {json.dumps({'error': str(e), 'type': 'error'})}\n\n"
        return
