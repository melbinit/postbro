"""
Supabase client initialization for Django backend
Provides singleton clients for regular and admin operations
"""
from supabase import create_client, Client
from django.conf import settings
from typing import Optional

# Singleton instances
_supabase_client: Optional[Client] = None
_supabase_admin_client: Optional[Client] = None


def get_supabase_client() -> Client:
    """
    Get or create Supabase client for regular operations
    Uses publishable key (or anon key as fallback)
    """
    global _supabase_client
    
    if _supabase_client is None:
        supabase_url = getattr(settings, 'SUPABASE_URL', None)
        supabase_key = getattr(settings, 'SUPABASE_PUBLISHABLE_KEY', None) or getattr(settings, 'SUPABASE_KEY', None)
        
        if not supabase_url or not supabase_key:
            raise ValueError(
                'Supabase URL and key must be set in settings. '
                'Please set SUPABASE_URL and SUPABASE_PUBLISHABLE_KEY (or SUPABASE_KEY) in your .env file.'
            )
        
        _supabase_client = create_client(supabase_url, supabase_key)
    
    return _supabase_client


def get_supabase_admin_client() -> Client:
    """
    Get or create Supabase admin client for privileged operations
    Uses secret key (or service_role key as fallback)
    Required for operations that bypass Row Level Security (RLS)
    """
    global _supabase_admin_client
    
    if _supabase_admin_client is None:
        supabase_url = getattr(settings, 'SUPABASE_URL', None)
        supabase_secret_key = getattr(settings, 'SUPABASE_SECRET_KEY', None) or getattr(settings, 'SUPABASE_SERVICE_ROLE_KEY', None)
        
        if not supabase_url or not supabase_secret_key:
            raise ValueError(
                'Supabase URL and secret key must be set in settings. '
                'Please set SUPABASE_URL and SUPABASE_SECRET_KEY (or SUPABASE_SERVICE_ROLE_KEY) in your .env file.'
            )
        
        _supabase_admin_client = create_client(supabase_url, supabase_secret_key)
    
    return _supabase_admin_client








