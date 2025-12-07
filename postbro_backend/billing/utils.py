"""
Utility functions for billing operations
"""
from datetime import timedelta
from django.utils import timezone
from accounts.models import Subscription
from typing import Optional, Tuple


def calculate_prorated_credit(
    old_subscription: Subscription,
    new_plan_price: float
) -> Tuple[float, int]:
    """
    Calculate prorated credit for upgrade
    
    Returns:
        (credit_amount, remaining_days)
    
    Example:
        User on $29 plan, day 3 of 30, upgrading to $59
        remaining_days = 27
        credit = (27 / 30) * 29 = $26.10
        user_pays = 59 - 26.10 = $32.90
    """
    if not old_subscription.end_date:
        # If no end_date, assume 30-day period from start_date
        period_end = old_subscription.start_date + timedelta(days=30)
    else:
        period_end = old_subscription.end_date
    
    now = timezone.now()
    
    # Calculate remaining days
    if period_end > now:
        remaining_days = (period_end - now).days
        total_days = (period_end - old_subscription.start_date).days
    else:
        # Period already ended
        return 0.0, 0
    
    if total_days == 0:
        return 0.0, remaining_days
    
    # Calculate credit
    old_price = float(old_subscription.plan.price)
    credit = (remaining_days / total_days) * old_price
    
    return round(credit, 2), remaining_days


def calculate_subscription_end_date(start_date, billing_period_days: int = 30):
    """
    Calculate subscription end date based on billing period
    """
    return start_date + timedelta(days=billing_period_days)


def get_old_active_subscription(user, exclude_subscription_id: Optional[str] = None) -> Optional[Subscription]:
    """
    Get user's current active subscription, excluding a specific subscription
    Used during upgrades to find the subscription being replaced
    """
    queryset = Subscription.objects.filter(
        user=user,
        status=Subscription.Status.ACTIVE
    )
    
    if exclude_subscription_id:
        queryset = queryset.exclude(id=exclude_subscription_id)
    
    return queryset.select_related('plan').order_by('-created_at').first()

