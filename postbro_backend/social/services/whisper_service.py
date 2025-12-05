"""
Whisper Transcription Service

This module provides audio transcription using OpenAI's Whisper API.
"""

import os
import logging
from typing import Optional
from io import BytesIO

logger = logging.getLogger(__name__)


def transcribe_audio_with_whisper(
    audio_bytes: bytes,
    language: Optional[str] = None
) -> Optional[str]:
    """
    Transcribe audio using OpenAI Whisper API.
    
    Args:
        audio_bytes: Audio data as bytes (MP3 format)
        language: Optional language code (e.g., 'en', 'es'). If None, auto-detect.
        
    Returns:
        Transcribed text, or None if failed
    """
    try:
        from openai import OpenAI
        
        # Get API key from environment
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            logger.warning("OPENAI_API_KEY not set, skipping Whisper transcription")
            return None
        
        # Initialize OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Create a temporary file-like object from bytes
        audio_file = BytesIO(audio_bytes)
        audio_file.name = 'audio.mp3'  # Required by OpenAI API
        
        # Call Whisper API
        logger.info(f"🎤 Transcribing {len(audio_bytes)} bytes of audio with Whisper...")
        transcript = client.audio.transcriptions.create(
            model='whisper-1',
            file=audio_file,
            language=language,  # None = auto-detect
            response_format='text'  # Get plain text
        )
        
        if transcript:
            transcript_text = transcript.strip() if isinstance(transcript, str) else str(transcript).strip()
            logger.info(f"✅ Whisper transcription completed: {len(transcript_text)} characters")
            return transcript_text
        
        return None
        
    except ImportError:
        logger.error("OpenAI library not installed. Install with: pip install openai")
        return None
    except Exception as e:
        logger.error(f"Failed to transcribe audio with Whisper: {e}")
        return None

