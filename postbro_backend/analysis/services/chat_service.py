"""
Chat Service for PostBro

Handles chat conversations with Gemini for follow-up questions about post analyses.
"""

import os
import logging
import time
from typing import Dict, Optional
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
    client = None  # Traditional SDK doesn't use a client object


def send_chat_message(session_id: str, user_message: str, user_id: str) -> Dict:
    """
    Send a chat message and get AI response.
    
    Args:
        session_id: ChatSession UUID
        user_message: User's message text
        user_id: User ID for validation and analytics
    
    Returns:
        Dictionary with user_message and assistant_message data
    
    Raises:
        ObjectDoesNotExist: If session not found
        PermissionDenied: If user doesn't own the session
        ValueError: If message is empty or invalid
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not configured")
    
    if not user_message or not user_message.strip():
        raise ValueError("Message cannot be empty")
    
    start_time = time.time()
    
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
            raise PermissionDenied("You don't have permission to access this chat session")
        
        # Get post (via post_analysis for now, will be direct post link later)
        post = session.post_analysis.post
        
        # Get previous messages (ordered by created_at)
        chat_history = session.messages.all().order_by('created_at')
        
        # Build chat prompt
        system_prompt = get_system_prompt()
        user_prompt = build_chat_prompt(
            post=post,
            user_message=user_message.strip(),
            chat_history=chat_history
        )
        
        logger.info(f"💬 [Chat] Sending message to session {session_id}")
        logger.info(f"📝 [Chat] System prompt length: {len(system_prompt)} chars")
        logger.info(f"📝 [Chat] User prompt length: {len(user_prompt)} chars")
        logger.info(f"📝 [Chat] Chat history: {chat_history.count()} previous messages")
        
        # Call Gemini API
        model_name = 'gemini-2.5-flash'
        response_text = ""
        tokens_used = None
        
        if USE_NEW_SDK:
            # New SDK format
            # The new SDK accepts strings directly in contents array (like playground script)
            contents = [user_prompt]
            
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,  # Slightly higher for conversational responses
                ),
            )
            
            response_text = response.text
            
            # Extract token usage
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                tokens_used = getattr(usage, 'total_token_count', None)
        else:
            # Traditional SDK format
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt
            )
            
            response = model.generate_content(
                contents=user_prompt,
                generation_config=genai.GenerationConfig(
                    temperature=0.7,  # Slightly higher for conversational responses
                )
            )
            
            response_text = response.text
            
            # Extract token usage
            if hasattr(response, 'usage_metadata'):
                usage = response.usage_metadata
                tokens_used = getattr(usage, 'total_token_count', None)
        
        processing_time = time.time() - start_time
        
        logger.info(f"✅ [Chat] Received response in {processing_time:.2f}s")
        logger.info(f"📊 [Chat] Response length: {len(response_text)} chars")
        if tokens_used:
            logger.info(f"📊 [Chat] Tokens used: {tokens_used}")
        
        # Save user message
        user_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.USER,
            content=user_message.strip(),
            tokens_used=None  # User messages don't use tokens
        )
        
        # Increment question usage (questions are tracked per user, platform doesn't matter)
        # Use the post's platform for consistency
        platform = post.platform.name.lower() if post.platform else 'instagram'
        increment_usage(session.user, platform, 'questions_asked')
        logger.info(f"📊 [Chat] Incremented question usage for user {user_id}")
        
        # Save assistant response
        assistant_msg = ChatMessage.objects.create(
            session=session,
            role=ChatMessage.Role.ASSISTANT,
            content=response_text,
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
                endpoint=f'/v1/models/gemini-2.5-flash:generateContent',
                method='POST',
                status_code=200,
                response_time_ms=int(processing_time * 1000),
                cost_estimate=None,  # Calculate in admin app
                response_size_bytes=len(response_text.encode('utf-8')) if response_text else None,
                metadata={
                    'model': 'gemini-2.5-flash',
                    'usage': usage_info,
                    'chat_session_id': str(session_id),  # Link to chat session
                }
            )
        except Exception as e:
            logger.warning(f"⚠️ [Chat] Failed to log API call: {e}")
        
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
        logger.error(f"❌ [Chat] Session not found: {session_id}")
        raise ObjectDoesNotExist(f"Chat session {session_id} not found")
    
    except PermissionDenied:
        raise
    
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"❌ [Chat] Error processing message after {processing_time:.2f}s: {e}", exc_info=True)
        
        # Log failed API call (async, non-blocking)
        try:
            log_external_api_call.delay(
                user_id=user_id,
                service='gemini',
                endpoint=f'/v1/models/gemini-2.5-flash:generateContent',
                method='POST',
                status_code=500,
                response_time_ms=int(processing_time * 1000),
                error_message=str(e)[:1000],
                metadata={
                    'model': 'gemini-2.5-flash',
                    'chat_session_id': str(session_id),  # Link to chat session
                }
            )
        except Exception as log_error:
            logger.warning(f"⚠️ [Chat] Failed to log error: {log_error}")
        
        raise

