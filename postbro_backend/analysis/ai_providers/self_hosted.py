"""
Self-Hosted LLM Provider

Uses a self-hosted LLM (e.g., Llama 3, Mistral) via OpenAI-compatible API.
This is a placeholder for future implementation when you're ready to self-host.
"""

import logging
from typing import Optional
import requests
from django.conf import settings
from .base import AIProvider

logger = logging.getLogger(__name__)


class SelfHostedProvider(AIProvider):
    """Self-hosted LLM provider (OpenAI-compatible API)"""
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        model_name: Optional[str] = None,
        api_key: Optional[str] = None
    ):
        """
        Initialize self-hosted LLM provider.
        
        Args:
            base_url: Base URL of the self-hosted LLM API
            model_name: Model name to use
            api_key: Optional API key (if required)
        """
        self.base_url = base_url or getattr(
            settings,
            'SELF_HOSTED_LLM_URL',
            'http://localhost:8000'
        )
        self.model_name = model_name or getattr(
            settings,
            'SELF_HOSTED_LLM_MODEL',
            'llama3'
        )
        self.api_key = api_key or getattr(
            settings,
            'SELF_HOSTED_LLM_API_KEY',
            None
        )
        self.provider_name = "self_hosted"
    
    def analyze_content(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Optional[str]:
        """
        Analyze content using self-hosted LLM.
        
        Args:
            prompt: The text prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
        
        Returns:
            Generated text response
        """
        try:
            headers = {
                'Content-Type': 'application/json'
            }
            
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            # Try OpenAI-compatible API format
            payload = {
                'model': self.model_name,
                'prompt': prompt,
                'temperature': temperature,
                'max_tokens': max_tokens,
                **kwargs
            }
            
            # Try /v1/completions endpoint (OpenAI format)
            response = requests.post(
                f'{self.base_url}/v1/completions',
                json=payload,
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    return data['choices'][0].get('text', '')
                elif 'text' in data:
                    return data['text']
            
            logger.error(f"Self-hosted LLM API error: {response.status_code} - {response.text}")
            return None
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error calling self-hosted LLM: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in self-hosted provider: {str(e)}")
            return None
    
    def analyze_with_vision(
        self,
        prompt: str,
        image_data: bytes,
        mime_type: str = "image/jpeg",
        **kwargs
    ) -> Optional[str]:
        """
        Analyze content with image using self-hosted vision model.
        
        Note: This requires a vision-capable model (e.g., LLaVA).
        
        Args:
            prompt: The text prompt
            image_data: Image bytes
            mime_type: MIME type of the image
            **kwargs: Additional parameters
        
        Returns:
            Generated text response
        """
        # For now, return None - vision support depends on model
        # You can implement this when you have a vision-capable model
        logger.warning("Vision analysis not yet implemented for self-hosted provider")
        return None
    
    def is_available(self) -> bool:
        """Check if self-hosted LLM is available"""
        try:
            response = requests.get(
                f'{self.base_url}/health',
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
    
    def get_provider_name(self) -> str:
        return "self_hosted"



