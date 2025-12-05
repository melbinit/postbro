"""
Utility functions for accounts app
"""
from django.utils import timezone
from datetime import date, timedelta
from .models import User, Subscription, UserUsage, Plan
from typing import Dict, Optional, Tuple


def get_user_subscription(user: User) -> Optional[Subscription]:
    """
    Get user's current active subscription
    Returns the most recent active or trial subscription
    """
    return Subscription.objects.filter(
        user=user,
        status__in=[Subscription.Status.ACTIVE, Subscription.Status.TRIAL]
    ).select_related('plan').order_by('-created_at').first()


def get_user_plan(user: User) -> Optional[Plan]:
    """
    Get user's current plan from their active subscription
    Returns None if no active subscription
    """
    subscription = get_user_subscription(user)
    return subscription.plan if subscription else None


def get_user_usage_today(user: User, platform: str) -> UserUsage:
    """
    Get or create today's usage record for user and platform
    """
    today = date.today()
    usage, created = UserUsage.objects.get_or_create(
        user=user,
        date=today,
        platform=platform,
        defaults={
            'handle_analyses': 0,
            'url_lookups': 0,
            'post_suggestions': 0,
            'questions_asked': 0
        }
    )
    return usage


def increment_usage(user: User, platform: str, usage_type: str) -> UserUsage:
    """
    Increment usage counter for user
    usage_type: 'handle_analyses', 'url_lookups', 'post_suggestions', or 'questions_asked'
    
    Note: For 'questions_asked', platform can be any value (questions are not platform-specific)
    """
    usage = get_user_usage_today(user, platform)
    
    if usage_type == 'handle_analyses':
        usage.handle_analyses += 1
    elif usage_type == 'url_lookups':
        usage.url_lookups += 1
    elif usage_type == 'post_suggestions':
        usage.post_suggestions += 1
    elif usage_type == 'questions_asked':
        usage.questions_asked += 1
    else:
        raise ValueError(f'Invalid usage type: {usage_type}')
    
    usage.save()
    return usage


def check_usage_limit(user: User, platform: str, usage_type: str) -> Tuple[bool, Dict]:
    """
    Check if user has reached their usage limit
    Returns (can_proceed, info_dict)
    """
    plan = get_user_plan(user)
    
    if not plan:
        return False, {
            'error': 'No active subscription found',
            'can_proceed': False
        }
    
    usage = get_user_usage_today(user, platform)
    
    # Get current usage
    if usage_type == 'url_lookups':
        current = usage.url_lookups
        limit = plan.max_urls
    elif usage_type == 'post_suggestions':
        current = usage.post_suggestions
        limit = plan.max_analyses_per_day
    elif usage_type == 'questions_asked':
        # Questions are tracked per user (not per platform), so we need to aggregate
        from django.db.models import Sum
        today = date.today()
        total_questions = UserUsage.objects.filter(
            user=user,
            date=today
        ).aggregate(total=Sum('questions_asked'))['total'] or 0
        current = total_questions
        limit = plan.max_questions_per_day
    else:
        return False, {'error': f'Invalid usage type: {usage_type}. Supported: url_lookups, post_suggestions, questions_asked'}
    
    can_proceed = current < limit
    
    return can_proceed, {
        'can_proceed': can_proceed,
        'current': current,
        'limit': limit,
        'remaining': max(0, limit - current),
        'plan_name': plan.name
    }


def get_usage_summary(user: User, platform: str = None) -> Dict:
    """
    Get comprehensive usage summary for user
    """
    plan = get_user_plan(user)
    
    if not plan:
        return {
            'error': 'No active subscription found',
            'plan': None,
            'usage': None
        }
    
    # Get today's usage
    today = date.today()
    
    if platform:
        # Single platform
        usage = UserUsage.objects.filter(
            user=user,
            date=today,
            platform=platform
        ).first()
        
        if not usage:
            usage = UserUsage(
                user=user,
                date=today,
                platform=platform,
                handle_analyses=0,
                url_lookups=0,
                post_suggestions=0,
                questions_asked=0
            )
        
        # For questions, aggregate across all platforms (questions are user-level)
        from django.db.models import Sum
        total_questions = UserUsage.objects.filter(
            user=user,
            date=today
        ).aggregate(total=Sum('questions_asked'))['total'] or 0
        
        return {
            'plan': {
                'id': str(plan.id),
                'name': plan.name,
                'max_handles': plan.max_handles,
                'max_urls': plan.max_urls,
                'max_analyses_per_day': plan.max_analyses_per_day,
                'max_questions_per_day': plan.max_questions_per_day
            },
            'usage': {
                'platform': platform,
                'date': today.isoformat(),
                'handle_analyses': {
                    'used': usage.handle_analyses,
                    'limit': plan.max_handles,
                    'remaining': max(0, plan.max_handles - usage.handle_analyses)
                },
                'url_lookups': {
                    'used': usage.url_lookups,
                    'limit': plan.max_urls,
                    'remaining': max(0, plan.max_urls - usage.url_lookups)
                },
                'post_suggestions': {
                    'used': usage.post_suggestions,
                    'limit': plan.max_analyses_per_day,
                    'remaining': max(0, plan.max_analyses_per_day - usage.post_suggestions)
                },
                'questions_asked': {
                    'used': total_questions,
                    'limit': plan.max_questions_per_day,
                    'remaining': max(0, plan.max_questions_per_day - total_questions)
                }
            }
        }
    else:
        # All platforms
        usages = UserUsage.objects.filter(
            user=user,
            date=today
        )
        
        # Aggregate questions across all platforms (questions are user-level, not platform-specific)
        from django.db.models import Sum
        total_questions = usages.aggregate(total=Sum('questions_asked'))['total'] or 0
        
        usage_by_platform = {}
        for usage in usages:
            usage_by_platform[usage.platform] = {
                'handle_analyses': usage.handle_analyses,
                'url_lookups': usage.url_lookups,
                'post_suggestions': usage.post_suggestions,
                'questions_asked': usage.questions_asked
            }
        
        return {
            'plan': {
                'id': str(plan.id),
                'name': plan.name,
                'max_handles': plan.max_handles,
                'max_urls': plan.max_urls,
                'max_analyses_per_day': plan.max_analyses_per_day,
                'max_questions_per_day': plan.max_questions_per_day
            },
            'usage': {
                'date': today.isoformat(),
                'platforms': usage_by_platform,
                'questions_asked': {
                    'used': total_questions,
                    'limit': plan.max_questions_per_day,
                    'remaining': max(0, plan.max_questions_per_day - total_questions)
                }
            }
        }






        
        # Aggregate questions across all platforms (questions are user-level, not platform-specific)
        from django.db.models import Sum
        total_questions = usages.aggregate(total=Sum('questions_asked'))['total'] or 0
        
        usage_by_platform = {}
        for usage in usages:
            usage_by_platform[usage.platform] = {
                'handle_analyses': usage.handle_analyses,
                'url_lookups': usage.url_lookups,
                'post_suggestions': usage.post_suggestions,
                'questions_asked': usage.questions_asked
            }
        
        return {
            'plan': {
                'id': str(plan.id),
                'name': plan.name,
                'max_handles': plan.max_handles,
                'max_urls': plan.max_urls,
                'max_analyses_per_day': plan.max_analyses_per_day,
                'max_questions_per_day': plan.max_questions_per_day
            },
            'usage': {
                'date': today.isoformat(),
                'platforms': usage_by_platform,
                'questions_asked': {
                    'used': total_questions,
                    'limit': plan.max_questions_per_day,
                    'remaining': max(0, plan.max_questions_per_day - total_questions)
                }
            }
        }





