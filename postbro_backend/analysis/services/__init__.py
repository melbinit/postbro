"""
Analysis Services Module

Provides Gemini analysis service for post analysis.
"""

import logging
from typing import Callable

logger = logging.getLogger(__name__)


def get_analysis_service() -> Callable:
    """
    Returns the Gemini analysis service function.
    
    Returns:
        Function: analyze_post_with_gemini
    """
    logger.info("🤖 [ModelSelection] Using Gemini 2.5 Flash for analysis")
    from .gemini_service import analyze_post_with_gemini
    return analyze_post_with_gemini
