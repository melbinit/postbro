"""
Webhook handlers for Dodo Payments
These handlers process webhook events from Dodo Payments API

Dodo webhook format:
{
    "business_id": "...",
    "data": { ... },  # Event data
    "timestamp": "...",
    "type": "payment.succeeded" | "subscription.active" | etc.
}
"""
import logging
from typing import Dict
from django.utils import timezone
from accounts.models import User, Subscription
from billing.models import Payment, BillingEvent, Refund
from billing.utils import calculate_subscription_end_date, get_old_active_subscription, calculate_prorated_credit

logger = logging.getLogger(__name__)


def handle_payment_succeeded(payment_data: Dict, billing_event: BillingEvent):
    """
    Handle payment.succeeded event from Dodo
    
    Dodo payment data structure:
    - payment_id: Dodo payment ID
    - subscription_id: Dodo subscription ID
    - total_amount: Amount in cents
    - settlement_amount: Settlement amount in cents
    - currency: Currency code (e.g., "USD", "AED")
    - status: "succeeded"
    - metadata: { subscription_id (our UUID), user_id, plan_id, plan_name }
    """
    try:
        metadata = payment_data.get('metadata', {})
        user_id = metadata.get('user_id')
        subscription_id = metadata.get('subscription_id')  # Our UUID
        
        if not user_id or not subscription_id:
            logger.warning("⚠️ [Dodo Webhook] Missing user_id or subscription_id in payment metadata")
            return
        
        user = User.objects.get(id=user_id)
        subscription = Subscription.objects.get(id=subscription_id)
        
        # Get payment details from Dodo format
        payment_id = payment_data.get('payment_id', '')
        amount_cents = payment_data.get('total_amount') or payment_data.get('settlement_amount', 0)
        amount = float(amount_cents) / 100 if amount_cents else 0  # Convert from cents
        currency = payment_data.get('currency', 'usd').lower()
        dodo_subscription_id = payment_data.get('subscription_id', '')  # Dodo's subscription ID
        
        # Create Payment record
        payment = Payment.objects.create(
            user=user,
            subscription=subscription,
            payment_provider=Payment.PaymentProvider.DODO,
            provider_payment_intent_id=payment_id,
            provider_charge_id=payment_id,  # Dodo may use same ID
            amount=amount,
            currency=currency,
            payment_type=Payment.PaymentType.SUBSCRIPTION,
            status=Payment.Status.SUCCEEDED,
            paid_at=timezone.now(),
            metadata=payment_data
        )
        
        # Check if this is an upgrade or downgrade (has old_subscription_id in metadata)
        old_subscription_id = metadata.get('old_subscription_id')
        is_upgrade = metadata.get('is_upgrade', 'false').lower() == 'true'
        prorated_credit = 0.0
        refund_created = False
        
        if old_subscription_id:
            try:
                old_subscription = Subscription.objects.get(
                    id=old_subscription_id,
                    user=user
                )
                
                # Determine if this is an upgrade or downgrade
                # Check metadata flag first, then compare prices
                if not is_upgrade:
                    # Check prices to determine upgrade vs downgrade
                    is_upgrade = subscription.plan.price > old_subscription.plan.price
                
                # Process based on whether this is upgrade or downgrade
                if is_upgrade and old_subscription.status == Subscription.Status.ACTIVE:
                    # UPGRADE via checkout (old flow): Process refund and cancel old subscription
                    # Note: Upgrades via change-plan API are handled by subscription.plan_changed webhook
                    # This logic only runs for upgrades that went through checkout flow (fallback cases)
                    
                    # Check if this upgrade was done via change-plan API
                    # If subscription has metadata indicating change-plan, skip manual refund
                    payment_metadata = payment_data.get('metadata', {})
                    is_change_plan_upgrade = payment_metadata.get('change_plan', 'false').lower() == 'true'
                    
                    if not is_change_plan_upgrade:
                        # Old checkout flow: Calculate and process refund manually
                        # Calculate prorated credit for upgrade
                        prorated_credit, remaining_days = calculate_prorated_credit(
                            old_subscription,
                            float(subscription.plan.price)
                        )
                        
                        # Process refund if credit > 0 (only for checkout-based upgrades)
                        if prorated_credit > 0:
                            try:
                                from billing.services.dodo_service import get_dodo_service
                                dodo_service = get_dodo_service()
                                
                                # Create refund via Dodo API
                                refund_data = dodo_service.create_refund(
                                    payment_id=payment_id,
                                    amount=prorated_credit,
                                    reason='Prorated credit for plan upgrade',
                                    metadata={
                                        'upgrade_from_plan': old_subscription.plan.name,
                                        'upgrade_to_plan': subscription.plan.name,
                                        'remaining_days': str(remaining_days),
                                        'old_subscription_id': str(old_subscription_id),
                                        'new_subscription_id': str(subscription_id),
                                        'user_id': str(user_id),
                                    }
                                )
                                
                                # Create Refund record in database
                                refund = Refund.objects.create(
                                    payment=payment,
                                    user=user,
                                    payment_provider=Refund.PaymentProvider.DODO,
                                    provider_refund_id=refund_data.get('id', ''),
                                    amount=prorated_credit,
                                    currency=currency,
                                    status=Refund.Status.PENDING,  # Will be updated via webhook
                                    reason='Prorated credit for plan upgrade',
                                    description=f'Upgrade from {old_subscription.plan.name} (${old_subscription.plan.price}/mo) to {subscription.plan.name} (${subscription.plan.price}/mo) - {remaining_days} days remaining on old plan',
                                    metadata=refund_data
                                )
                                
                                refund_created = True
                                logger.info(f"💰 [Dodo Webhook] Proration refund created: ${prorated_credit} (refund_id: {refund.id}, remaining_days: {remaining_days})")
                                
                            except Exception as refund_error:
                                # Log error but don't fail the payment - refund can be processed manually
                                logger.error(f"❌ [Dodo Webhook] Failed to create proration refund: {str(refund_error)}", exc_info=True)
                                logger.warning(f"⚠️ [Dodo Webhook] Payment succeeded but refund failed. Manual refund may be required: ${prorated_credit}")
                    else:
                        logger.info(f"ℹ️ [Dodo Webhook] Upgrade via change-plan API detected, skipping manual refund (handled by subscription.plan_changed)")
                    
                    # Cancel old subscription AFTER refund is initiated (for checkout-based upgrades)
                    # For change-plan upgrades, old subscription is handled by subscription.plan_changed
                    if not is_change_plan_upgrade:
                        old_subscription.status = Subscription.Status.CANCELLED
                        old_subscription.end_date = timezone.now()
                        old_subscription.save()
                        logger.info(f"🔄 [Dodo Webhook] Cancelled old subscription after upgrade: {old_subscription_id}")
                    
                elif not is_upgrade:
                    # DOWNGRADE: Cancel old subscription after payment succeeds
                    # Check if metadata indicates downgrade (from task) or check status
                    is_downgrade_from_metadata = metadata.get('is_downgrade') == 'true'
                    
                    if is_downgrade_from_metadata or old_subscription.status == Subscription.Status.CANCELING:
                        # Old subscription is CANCELING (from task) - cancel it now that new payment succeeded
                        old_subscription.status = Subscription.Status.CANCELLED
                        old_subscription.end_date = timezone.now()
                        
                        # Also cancel in Dodo if it exists
                        if old_subscription.provider_subscription_id and old_subscription.payment_provider == Subscription.PaymentProvider.DODO:
                            try:
                                from billing.services.dodo_service import get_dodo_service
                                dodo_service = get_dodo_service()
                                dodo_service.cancel_subscription(old_subscription.provider_subscription_id)
                                logger.info(f"✅ [Dodo Webhook] Cancelled Dodo subscription: {old_subscription.provider_subscription_id}")
                            except Exception as e:
                                logger.warning(f"⚠️ [Dodo Webhook] Failed to cancel Dodo subscription: {str(e)}")
                        
                        old_subscription.save()
                        logger.info(f"🔄 [Dodo Webhook] Cancelled old subscription after downgrade payment succeeded: {old_subscription_id}")
                    else:
                        # Edge case: Not a scheduled downgrade, but prices indicate downgrade
                        logger.warning(f"⚠️ [Dodo Webhook] Downgrade detected but old subscription {old_subscription_id} status is {old_subscription.status}, skipping cancellation")
                
            except Subscription.DoesNotExist:
                logger.warning(f"⚠️ [Dodo Webhook] Old subscription not found: {old_subscription_id}")
        
        # ALWAYS update provider_subscription_id if we have it (regardless of status)
        if dodo_subscription_id and not subscription.provider_subscription_id:
            subscription.provider_subscription_id = dodo_subscription_id
            logger.info(f"✅ [Dodo Webhook] Updated provider_subscription_id: {dodo_subscription_id}")
        
        # Activate subscription if it's PENDING (or TRIAL for backward compatibility)
        if subscription.status in [Subscription.Status.PENDING, Subscription.Status.TRIAL]:
            subscription.status = Subscription.Status.ACTIVE
            subscription.start_date = timezone.now()
            
            # Set end_date (30 days from start_date)
            if not subscription.end_date:
                subscription.end_date = calculate_subscription_end_date(
                    subscription.start_date,
                    billing_period_days=30
                )
            
            subscription.save()
            logger.info(f"✅ [Dodo Webhook] Activated subscription: {subscription_id} (end_date: {subscription.end_date})")
                    
        elif subscription.status == Subscription.Status.ACTIVE:
            # Update provider_subscription_id even if already active
            if dodo_subscription_id:
                subscription.save()
            logger.info(f"ℹ️ [Dodo Webhook] Subscription already active: {subscription_id}")
        else:
            # Update provider_subscription_id even for other statuses
            if dodo_subscription_id:
                subscription.save()
            logger.warning(f"⚠️ [Dodo Webhook] Payment succeeded but subscription status is {subscription.status}: {subscription_id}")
        
        billing_event.user = user
        billing_event.subscription = subscription
        billing_event.save()
        
        logger.info(f"✅ [Dodo Webhook] Payment succeeded: {payment.id} for subscription {subscription_id}")
        
    except (User.DoesNotExist, Subscription.DoesNotExist) as e:
        logger.error(f"❌ [Dodo Webhook] {type(e).__name__}: {e}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling payment succeeded: {str(e)}", exc_info=True)


def handle_subscription_active(subscription_data: Dict, billing_event: BillingEvent):
    """
    Handle subscription.active event from Dodo
    
    Dodo subscription data structure:
    - subscription_id: Dodo subscription ID
    - status: "active"
    - metadata: { subscription_id (our UUID), user_id, plan_id, plan_name }
    """
    try:
        metadata = subscription_data.get('metadata', {})
        user_id = metadata.get('user_id')
        subscription_id = metadata.get('subscription_id')  # Our UUID
        dodo_subscription_id = subscription_data.get('subscription_id', '')  # Dodo's ID
        
        if not user_id:
            logger.warning("⚠️ [Dodo Webhook] Missing user_id in subscription metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Find subscription by our UUID (preferred) or Dodo's subscription ID
        subscription = None
        if subscription_id:
            try:
                subscription = Subscription.objects.get(id=subscription_id, user=user)
            except Subscription.DoesNotExist:
                pass
        
        if not subscription and dodo_subscription_id:
            subscription = Subscription.objects.filter(
                user=user,
                provider_subscription_id=dodo_subscription_id
            ).first()
        
        if subscription:
            # ALWAYS update provider_subscription_id if we have it (regardless of status)
            if dodo_subscription_id and not subscription.provider_subscription_id:
                subscription.provider_subscription_id = dodo_subscription_id
                logger.info(f"✅ [Dodo Webhook] Updated provider_subscription_id: {dodo_subscription_id}")
            
            # Handle old subscription cancellation for upgrades (if not already handled by payment.succeeded)
            old_subscription_id = metadata.get('old_subscription_id')
            is_upgrade = metadata.get('is_upgrade', 'false').lower() == 'true'
            
            if old_subscription_id and is_upgrade:
                try:
                    old_subscription = Subscription.objects.get(
                        id=old_subscription_id,
                        user=user,
                        status=Subscription.Status.ACTIVE
                    )
                    # Only cancel if still active (might have been cancelled by payment.succeeded already)
                    old_subscription.status = Subscription.Status.CANCELLED
                    old_subscription.end_date = timezone.now()
                    old_subscription.save()
                    logger.info(f"🔄 [Dodo Webhook] Cancelled old subscription after upgrade: {old_subscription_id}")
                except Subscription.DoesNotExist:
                    logger.warning(f"⚠️ [Dodo Webhook] Old subscription not found: {old_subscription_id}")
                except Exception as e:
                    logger.warning(f"⚠️ [Dodo Webhook] Error cancelling old subscription: {str(e)}")
            
            # Activate subscription if it's PENDING or TRIAL
            if subscription.status in [Subscription.Status.PENDING, Subscription.Status.TRIAL]:
                subscription.status = Subscription.Status.ACTIVE
                subscription.start_date = timezone.now()
                subscription.end_date = calculate_subscription_end_date(subscription.start_date)
                subscription.save()
                logger.info(f"✅ [Dodo Webhook] Subscription activated: {subscription.id} (was {subscription.status})")
            elif subscription.status == Subscription.Status.ACTIVE:
                # Update provider_subscription_id even if already active
                if dodo_subscription_id:
                    subscription.save()
                logger.info(f"ℹ️ [Dodo Webhook] Subscription already active: {subscription.id}")
            else:
                # Update provider_subscription_id even for other statuses
                if dodo_subscription_id:
                    subscription.save()
                logger.warning(f"⚠️ [Dodo Webhook] Subscription active event but status is {subscription.status}: {subscription.id}")
            
            billing_event.user = user
            billing_event.subscription = subscription
            billing_event.save()
        else:
            logger.warning(f"⚠️ [Dodo Webhook] Subscription not found for user {user_id}")
            
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling subscription active: {str(e)}", exc_info=True)


def handle_subscription_renewed(subscription_data: Dict, billing_event: BillingEvent):
    """
    Handle subscription.renewed event from Dodo
    Similar to subscription.active but for renewals
    """
    # Treat renewal same as active - ensure subscription stays active
    handle_subscription_active(subscription_data, billing_event)
    logger.info("ℹ️ [Dodo Webhook] Subscription renewed")


def handle_subscription_plan_changed(subscription_data: Dict, billing_event: BillingEvent):
    """
    Handle subscription.plan_changed event from Dodo
    Fired when change-plan API succeeds
    
    Dodo subscription data structure:
    - subscription_id: Dodo subscription ID
    - product_id: New product ID
    - metadata: { user_id, old_plan_id, new_plan_id, old_subscription_id, is_upgrade }
    """
    try:
        from django.db import transaction
        
        metadata = subscription_data.get('metadata', {})
        user_id = metadata.get('user_id')
        dodo_subscription_id = subscription_data.get('id', '')  # Dodo's subscription ID
        new_product_id = subscription_data.get('product', {}).get('id') or subscription_data.get('product_id', '')
        
        if not user_id or not dodo_subscription_id:
            logger.warning("⚠️ [Dodo Webhook] Missing user_id or subscription_id in plan_changed event")
            return
        
        user = User.objects.get(id=user_id)
        
        # Find subscription by provider_subscription_id
        subscription = Subscription.objects.filter(
            user=user,
            provider_subscription_id=dodo_subscription_id,
            payment_provider=Subscription.PaymentProvider.DODO
        ).first()
        
        if not subscription:
            logger.warning(f"⚠️ [Dodo Webhook] Subscription not found for plan_changed event: {dodo_subscription_id}")
            return
        
        # Get new plan from metadata or find by product_id
        new_plan_id = metadata.get('new_plan_id')
        old_subscription_id = metadata.get('old_subscription_id')
        is_upgrade = metadata.get('is_upgrade', 'false').lower() == 'true'
        
        with transaction.atomic():
            # Find new plan
            new_plan = None
            if new_plan_id:
                try:
                    from accounts.models import Plan
                    new_plan = Plan.objects.get(id=new_plan_id, is_active=True)
                except Plan.DoesNotExist:
                    logger.error(f"❌ [Dodo Webhook] New plan not found: {new_plan_id}")
                    # Try to find by product_id as fallback
                    if new_product_id:
                        new_plan = Plan.objects.filter(provider_product_id=new_product_id, is_active=True).first()
            
            if not new_plan:
                logger.error(f"❌ [Dodo Webhook] Could not find new plan for plan_changed event")
                return
            
            # Update subscription plan
            old_plan = subscription.plan
            subscription.plan = new_plan
            subscription.status = Subscription.Status.ACTIVE  # Ensure it's active
            subscription.save()
            
            logger.info(f"✅ [Dodo Webhook] Plan changed: {old_plan.name} → {new_plan.name} (subscription: {subscription.id})")
            
            # Handle old subscription cancellation for upgrades
            if is_upgrade and old_subscription_id:
                try:
                    old_subscription = Subscription.objects.get(
                        id=old_subscription_id,
                        user=user
                    )
                    # Only cancel if it's different from current subscription
                    if old_subscription.id != subscription.id and old_subscription.status != Subscription.Status.CANCELLED:
                        old_subscription.status = Subscription.Status.CANCELLED
                        old_subscription.end_date = timezone.now()
                        old_subscription.save()
                        logger.info(f"🔄 [Dodo Webhook] Cancelled old subscription after plan change: {old_subscription_id}")
                except Subscription.DoesNotExist:
                    logger.warning(f"⚠️ [Dodo Webhook] Old subscription not found: {old_subscription_id}")
                except Exception as e:
                    logger.warning(f"⚠️ [Dodo Webhook] Error cancelling old subscription: {str(e)}")
            
            billing_event.user = user
            billing_event.subscription = subscription
            billing_event.save()
            
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling plan_changed: {str(e)}", exc_info=True)


def handle_subscription_failed(subscription_data: Dict, billing_event: BillingEvent):
    """
    Handle subscription.failed event from Dodo
    
    Dodo subscription data structure:
    - subscription_id: Dodo subscription ID
    - status: "failed"
    - metadata: { subscription_id (our UUID), user_id, plan_id, plan_name }
    """
    try:
        metadata = subscription_data.get('metadata', {})
        user_id = metadata.get('user_id')
        subscription_id = metadata.get('subscription_id')  # Our UUID
        dodo_subscription_id = subscription_data.get('subscription_id', '')  # Dodo's ID
        
        if not user_id:
            logger.warning("⚠️ [Dodo Webhook] Missing user_id in subscription metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Find subscription
        subscription = None
        if subscription_id:
            try:
                subscription = Subscription.objects.get(id=subscription_id, user=user)
            except Subscription.DoesNotExist:
                pass
        
        if not subscription and dodo_subscription_id:
            subscription = Subscription.objects.filter(
                user=user,
                provider_subscription_id=dodo_subscription_id
            ).first()
        
        if subscription:
            # Mark subscription as FAILED (aligns with Dodo's status: "failed")
            # Only mark as failed if not already ACTIVE (active subscriptions might fail later, but we handle that separately)
            if subscription.status != Subscription.Status.ACTIVE:
                subscription.status = Subscription.Status.FAILED
                subscription.end_date = timezone.now()
                subscription.save()
                logger.info(f"❌ [Dodo Webhook] Subscription failed: {subscription.id} (was {subscription.status})")
            else:
                # If already active, this might be a renewal failure - mark as failed
                subscription.status = Subscription.Status.FAILED
                subscription.end_date = timezone.now()
                subscription.save()
                logger.warning(f"⚠️ [Dodo Webhook] Active subscription failed: {subscription.id} - marked as failed")
            
            billing_event.user = user
            billing_event.subscription = subscription
            billing_event.save()
        else:
            logger.warning(f"⚠️ [Dodo Webhook] Subscription not found for user {user_id}")
            
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling subscription failed: {str(e)}", exc_info=True)


def handle_payment_failed(payment_data: Dict, billing_event: BillingEvent):
    """
    Handle payment.failed event from Dodo
    
    Dodo payment data structure:
    - payment_id: Dodo payment ID
    - subscription_id: Dodo subscription ID
    - total_amount: Amount in cents
    - currency: Currency code
    - status: "failed"
    - error_code: Error code (e.g., "INSUFFICIENT_FUNDS")
    - error_message: Error message
    - metadata: { subscription_id (our UUID), user_id, plan_id, plan_name }
    """
    try:
        metadata = payment_data.get('metadata', {})
        user_id = metadata.get('user_id')
        subscription_id = metadata.get('subscription_id')
        
        if not user_id:
            logger.warning("⚠️ [Dodo Webhook] No user_id in payment metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Mark subscription as FAILED when payment fails (aligns with Dodo's payment.failed event)
        if subscription_id:
            try:
                subscription = Subscription.objects.get(id=subscription_id, user=user)
                is_downgrade_payment = metadata.get('is_downgrade') == 'true'
                old_subscription_id = metadata.get('old_subscription_id')
                
                # Mark new subscription as FAILED
                if subscription.status in [Subscription.Status.PENDING, Subscription.Status.TRIAL]:
                    subscription.status = Subscription.Status.FAILED
                    subscription.end_date = timezone.now()
                    subscription.save()
                    
                    # For downgrades: Old subscription stays CANCELING (user keeps access to retry payment)
                    if is_downgrade_payment and old_subscription_id:
                        try:
                            old_subscription = Subscription.objects.get(id=old_subscription_id, user=user)
                            # Old subscription remains CANCELING - user keeps access
                            logger.warning(f"⚠️ [Dodo Webhook] Downgrade payment failed for {subscription_id}. Old subscription {old_subscription_id} remains active for retry.")
                            logger.info(f"ℹ️ [Dodo Webhook] User can retry payment. Old plan ({old_subscription.plan.name}) remains active.")
                        except Subscription.DoesNotExist:
                            logger.warning(f"⚠️ [Dodo Webhook] Old subscription {old_subscription_id} not found for downgrade payment failure")
                    
                    logger.info(f"❌ [Dodo Webhook] Payment failed - subscription marked as failed: {subscription_id} (was {subscription.status})")
                    
                elif subscription.status == Subscription.Status.ACTIVE:
                    # Active subscription payment failed - mark as failed (renewal failure)
                    subscription.status = Subscription.Status.FAILED
                    subscription.end_date = timezone.now()
                    subscription.save()
                    logger.warning(f"⚠️ [Dodo Webhook] Payment failed for active subscription: {subscription_id} - marked as failed")
            except Subscription.DoesNotExist:
                pass
        
        # Create failed payment record
        payment_id = payment_data.get('payment_id', '')
        amount_cents = payment_data.get('total_amount', 0)
        amount = float(amount_cents) / 100 if amount_cents else 0
        
        payment = Payment.objects.create(
            user=user,
            payment_provider=Payment.PaymentProvider.DODO,
            provider_payment_intent_id=payment_id,
            amount=amount,
            currency=payment_data.get('currency', 'usd').lower(),
            status=Payment.Status.FAILED,
            failed_at=timezone.now(),
            failure_reason=payment_data.get('error_message', ''),  # Dodo uses error_message
            failure_code=payment_data.get('error_code', ''),  # Dodo uses error_code
            metadata=payment_data
        )
        
        error_msg = payment_data.get('error_message', 'Unknown error')
        logger.info(f"❌ [Dodo Webhook] Payment failed: {payment.id} - {error_msg}")
        
        billing_event.user = user
        billing_event.save()
        
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling payment failed: {str(e)}", exc_info=True)


def handle_refund_succeeded(refund_data: Dict, billing_event: BillingEvent):
    """
    Handle refund.succeeded event from Dodo
    
    Dodo refund data structure:
    - refund_id: Dodo refund ID
    - payment_id: Dodo payment ID
    - amount: Refund amount in cents
    - currency: Currency code
    - status: "succeeded"
    - metadata: Additional metadata
    """
    try:
        refund_id = refund_data.get('refund_id', '') or refund_data.get('id', '')
        payment_id = refund_data.get('payment_id', '')
        
        if not refund_id:
            logger.warning("⚠️ [Dodo Webhook] Missing refund_id in refund data")
            return
        
        # Find refund by provider_refund_id
        refund = Refund.objects.filter(
            provider_refund_id=refund_id
        ).first()
        
        if refund:
            refund.status = Refund.Status.SUCCEEDED
            refund.processed_at = timezone.now()
            refund.save()
            
            # Update payment status if fully refunded
            payment = refund.payment
            total_refunded = sum(
                r.amount for r in payment.refunds.filter(status=Refund.Status.SUCCEEDED)
            )
            if total_refunded >= payment.amount:
                payment.status = Payment.Status.REFUNDED
            else:
                payment.status = Payment.Status.PARTIALLY_REFUNDED
            payment.save()
            
            logger.info(f"✅ [Dodo Webhook] Refund succeeded: {refund.id} (${refund.amount})")
            
            billing_event.user = refund.user
            billing_event.save()
        else:
            logger.warning(f"⚠️ [Dodo Webhook] Refund not found in database: {refund_id}")
            
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling refund succeeded: {str(e)}", exc_info=True)


def handle_refund_failed(refund_data: Dict, billing_event: BillingEvent):
    """
    Handle refund.failed event from Dodo
    """
    try:
        refund_id = refund_data.get('refund_id', '') or refund_data.get('id', '')
        
        if not refund_id:
            logger.warning("⚠️ [Dodo Webhook] Missing refund_id in refund data")
            return
        
        refund = Refund.objects.filter(
            provider_refund_id=refund_id
        ).first()
        
        if refund:
            refund.status = Refund.Status.FAILED
            refund.save()
            logger.warning(f"❌ [Dodo Webhook] Refund failed: {refund.id}")
            
            billing_event.user = refund.user
            billing_event.save()
        else:
            logger.warning(f"⚠️ [Dodo Webhook] Refund not found: {refund_id}")
            
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling refund failed: {str(e)}", exc_info=True)

