"""
Authentication views using Clerk
Clerk handles: signup, login, email verification, password reset
We sync Clerk users with Django User model
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .clerk_client import get_clerk_client
from .models import User, Plan, Subscription
from .serializers import UserProfileSerializer, PlanSerializer, SubscriptionSerializer
from django.utils import timezone
from analytics.utils import get_client_ip
from analytics.tasks import log_auth_event
import logging

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([AllowAny])
def signup(request):
    """
    Sign up user via Clerk
    Clerk handles email verification automatically
    """
    try:
        email = request.data.get('email')
        password = request.data.get('password')
        full_name = request.data.get('full_name', '')
        company_name = request.data.get('company_name', '')
        
        if not email or not password:
            return Response(
                {'error': 'Email and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user with Clerk
        clerk = get_clerk_client()
        
        # Split full_name into first and last name
        name_parts = full_name.split(maxsplit=1) if full_name else ['', '']
        first_name = name_parts[0] if len(name_parts) > 0 else ''
        last_name = name_parts[1] if len(name_parts) > 1 else ''
        
        user_response = clerk.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            metadata={'company_name': company_name, 'full_name': full_name} if company_name or full_name else None
        )
        
        if not user_response or user_response.get('error') or not user_response.get('id'):
            error_text = user_response.get('error', 'Failed to create user') if isinstance(user_response, dict) else 'Failed to create user'
            status_code = user_response.get('status_code', status.HTTP_400_BAD_REQUEST) if isinstance(user_response, dict) else status.HTTP_400_BAD_REQUEST
            return Response(
                {'error': error_text},
                status=status_code
            )
        
        clerk_user_id = user_response['id']
        email_addresses = user_response.get('email_addresses', [])
        email_verified = email_addresses[0].get('verification', {}).get('status') == 'verified' if email_addresses else False
        
        # Sync with Django User model
        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                'clerk_user_id': clerk_user_id,
                'full_name': full_name,
                'company_name': company_name,
                'email_verified': email_verified,
                'is_active': True
            }
        )
        
        if not created:
            # Update existing user
            user.clerk_user_id = clerk_user_id
            user.email_verified = email_verified
            if full_name:
                user.full_name = full_name
            if company_name:
                user.company_name = company_name
            user.save()
        
        # Auto-create Free subscription
        try:
            free_plan = Plan.objects.get(name='Free', is_active=True)
            Subscription.objects.get_or_create(
                user=user,
                plan=free_plan,
                defaults={
                    'status': Subscription.Status.ACTIVE,
                    'start_date': timezone.now()
                }
            )
        except Plan.DoesNotExist:
            pass  # Plan will be created by migration
        
        # Log successful signup
        try:
            log_auth_event.delay(
                user_id=str(user.id),
                event_type='signup',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
                metadata={'email': email, 'full_name': full_name}
            )
        except Exception as e:
            # Don't fail signup if logging fails
            logger.warning(f"Failed to log signup event: {str(e)}")
        
        return Response(
            {
                'message': 'Account created successfully. Please check your email to verify your account.',
                'user': {
                    'id': str(user.id),
                    'email': user.email,
                    'email_verified': user.email_verified
                }
            },
            status=status.HTTP_201_CREATED
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Signup error: {error_msg}")
        
        # Log failed signup attempt
        try:
            email = request.data.get('email', 'unknown')
            log_auth_event.delay(
                user_id=None,
                event_type='signup',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False,
                error_message=error_msg[:500],
                metadata={'email': email}
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        if 'already registered' in error_msg.lower() or 'user already exists' in error_msg.lower() or 'email_address' in error_msg.lower():
            return Response(
                {'error': 'A user with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return Response(
            {'error': f'Signup failed: {error_msg}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Verify Clerk token and sync user
    
    Note: With Clerk, the frontend typically handles login and gets a JWT token.
    This endpoint verifies the token and syncs the user with Django.
    Alternatively, you can pass email/password and we'll verify via Clerk API.
    """
    try:
        # Option 1: Token-based login (preferred with Clerk)
        token = request.data.get('token')
        if token:
            clerk = get_clerk_client()
            session_data = clerk.verify_token(token)
            
            if not session_data:
                return Response(
                    {'error': 'Invalid or expired token'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            clerk_user_id = session_data.get('sub')
            email = session_data.get('email')
            email_verified = session_data.get('email_verified', False)
            
            if not clerk_user_id:
                return Response(
                    {'error': 'Invalid token data'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            # Sync with Django User model
            user, created = User.objects.get_or_create(
                clerk_user_id=clerk_user_id,
                defaults={
                    'email': email or f"{clerk_user_id}@clerk.local",
                    'email_verified': email_verified,
                    'is_active': True
                }
            )
            
            if not created:
                # Update user info
                if email and user.email != email:
                    user.email = email
                user.email_verified = email_verified
                user.is_active = True
                user.save()
            
            # Log successful login
            try:
                log_auth_event.delay(
                    user_id=str(user.id),
                    event_type='login',
                    ip_address=get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    success=True,
                    metadata={'email': user.email}
                )
            except Exception as e:
                logger.warning(f"Failed to log login event: {str(e)}")
            
            return Response(
                {
                    'message': 'Login successful',
                    'user': {
                        'id': str(user.id),
                        'email': user.email,
                        'email_verified': user.email_verified,
                        'full_name': user.full_name,
                        'company_name': user.company_name
                    }
                },
                status=status.HTTP_200_OK
            )
        
        # Option 2: Email/password (for backward compatibility)
        # Note: Clerk doesn't support backend password verification directly
        # This is a fallback - frontend should use Clerk SDK for login
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response(
                {'error': 'Token or email/password is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # For email/password, we can't verify directly with Clerk backend API
        # The frontend should handle login with Clerk SDK and send us the token
        return Response(
            {
                'error': 'Please use Clerk frontend SDK to login and send the token to this endpoint',
                'message': 'Use /api/accounts/login/ with a "token" field containing your Clerk JWT token'
            },
            status=status.HTTP_400_BAD_REQUEST
        )
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Login error: {error_msg}")
        
        # Log failed login attempt
        try:
            email = request.data.get('email', 'unknown')
            log_auth_event.delay(
                user_id=None,
                event_type='login_failed',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=False,
                error_message=error_msg[:500],
                metadata={'email': email}
            )
        except Exception:
            pass  # Don't fail if logging fails
        
        return Response(
            {'error': f'Login failed: {error_msg}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout user
    Note: With Clerk, logout is typically handled on the frontend.
    This endpoint just logs the logout event.
    """
    try:
        # Log logout
        try:
            user_id = str(request.user.id) if hasattr(request, 'user') and request.user.is_authenticated else None
            log_auth_event.delay(
                user_id=user_id,
                event_type='logout',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True
            )
        except Exception as e:
            logger.warning(f"Failed to log logout event: {str(e)}")
        
        return Response(
            {'message': 'Logged out successfully'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'Logout failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    """
    Request password reset via Clerk
    Clerk sends reset email automatically
    """
    try:
        email = request.data.get('email')
        
        if not email:
            return Response(
                {'error': 'Email is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Request password reset with Clerk
        clerk = get_clerk_client()
        redirect_url = request.data.get('redirect_to', 'http://localhost:3000/reset-password')
        
        success = clerk.create_password_reset_token(email, redirect_url)
        
        if not success:
            return Response(
                {'error': 'Failed to send password reset email. User may not exist.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log password reset request
        try:
            # Try to get user by email
            try:
                user = User.objects.get(email=email)
                user_id = str(user.id)
            except User.DoesNotExist:
                user_id = None
            
            log_auth_event.delay(
                user_id=user_id,
                event_type='password_reset_request',
                ip_address=get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                success=True,
                metadata={'email': email}
            )
        except Exception as e:
            logger.warning(f"Failed to log password reset event: {str(e)}")
        
        return Response(
            {'message': 'Password reset email sent. Please check your inbox.'},
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return Response(
            {'error': f'Password reset failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET', 'PATCH'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get or update user profile
    """
    if request.method == 'GET':
        serializer = UserProfileSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    elif request.method == 'PATCH':
        serializer = UserProfileSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def current_subscription(request):
    """
    Get user's current subscription
    """
    try:
        subscription = Subscription.objects.filter(
            user=request.user,
            status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
        ).select_related('plan').first()
        
        if not subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch subscription: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def plans_list(request):
    """
    Get all active subscription plans
    Public endpoint - no authentication required
    """
    try:
        plans = Plan.objects.filter(is_active=True).order_by('price')
        serializer = PlanSerializer(plans, many=True)
        return Response(
            {'plans': serializer.data},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        error_message = str(e)
        # Check if it's a database connection error
        if 'could not translate host name' in error_message or 'No address associated with hostname' in error_message:
            logger.error(f"❌ [Plans] Database connection failed - Supabase database may be paused: {error_message}")
            return Response(
                {
                    'error': 'Database connection failed',
                    'message': 'Unable to connect to database. Please check if your Supabase database is active.',
                    'details': 'The database hostname could not be resolved. This usually means the Supabase database is paused. Please check your Supabase dashboard.'
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )
        else:
            logger.error(f"❌ [Plans] Failed to fetch plans: {error_message}", exc_info=True)
            return Response(
                {'error': f'Failed to fetch plans: {error_message}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_stats(request):
    """
    Get user's current usage statistics
    Optional query param: ?platform=twitter (to filter by platform)
    """
    try:
        from .utils import get_usage_summary
        
        platform = request.query_params.get('platform', None)
        summary = get_usage_summary(request.user, platform)
        
        if 'error' in summary:
            return Response(summary, status=status.HTTP_404_NOT_FOUND)
        
        return Response(summary, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch usage stats: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_limits(request):
    """
    Get user's plan limits
    """
    try:
        from .utils import get_user_plan
        
        plan = get_user_plan(request.user)
        
        if not plan:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer = PlanSerializer(plan)
        return Response(
            {
                'plan': serializer.data,
                'limits': {
                    'max_handles': plan.max_handles,
                    'max_urls': plan.max_urls,
                    'max_analyses_per_day': plan.max_analyses_per_day,
                    'max_questions_per_day': plan.max_questions_per_day
                }
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch limits: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def usage_history(request):
    """
    Get user's usage history
    Optional query params: ?platform=twitter&days=7
    """
    try:
        from .models import UserUsage
        from .usage_serializers import UsageSerializer
        from datetime import date, timedelta
        
        platform = request.query_params.get('platform', None)
        days = int(request.query_params.get('days', 30))
        
        start_date = date.today() - timedelta(days=days)
        
        queryset = UserUsage.objects.filter(
            user=request.user,
            date__gte=start_date
        )
        
        if platform:
            queryset = queryset.filter(platform=platform)
        
        queryset = queryset.order_by('-date', 'platform')
        
        serializer = UsageSerializer(queryset, many=True)
        
        return Response(
            {
                'usage_history': serializer.data,
                'count': len(serializer.data),
                'start_date': start_date.isoformat(),
                'end_date': date.today().isoformat()
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch usage history: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
