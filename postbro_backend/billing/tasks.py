"""
Celery tasks for billing operations
"""
from celery import shared_task
from django.utils import timezone
from django.db import transaction
import logging
import os
from accounts.models import Subscription
from billing.utils import calculate_subscription_end_date
from billing.services.dodo_service import get_dodo_service

logger = logging.getLogger(__name__)


@shared_task
def process_scheduled_downgrades():
    """
    Process subscriptions that need to be downgraded at period end.
    Also handles expired cancellations (assigns free plan).
    Runs daily via Celery Beat.
    
    Standard SaaS behavior:
    - Cancel old subscription at period end
    - Activate new downgraded plan
    - Charge for new plan (if paid)
    - Assign free plan to expired cancellations
    """
    now = timezone.now()
    
    # Find subscriptions that are CANCELING and have passed their end_date
    expired_canceling = Subscription.objects.filter(
        status=Subscription.Status.CANCELING,
        end_date__lte=now,
        downgrade_to_plan__isnull=False
    ).select_related('user', 'plan', 'downgrade_to_plan')
    
    # Also find expired cancellations (no downgrade_to_plan) - assign free plan
    expired_cancellations = Subscription.objects.filter(
        status=Subscription.Status.CANCELING,
        end_date__lte=now,
        downgrade_to_plan__isnull=True
    ).select_related('user', 'plan')
    
    processed_count = 0
    errors = []
    
    # Process expired cancellations (assign free plan)
    from accounts.models import Plan
    free_plan = Plan.objects.filter(price=0, is_active=True).first()
    
    for subscription in expired_cancellations:
        try:
            with transaction.atomic():
                # Check if user already has free plan
                existing_free = Subscription.objects.filter(
                    user=subscription.user,
                    plan=free_plan,
                    status__in=[Subscription.Status.ACTIVE, Subscription.Status.CANCELING]
                ).first() if free_plan else None
                
                if existing_free:
                    # User already has free plan, just mark old as CANCELLED
                    subscription.status = Subscription.Status.CANCELLED
                    subscription.save()
                    logger.info(f"✅ [Billing Task] Cancelled subscription {subscription.id}, user already has free plan")
                elif free_plan:
                    # Mark old subscription as CANCELLED
                    subscription.status = Subscription.Status.CANCELLED
                    subscription.save()
                    
                    # Create free plan subscription
                    free_subscription = Subscription.objects.create(
                        user=subscription.user,
                        plan=free_plan,
                        status=Subscription.Status.ACTIVE,
                        start_date=now,
                        payment_provider=Subscription.PaymentProvider.DODO,
                        provider_customer_id=subscription.provider_customer_id or ''
                    )
                    
                    logger.info(f"✅ [Billing Task] Assigned free plan to {subscription.user.email} after cancellation expired")
                    processed_count += 1
                else:
                    logger.error("❌ [Billing Task] No free plan found - cannot assign to expired cancellations")
                    errors.append(f"Subscription {subscription.id}: No free plan available")
                    
        except Exception as e:
            error_msg = f"Subscription {subscription.id} (cancellation): {str(e)}"
            logger.error(f"❌ [Billing Task] Error processing expired cancellation: {error_msg}", exc_info=True)
            errors.append(error_msg)
    
    # Process scheduled downgrades
    for subscription in expired_canceling:
        try:
            with transaction.atomic():
                old_plan = subscription.plan
                new_plan = subscription.downgrade_to_plan
                
                if not new_plan:
                    logger.warning(f"⚠️ [Billing Task] Subscription {subscription.id} has CANCELING status but no downgrade_to_plan")
                    continue
                
                # DO NOT cancel old subscription yet - keep it CANCELING
                # User keeps old plan access until new payment succeeds
                # Old subscription will be cancelled in webhook after payment succeeds
                logger.info(f"📅 [Billing Task] Processing downgrade: {old_plan.name} → {new_plan.name}. Keeping old subscription active until payment succeeds.")
                
                # Create and activate new subscription for downgraded plan
                # For paid plans, create checkout session (user needs to pay for new plan)
                if new_plan.price > 0:
                    # Create PENDING subscription - user will pay for new plan
                    new_subscription = Subscription.objects.create(
                        user=subscription.user,
                        plan=new_plan,
                        status=Subscription.Status.PENDING,  # Will be activated after payment
                        start_date=now,
                        end_date=calculate_subscription_end_date(now),
                        payment_provider=subscription.payment_provider,
                        provider_customer_id=subscription.provider_customer_id
                    )
                    
                    # Create checkout session for new plan
                    try:
                        # Reuse existing customer ID - user already has one from previous subscription
                        # No need to call API again - standard payment provider practice
                        customer_id = subscription.provider_customer_id
                        
                        if not customer_id:
                            # Edge case: No customer ID found, create one (shouldn't happen in normal flow)
                            logger.warning(f"⚠️ [Billing Task] No customer ID found for user {subscription.user.email}, creating new customer")
                            dodo_service = get_dodo_service()
                            customer = dodo_service.get_or_create_customer(
                                email=subscription.user.email,
                                name=subscription.user.get_full_name() or subscription.user.email,
                                metadata={
                                    'user_id': str(subscription.user.id),
                                    'clerk_user_id': subscription.user.clerk_user_id or '',
                                }
                            )
                            customer_id = customer.get('id', '')
                            # Update subscription with new customer ID
                            subscription.provider_customer_id = customer_id
                            subscription.save()
                        
                        dodo_service = get_dodo_service()
                        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
                        return_url = f"{frontend_url}/billing/callback"
                        
                        checkout_metadata = {
                            'subscription_id': str(new_subscription.id),
                            'user_id': str(subscription.user.id),
                            'plan_id': str(new_plan.id),
                            'plan_name': new_plan.name,
                            'is_downgrade': 'true',
                            'from_plan': old_plan.name,
                            'old_subscription_id': str(subscription.id)  # Store old subscription ID for webhook
                        }
                        
                        checkout_session = dodo_service.create_checkout_session(
                            product_id=new_plan.provider_product_id,
                            customer_id=customer_id,
                            return_url=return_url,
                            metadata=checkout_metadata
                        )
                        
                        checkout_id = checkout_session.get('id', '')
                        checkout_url = checkout_session.get('checkout_url', '')
                        
                        logger.info(f"✅ [Billing Task] Created checkout for downgrade: {new_subscription.id} (checkout: {checkout_id})")
                        logger.warning(f"⚠️ [Billing Task] User {subscription.user.email} needs to complete payment for downgraded plan. Checkout URL: {checkout_url}")
                        # Note: In production, you might want to send an email with checkout link
                        # For now, user will need to complete payment when they next log in
                        
                    except Exception as e:
                        logger.error(f"❌ [Billing Task] Failed to create checkout for downgrade: {str(e)}", exc_info=True)
                        errors.append(f"Subscription {subscription.id}: Failed to create checkout - {str(e)}")
                        # Subscription stays PENDING - can be retried or handled manually
                else:
                    # Free plan - activate immediately (no payment needed)
                    # Check if user already has free plan
                    existing_free = Subscription.objects.filter(
                        user=subscription.user,
                        plan=new_plan,
                        status=Subscription.Status.ACTIVE
                    ).first()
                    
                    if existing_free:
                        # User already has free plan, just log it
                        logger.info(f"✅ [Billing Task] User already has free plan, skipping creation")
                        new_subscription = existing_free
                    else:
                        # Create free plan subscription
                        new_subscription = Subscription.objects.create(
                            user=subscription.user,
                            plan=new_plan,
                            status=Subscription.Status.ACTIVE,
                            start_date=now,
                            end_date=None,  # Free plans don't expire
                            payment_provider=subscription.payment_provider,
                            provider_customer_id=subscription.provider_customer_id
                        )
                        logger.info(f"✅ [Billing Task] Activated free plan for downgrade: {new_subscription.id}")
                
                processed_count += 1
                logger.info(f"✅ [Billing Task] Processed downgrade: {subscription.id} → {new_subscription.id if 'new_subscription' in locals() else 'existing'} ({old_plan.name} → {new_plan.name})")
                
        except Exception as e:
            error_msg = f"Subscription {subscription.id}: {str(e)}"
            logger.error(f"❌ [Billing Task] Error processing downgrade: {error_msg}", exc_info=True)
            errors.append(error_msg)
    
    if processed_count > 0:
        logger.info(f"📊 [Billing Task] Processed {processed_count} scheduled downgrades")
    if errors:
        logger.warning(f"⚠️ [Billing Task] {len(errors)} errors occurred during downgrade processing")
    
    return {
        'processed': processed_count,
        'errors': errors
    }

