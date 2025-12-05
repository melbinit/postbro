"""
Dodo Payments Service
Handles all interactions with Dodo Payments API
"""

import os
import logging
import requests
import hmac
import hashlib
from typing import Dict, Optional, List
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)

# Dodo Payments API Configuration
DODO_API_KEY = os.getenv('DODO_API_KEY')
DODO_WEBHOOK_SECRET = os.getenv('DODO_WEBHOOK_SECRET')
DODO_BASE_URL = os.getenv('DODO_BASE_URL', 'https://api.dodopayments.com')  # Default to production

# Test mode URL (if needed)
# DODO_BASE_URL = 'https://api-test.dodopayments.com'  # For testing

if not DODO_API_KEY:
    logger.warning("DODO_API_KEY not found in environment variables")


class DodoPaymentsService:
    """
    Service for interacting with Dodo Payments API
    """
    
    def __init__(self):
        self.api_key = DODO_API_KEY
        self.base_url = DODO_BASE_URL.rstrip('/')
        self.webhook_secret = DODO_WEBHOOK_SECRET
        
        if not self.api_key:
            raise ValueError("DODO_API_KEY is required. Set it in your .env file.")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
        }
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict:
        """
        Make HTTP request to Dodo Payments API
        
        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint (e.g., '/checkouts', '/customers')
            data: Request body data
            params: Query parameters
            
        Returns:
            Response JSON as dictionary
            
        Raises:
            requests.RequestException: If API request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers()
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers,
                json=data,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            error_msg = f"Dodo API error: {e.response.status_code}"
            if e.response.text:
                try:
                    error_data = e.response.json()
                    error_msg += f" - {error_data.get('message', e.response.text)}"
                except:
                    error_msg += f" - {e.response.text[:200]}"
            logger.error(f"❌ [Dodo] {error_msg}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ [Dodo] Request failed: {str(e)}")
            raise
    
    def create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create a customer in Dodo Payments
        
        Args:
            email: Customer email
            name: Customer name (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Customer object from Dodo API
        """
        data = {
            'email': email,
        }
        if name:
            data['name'] = name
        if metadata:
            data['metadata'] = metadata
        
        logger.info(f"📝 [Dodo] Creating customer: {email}")
        customer = self._make_request('POST', '/customers', data=data)
        logger.info(f"✅ [Dodo] Customer created: {customer.get('id')}")
        return customer
    
    def get_or_create_customer(
        self,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Get existing customer or create new one
        
        Args:
            email: Customer email
            name: Customer name (optional)
            metadata: Additional metadata (optional)
            
        Returns:
            Customer object from Dodo API
        """
        # Try to find existing customer by email
        try:
            customers = self._make_request('GET', '/customers', params={'email': email})
            if customers.get('data') and len(customers['data']) > 0:
                logger.info(f"✅ [Dodo] Found existing customer: {customers['data'][0].get('id')}")
                return customers['data'][0]
        except Exception as e:
            logger.warning(f"⚠️ [Dodo] Could not find existing customer: {e}")
        
        # Create new customer
        return self.create_customer(email, name, metadata)
    
    def create_checkout_session(
        self,
        product_id: str,
        customer_id: Optional[str] = None,
        return_url: Optional[str] = None,
        metadata: Optional[Dict] = None,
        quantity: int = 1
    ) -> Dict:
        """
        Create a checkout session for subscription or one-time payment
        
        Args:
            product_id: Dodo product ID
            customer_id: Dodo customer ID (optional, will create if not provided)
            return_url: URL to redirect after payment (optional)
            metadata: Additional metadata (optional)
            quantity: Product quantity (default: 1)
            
        Returns:
            Checkout session object with checkout_url
        """
        data = {
            'product_cart': [{
                'product_id': product_id,
                'quantity': quantity
            }]
        }
        
        if customer_id:
            data['customer_id'] = customer_id
        
        if return_url:
            data['return_url'] = return_url
        
        if metadata:
            data['metadata'] = metadata
        
        logger.info(f"🛒 [Dodo] Creating checkout session for product: {product_id}")
        checkout_session = self._make_request('POST', '/checkouts', data=data)
        logger.info(f"✅ [Dodo] Checkout session created: {checkout_session.get('id')}")
        return checkout_session
    
    def get_checkout_session(self, checkout_id: str) -> Dict:
        """
        Get checkout session details
        
        Args:
            checkout_id: Checkout session ID
            
        Returns:
            Checkout session object
        """
        logger.info(f"🔍 [Dodo] Getting checkout session: {checkout_id}")
        return self._make_request('GET', f'/checkouts/{checkout_id}')
    
    def cancel_subscription(self, subscription_id: str) -> Dict:
        """
        Cancel a subscription in Dodo Payments
        
        Args:
            subscription_id: Dodo subscription ID
            
        Returns:
            Updated subscription object
        """
        logger.info(f"🚫 [Dodo] Cancelling subscription: {subscription_id}")
        # Note: Check Dodo docs for exact endpoint - this might be PATCH /subscriptions/{id}
        # with status: 'cancelled' or DELETE endpoint
        subscription = self._make_request('PATCH', f'/subscriptions/{subscription_id}', data={
            'status': 'cancelled'
        })
        logger.info(f"✅ [Dodo] Subscription cancelled: {subscription_id}")
        return subscription
    
    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str
    ) -> bool:
        """
        Verify webhook signature from Dodo Payments
        
        Args:
            payload: Raw request body as bytes
            signature: Signature from X-Dodo-Signature header
            
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            logger.warning("⚠️ [Dodo] Webhook secret not configured, skipping signature verification")
            return True  # Allow in development, but should be False in production
        
        try:
            # Dodo uses HMAC SHA256 for webhook signatures
            # Format: signature = hmac_sha256(payload, webhook_secret)
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures (use constant-time comparison to prevent timing attacks)
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"❌ [Dodo] Webhook signature verification failed: {e}")
            return False


# Singleton instance
_dodo_service = None


def get_dodo_service() -> DodoPaymentsService:
    """
    Get or create Dodo Payments service instance
    
    Returns:
        DodoPaymentsService instance
    """
    global _dodo_service
    if _dodo_service is None:
        _dodo_service = DodoPaymentsService()
    return _dodo_service

