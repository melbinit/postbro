"""
Clerk authentication for Django REST Framework
"""
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import get_user_model
from django.utils import timezone
from .clerk_client import get_clerk_client
from typing import Optional
import logging

logger = logging.getLogger(__name__)

User = get_user_model()


class ClerkAuthentication(authentication.BaseAuthentication):
    """
    Authenticate users using Clerk JWT tokens
    
    Clerk tokens are JWTs that can be verified using Clerk's API
    or by verifying the signature with Clerk's public key.
    """
    
    def authenticate(self, request):
        """
        Authenticate the request using Clerk JWT token
        Returns (user, token) tuple or None
        """
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return None
        
        # Extract token from "Bearer <token>"
        try:
            scheme, token = auth_header.split()
            if scheme.lower() != 'bearer':
                return None
        except ValueError:
            return None
        
        # Verify token and get user
        user = self.authenticate_token(token)
        
        if user:
            return (user, token)
        
        return None
    
    def authenticate_token(self, token: str) -> Optional[User]:
        """
        Verify Clerk JWT token and return Django user
        
        Clerk tokens are JWTs. We verify them by:
        1. Decoding the token to get user info
        2. Optionally verifying signature with Clerk's public key
        3. Or verifying via Clerk API
        """
        try:
            clerk = get_clerk_client()
            
            # Verify token with Clerk API
            session_data = clerk.verify_token(token)
            
            if not session_data:
                # Try alternative: decode JWT without verification to get user_id
                import jwt
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    clerk_user_id = decoded.get('sub')
                    email = decoded.get('email')
                    
                    if clerk_user_id:
                        # Get FULL user info from Clerk API (includes first_name/last_name)
                        user_data = clerk.get_user(clerk_user_id)
                        if user_data:
                            email = user_data.get('email_addresses', [{}])[0].get('email_address') if user_data.get('email_addresses') else email
                            email_verified = user_data.get('email_addresses', [{}])[0].get('verification', {}).get('status') == 'verified' if user_data.get('email_addresses') else False
                            
                            # Extract first_name/last_name from Clerk user data
                            first_name = user_data.get('first_name', '')
                            last_name = user_data.get('last_name', '')
                            full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else ''
                            
                            user = self.get_or_create_user_from_clerk(
                                clerk_user_id, 
                                email, 
                                {
                                    'email_verified': email_verified,
                                    'first_name': first_name,
                                    'last_name': last_name,
                                    'full_name': full_name
                                }
                            )
                            return user
                except jwt.InvalidTokenError:
                    raise AuthenticationFailed('Invalid token format')
                except Exception as e:
                    logger.error(f"Error decoding token: {str(e)}")
                    raise AuthenticationFailed('Token verification failed')
            
            # Extract user info from verified session
            clerk_user_id = session_data.get('sub')
            email = session_data.get('email')
            email_verified = session_data.get('email_verified', False)
            
            if not clerk_user_id:
                return None
            
            # Fetch FULL user data from Clerk API to get first_name/last_name
            user_data = clerk.get_user(clerk_user_id)
            if user_data:
                # Extract first_name/last_name from Clerk user data
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else ''
                
                # Update session_data with name info
                session_data['first_name'] = first_name
                session_data['last_name'] = last_name
                session_data['full_name'] = full_name
            
            # Get or create Django User from Clerk user
            user = self.get_or_create_user_from_clerk(clerk_user_id, email, session_data)
            
            return user
            
        except AuthenticationFailed:
            raise
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            raise AuthenticationFailed(f'Authentication failed: {str(e)}')
    
    def get_or_create_user_from_clerk(self, clerk_user_id: str, email: str, session_data: dict) -> User:
        """
        Get or create Django User from Clerk user ID
        Syncs Clerk users with Django User model
        """
        try:
            user = None
            is_new_user = False
            
            # Extract name data from session_data
            first_name = session_data.get('first_name', '')
            last_name = session_data.get('last_name', '')
            full_name = session_data.get('full_name', '') or (f"{first_name} {last_name}".strip() if (first_name or last_name) else '')
            
            # Try to find user by clerk_user_id first
            try:
                user = User.objects.get(clerk_user_id=clerk_user_id)
                # Update email if changed
                if email and user.email != email:
                    user.email = email
                user.email_verified = session_data.get('email_verified', False)
                # Update name if provided and missing
                if full_name and not user.full_name:
                    user.full_name = full_name
                user.save()
            except User.DoesNotExist:
                pass
            
            # Fallback: try by email
            if not user and email:
                try:
                    user = User.objects.get(email=email)
                    # Update with clerk_user_id if missing
                    if not user.clerk_user_id:
                        user.clerk_user_id = clerk_user_id
                    user.email_verified = session_data.get('email_verified', False)
                    # Update name if provided and missing
                    if full_name and not user.full_name:
                        user.full_name = full_name
                    user.save()
                except User.DoesNotExist:
                    pass
            
            # User exists in Clerk but not in Django - create Django user
            if not user:
                user = User.objects.create_user(
                    email=email or f"{clerk_user_id}@clerk.local",
                    clerk_user_id=clerk_user_id,
                    email_verified=session_data.get('email_verified', False),
                    full_name=full_name,
                    is_active=True
                )
                is_new_user = True
            
            # ALWAYS ensure Free subscription exists (for both new and existing users)
            # This handles cases where user was created but subscription wasn't
            self._ensure_free_subscription(user)
            
            return user
            
        except Exception as e:
            logger.error(f"Error syncing user: {str(e)}")
            raise AuthenticationFailed(f'Failed to sync user: {str(e)}')
    
    def _ensure_free_subscription(self, user: User) -> None:
        """
        Ensure user has an active Free subscription.
        Called when a new user is created via Clerk authentication.
        """
        try:
            from .models import Plan, Subscription
            
            free_plan = Plan.objects.get(name='Free', is_active=True)
            subscription, created = Subscription.objects.get_or_create(
                user=user,
                plan=free_plan,
                defaults={
                    'status': Subscription.Status.ACTIVE,
                    'start_date': timezone.now()
                }
            )
            
            if created:
                logger.info(f"✅ [ClerkAuth] Created Free subscription for new user {user.id} (email: {user.email})")
            else:
                # Subscription already exists - ensure it's active
                if subscription.status != Subscription.Status.ACTIVE:
                    logger.warning(
                        f"⚠️ [ClerkAuth] Existing subscription for user {user.id} has status {subscription.status}, "
                        f"updating to ACTIVE"
                    )
                    subscription.status = Subscription.Status.ACTIVE
                    subscription.start_date = timezone.now()
                    subscription.save()
                else:
                    logger.debug(f"✅ [ClerkAuth] User {user.id} already has active Free subscription")
                    
        except Plan.DoesNotExist:
            logger.error(
                f"❌ [ClerkAuth] Free plan not found in database - subscription not created for user {user.id}"
            )
        except Exception as e:
            logger.error(
                f"❌ [ClerkAuth] Failed to create Free subscription for user {user.id}: {str(e)}",
                exc_info=True
            )
            # Don't raise - authentication should succeed even if subscription creation fails

