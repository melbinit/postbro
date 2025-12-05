"""
Social media scrapers package.

This package contains scrapers for different social media platforms:
- BrightData: Instagram and YouTube
- TwitterAPI: Twitter/X
"""

from .brightdata import BrightDataScraper
from .twitterapi import TwitterAPIScraper

__all__ = ['BrightDataScraper', 'TwitterAPIScraper']


