"""
Base AI Provider Interface

All AI providers must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class AIProvider(ABC):
    """Base class for all AI providers"""
    
    @abstractmethod
    def analyze_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Optional[str]:
        """
        Analyze content using the AI provider.
        
        Args:
            prompt: The text prompt/instruction
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters
        
        Returns:
            Generated text response, or None if failed
        """
        pass
    
    @abstractmethod
    def analyze_with_vision(
        self,
        prompt: str,
        image_data: bytes,
        mime_type: str = "image/jpeg",
        **kwargs
    ) -> Optional[str]:
        """
        Analyze content with image using vision capabilities.
        
        Args:
            prompt: The text prompt
            image_data: Image bytes
            mime_type: MIME type of the image
            **kwargs: Additional parameters
        
        Returns:
            Generated text response, or None if failed
        """
        pass
    
    def is_available(self) -> bool:
        """
        Check if the provider is available/configured.
        
        Returns:
            True if provider is ready to use
        """
        return True
    
    def get_provider_name(self) -> str:
        """
        Get the name of this provider.
        
        Returns:
            Provider name (e.g., 'gemini', 'self_hosted')
        """
        return self.__class__.__name__



