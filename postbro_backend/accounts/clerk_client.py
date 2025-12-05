"""
Clerk client initialization for Django backend
Provides singleton client for Clerk API operations
"""
import os
import requests
from django.conf import settings
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Singleton instance
_clerk_client: Optional['ClerkClient'] = None


class ClerkClient:
    """
    Clerk API client for backend operations
    """
    
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self.base_url = "https://api.clerk.com/v1"
        self.headers = {
            "Authorization": f"Bearer {secret_key}",
            "Content-Type": "application/json"
        }
    
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Verify a Clerk JWT token and return the session/user info
        
        Clerk tokens are JWTs. We decode them to get user info.
        For production, you should verify the signature using Clerk's public key.
        """
        try:
            import jwt
            
            # Decode token to get user info (without signature verification for now)
            # In production, you should verify signature with Clerk's public key
            decoded = jwt.decode(token, options={"verify_signature": False})
            
            clerk_user_id = decoded.get("sub")
            email = decoded.get("email")
            email_verified = decoded.get("email_verified", False)
            
            if not clerk_user_id:
                return None
            
            # Optionally, get full user info from Clerk API
            try:
                user_data = self.get_user(clerk_user_id)
                if user_data:
                    email_addresses = user_data.get("email_addresses", [])
                    if email_addresses:
                        email = email_addresses[0].get("email_address", email)
                        verification_status = email_addresses[0].get("verification", {}).get("status")
                        email_verified = verification_status == "verified"
            except Exception as e:
                logger.warning(f"Could not fetch user details from Clerk API: {str(e)}")
                # Continue with decoded token data
            
            return {
                "sub": clerk_user_id,
                "email": email,
                "email_verified": email_verified,
            }
            
        except jwt.InvalidTokenError as e:
            logger.error(f"Invalid JWT token: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error verifying Clerk token: {str(e)}")
            return None
    
    def create_user(self, email: str, password: str, first_name: str = "", last_name: str = "", metadata: Dict = None) -> Optional[Dict[str, Any]]:
        """
        Create a new user in Clerk
        """
        try:
            payload = {
                "email_address": [email],
                "password": password,
                "skip_password_checks": False,  # Set to True if you want to skip password validation
                "skip_password_requirement": False,
            }
            
            if first_name or last_name:
                payload["first_name"] = first_name
                payload["last_name"] = last_name
            
            if metadata:
                payload["public_metadata"] = metadata
            
            response = requests.post(
                f"{self.base_url}/users",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return response.json()
            else:
                error_data = response.json() if response.content else {}
                error_msg = error_data.get("errors", [{}])[0].get("message", response.text) if error_data.get("errors") else response.text
                logger.error(f"Failed to create user: {response.status_code} - {error_msg}")
                # Return error info for better error handling
                return {"error": error_msg, "status_code": response.status_code}
                
        except Exception as e:
            logger.error(f"Error creating Clerk user: {str(e)}")
            return None
    
    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get user information from Clerk
        """
        try:
            response = requests.get(
                f"{self.base_url}/users/{user_id}",
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
            return None
            
        except Exception as e:
            logger.error(f"Error getting Clerk user: {str(e)}")
            return None
    
    def create_password_reset_token(self, email: str, redirect_url: str = None) -> bool:
        """
        Create a password reset token and send email via Clerk
        """
        try:
            # First, find user by email
            # Clerk API: GET /users?email_address=email
            users_response = requests.get(
                f"{self.base_url}/users",
                headers=self.headers,
                params={"email_address": email},
                timeout=10
            )
            
            if users_response.status_code != 200:
                logger.error(f"Failed to find user: {users_response.status_code} - {users_response.text}")
                return False
            
            users_data = users_response.json()
            # Clerk returns a list or object with data array
            users = users_data if isinstance(users_data, list) else users_data.get("data", [])
            
            if not users or len(users) == 0:
                logger.warning(f"No user found with email: {email}")
                return False
            
            user_id = users[0].get("id")
            if not user_id:
                return False
            
            # Create password reset token
            # Clerk API: POST /users/{user_id}/password_reset
            payload = {}
            if redirect_url:
                payload["redirect_url"] = redirect_url
            
            response = requests.post(
                f"{self.base_url}/users/{user_id}/password_reset",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Failed to create password reset token: {response.status_code} - {response.text}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating password reset token: {str(e)}")
            return False


def get_clerk_client() -> ClerkClient:
    """
    Get or create Clerk client singleton
    """
    global _clerk_client
    
    if _clerk_client is None:
        clerk_secret_key = getattr(settings, 'CLERK_SECRET_KEY', None) or os.getenv('CLERK_SECRET_KEY')
        
        if not clerk_secret_key:
            raise ValueError(
                'Clerk secret key must be set in settings. '
                'Please set CLERK_SECRET_KEY in your .env file.'
            )
        
        _clerk_client = ClerkClient(clerk_secret_key)
    
    return _clerk_client

