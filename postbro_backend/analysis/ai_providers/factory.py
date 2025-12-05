"""
AI Provider Factory

Factory pattern to get the appropriate AI provider based on settings.
"""

import logging
from django.conf import settings
from .self_hosted import SelfHostedProvider

logger = logging.getLogger(__name__)


def get_ai_provider():
    """
    Get AI provider based on settings.
    
    NOTE: Gemini is now handled directly via analysis.services.gemini_service
    This factory is kept for self-hosted provider support.
    
    Returns:
        AIProvider instance (SelfHostedProvider)
    
    Raises:
        ValueError: If provider type is unknown
    """
    provider_type = getattr(settings, 'AI_PROVIDER', 'gemini').lower()
    
    if provider_type == 'self_hosted':
        logger.info("Using self-hosted LLM provider")
        return SelfHostedProvider()
    
    elif provider_type == 'gemini':
        # Gemini is now handled directly via analysis.services.gemini_service
        # This is kept for backward compatibility
        logger.warning("AI_PROVIDER=gemini is deprecated. Gemini is now handled via gemini_service directly.")
        return None
    
    else:
        raise ValueError(
            f"Unknown AI provider: {provider_type}. "
            f"Set AI_PROVIDER to 'self_hosted' in settings."
        )



