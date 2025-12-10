"""
Billing views for subscription management
"""
import logging
import json
import os
from typing import Dict
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import HttpResponse, JsonResponse
from accounts.models import User, Plan, Subscription
from accounts.serializers import SubscriptionSerializer, SubscriptionCreateSerializer
from accounts.utils import get_user_subscription, get_user_plan
from billing.models import Payment, Invoice, BillingEvent, PaymentMethod
from billing.services.dodo_service import get_dodo_service
from billing.webhook_handlers import (
    handle_payment_succeeded,
    handle_subscription_active,
    handle_subscription_renewed,
    handle_subscription_plan_changed,
    handle_subscription_failed,
    handle_payment_failed,
    handle_refund_succeeded,
    handle_refund_failed
)
from billing.utils import (
    calculate_prorated_credit,
    calculate_subscription_end_date,
    get_old_active_subscription
)
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

logger = logging.getLogger(__name__)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def subscribe_to_plan(request):
    """
    Subscribe to a paid plan
    Creates Dodo checkout session for paid plans
    Proper SaaS flow: Doesn't cancel old subscription until new payment succeeds
    """
    try:
        serializer = SubscriptionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        plan_id = serializer.validated_data['plan_id']
        plan = Plan.objects.get(id=plan_id, is_active=True)
        
        # Check if user already has active subscription
        current_subscription = get_user_subscription(request.user)
        
        # Track old subscription for upgrade/downgrade handling
        old_subscription_id = None
        prorated_credit = 0.0
        remaining_days = 0
        is_upgrade = False
        is_downgrade = False
        
        if current_subscription:
            # User already has subscription
            if current_subscription.plan.id == plan.id:
                return Response(
                    {'error': 'You are already subscribed to this plan'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Determine if this is an upgrade or downgrade
            if plan.price > current_subscription.plan.price:
                is_upgrade = True
                # Calculate prorated credit for upgrade
                prorated_credit, remaining_days = calculate_prorated_credit(
                    current_subscription,
                    float(plan.price)
                )
                logger.info(f"💰 [Billing] Upgrade detected: ${prorated_credit} credit ({remaining_days} days remaining)")
            elif plan.price < current_subscription.plan.price:
                is_downgrade = True
                logger.info(f"📉 [Billing] Downgrade detected: ${current_subscription.plan.price}/mo → ${plan.price}/mo")
            
            # Store old subscription ID
            old_subscription_id = str(current_subscription.id)
            
            # Handle downgrades: Schedule at period end (industry standard)
            # User keeps current plan until period ends, then switches to downgraded plan
            # This applies to BOTH paid→paid and paid→free downgrades
            if is_downgrade:
                # IMPORTANT: Clear any other scheduled downgrades for this user
                # This prevents multiple downgrades from being scheduled
                # This can happen if user downgrades multiple times before the first downgrade is processed
                other_scheduled_downgrades = Subscription.objects.filter(
                    user=request.user,
                    status=Subscription.Status.CANCELING,
                    downgrade_to_plan__isnull=False
                )
                
                # Exclude current subscription if it exists
                if current_subscription:
                    other_scheduled_downgrades = other_scheduled_downgrades.exclude(id=current_subscription.id)
                
                if other_scheduled_downgrades.exists():
                    logger.info(f"🔄 [Billing] Clearing {other_scheduled_downgrades.count()} other scheduled downgrade(s) before scheduling new one")
                    for old_downgrade in other_scheduled_downgrades:
                        old_plan_name = old_downgrade.downgrade_to_plan.name if old_downgrade.downgrade_to_plan else "unknown"
                        old_downgrade.downgrade_to_plan = None
                        # If the old subscription has expired, mark it as CANCELLED
                        if old_downgrade.end_date and old_downgrade.end_date < timezone.now():
                            old_downgrade.status = Subscription.Status.CANCELLED
                            logger.info(f"🗑️ [Billing] Marking expired scheduled downgrade as CANCELLED: {old_downgrade.id}")
                        old_downgrade.save()
                        logger.info(f"🧹 [Billing] Cleared scheduled downgrade from {old_downgrade.plan.name} → {old_plan_name}")
                
                # Edge case: If user already has a scheduled downgrade on current subscription, update it
                if current_subscription.status == Subscription.Status.CANCELING and current_subscription.downgrade_to_plan:
                    logger.info(f"🔄 [Billing] Updating existing downgrade: {current_subscription.downgrade_to_plan.name} → {plan.name}")
                
                # Mark current subscription as CANCELING and store target plan
                # User keeps current plan features until period ends (regardless of target plan being free or paid)
                current_subscription.status = Subscription.Status.CANCELING
                current_subscription.downgrade_to_plan = plan
                # Keep original end_date - user retains access until period ends
                # Ensure end_date is set (should already be set, but safety check)
                if not current_subscription.end_date:
                    current_subscription.end_date = calculate_subscription_end_date(
                        current_subscription.start_date,
                        billing_period_days=30
                    )
                current_subscription.save()
                
                logger.info(f"📅 [Billing] Scheduled downgrade: {current_subscription.plan.name} → {plan.name} at {current_subscription.end_date}")
                
                # Return CURRENT subscription (not a new one) - user stays on it until period ends
                # This ensures user keeps paid plan benefits until period ends, even if downgrading to free
                return Response(
                    {
                        'message': f'Downgrade scheduled. You will switch to {plan.name} plan at the end of your current billing period ({current_subscription.end_date.strftime("%B %d, %Y")}). You will continue to have access to {current_subscription.plan.name} features until then.',
                        'subscription': SubscriptionSerializer(current_subscription).data,  # Current subscription, not new
                        'downgrade': True,
                        'scheduled_at': current_subscription.end_date.isoformat(),
                        'current_plan': current_subscription.plan.name,
                        'downgrade_to_plan': plan.name
                    },
                    status=status.HTTP_200_OK  # Not 201 - we're not creating new subscription
                )
            
            # Edge case: If user upgrades while downgrade is scheduled, cancel the downgrade
            if is_upgrade and current_subscription.status == Subscription.Status.CANCELING and current_subscription.downgrade_to_plan:
                logger.info(f"🔄 [Billing] Cancelling scheduled downgrade due to upgrade: {current_subscription.downgrade_to_plan.name} → {plan.name}")
                current_subscription.downgrade_to_plan = None
                # Status will be updated to ACTIVE after upgrade payment succeeds (in webhook)
            
            # Handle upgrades using change-plan API (if conditions are met)
            if is_upgrade:
                # Check if we can use change-plan API
                # Requirements:
                # 1. Must have provider_subscription_id (existing Dodo subscription)
                # 2. Must be ACTIVE (webhook has processed, subscription is live)
                if current_subscription.provider_subscription_id and \
                   current_subscription.status == Subscription.Status.ACTIVE and \
                   current_subscription.payment_provider == Subscription.PaymentProvider.DODO:
                    
                    # Use change-plan API for upgrade
                    if not plan.provider_product_id:
                        return Response(
                            {
                                'error': 'Plan not configured for payments',
                                'message': 'This plan does not have a payment product ID configured. Please contact support.'
                            },
                            status=status.HTTP_400_BAD_REQUEST
                        )
                    
                    try:
                        dodo_service = get_dodo_service()
                        
                        # Prepare metadata for webhook handling
                        change_plan_metadata = {
                            'user_id': str(request.user.id),
                            'old_plan_id': str(current_subscription.plan.id),
                            'new_plan_id': str(plan.id),
                            'old_plan_name': current_subscription.plan.name,
                            'new_plan_name': plan.name,
                            'old_subscription_id': str(current_subscription.id),
                            'is_upgrade': 'true',
                        }
                        
                        # Call change-plan API with prorated_immediately mode
                        result = dodo_service.change_subscription_plan(
                            subscription_id=current_subscription.provider_subscription_id,
                            product_id=plan.provider_product_id,
                            proration_billing_mode='prorated_immediately',
                            quantity=1,
                            metadata=change_plan_metadata
                        )
                        
                        # Update subscription in our DB (plan will be updated after webhook confirms)
                        # Mark as PENDING until webhook confirms payment
                        current_subscription.status = Subscription.Status.PENDING
                        current_subscription.save()
                        
                        logger.info(f"✅ [Billing] Upgrade initiated via change-plan API: {current_subscription.id} (Dodo subscription: {current_subscription.provider_subscription_id})")
                        
                        # Return response - no redirect needed, payment is processed by Dodo
                        return Response(
                            {
                                'message': f'Upgrade to {plan.name} initiated. Your plan will be updated once payment is processed.',
                                'subscription': SubscriptionSerializer(current_subscription).data,
                                'upgrade': True,
                                'payment_id': result.get('payment_id'),
                                'status': result.get('status'),
                            },
                            status=status.HTTP_200_OK
                        )
                        
                    except Exception as e:
                        logger.error(f"❌ [Billing] Failed to change plan via API: {str(e)}", exc_info=True)
                        # Fallback to checkout flow if change-plan fails
                        logger.warning(f"⚠️ [Billing] Falling back to checkout flow for upgrade")
                        # Continue to checkout flow below
                else:
                    # Fallback to checkout for upgrades when:
                    # - No provider_subscription_id (Free → Paid, or first subscription)
                    # - Status is PENDING (webhook hasn't processed yet)
                    # - Payment provider is not DODO
                    logger.info(f"ℹ️ [Billing] Upgrade cannot use change-plan API, falling back to checkout. "
                              f"Reason: provider_subscription_id={bool(current_subscription.provider_subscription_id)}, "
                              f"status={current_subscription.status}")
                    # Continue to checkout flow below
            
            # For upgrades using checkout: DON'T cancel old subscription yet - wait for webhook confirmation
        
        # Create new subscription
        # For free plan, activate immediately
        # For paid plans, create Dodo checkout session
        if plan.price == 0:
            # Free plan - activate immediately
            new_subscription = Subscription.objects.create(
                user=request.user,
                plan=plan,
                status=Subscription.Status.ACTIVE,
                start_date=timezone.now(),
                payment_provider=Subscription.PaymentProvider.DODO
            )
        else:
            # Paid plan - create Dodo checkout session
            if not plan.provider_product_id:
                return Response(
                    {
                        'error': 'Plan not configured for payments',
                        'message': 'This plan does not have a payment product ID configured. Please contact support.'
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                # Check if user already has a Dodo customer ID in existing subscriptions
                # This avoids unnecessary API calls - standard payment provider practice
                existing_subscription = Subscription.objects.filter(
                    user=request.user,
                    payment_provider=Subscription.PaymentProvider.DODO,
                    provider_customer_id__isnull=False
                ).exclude(provider_customer_id='').first()
                
                if existing_subscription and existing_subscription.provider_customer_id:
                    # Reuse existing customer ID - no API call needed
                    customer_id = existing_subscription.provider_customer_id
                    logger.info(f"✅ [Billing] Reusing existing Dodo customer ID: {customer_id}")
                else:
                    # First time user - create customer in Dodo
                    dodo_service = get_dodo_service()
                    customer = dodo_service.get_or_create_customer(
                        email=request.user.email,
                        name=request.user.get_full_name() or request.user.email,
                        metadata={
                            'user_id': str(request.user.id),
                            'clerk_user_id': request.user.clerk_user_id or '',
                        }
                    )
                    customer_id = customer.get('id', '')
                    logger.info(f"✅ [Billing] Created new Dodo customer: {customer_id}")
                
                # Create pending subscription - will be activated only after webhook confirms payment
                new_subscription = Subscription.objects.create(
                    user=request.user,
                    plan=plan,
                    status=Subscription.Status.PENDING,  # Only activated after payment confirmation via webhook
                    start_date=timezone.now(),
                    payment_provider=Subscription.PaymentProvider.DODO,
                    provider_customer_id=customer_id
                )
                
                # Build return URL (frontend callback page)
                # Dodo will redirect here after payment (success or failure)
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
                return_url = f"{frontend_url}/billing/callback"
                
                # Prepare metadata for checkout session
                checkout_metadata = {
                    'subscription_id': str(new_subscription.id),
                    'user_id': str(request.user.id),
                    'plan_id': str(plan.id),
                    'plan_name': plan.name,
                }
                
                # Add old subscription info if upgrading (only for upgrades, not downgrades)
                if old_subscription_id and is_upgrade:
                    checkout_metadata['old_subscription_id'] = old_subscription_id
                    checkout_metadata['prorated_credit'] = str(prorated_credit)
                    checkout_metadata['remaining_days'] = str(remaining_days)
                    checkout_metadata['is_upgrade'] = 'true'  # Flag to distinguish from downgrades
                
                # Create checkout session
                # Note: Dodo will handle proration if configured, or we can pass discount
                dodo_service = get_dodo_service()
                checkout_session = dodo_service.create_checkout_session(
                    product_id=plan.provider_product_id,
                    customer_id=customer_id,
                    return_url=return_url,
                    metadata=checkout_metadata
                )
                
                # Update return URL with checkout ID for status checking
                # Note: We use checkout_id to find subscription via metadata, not subscription_id
                # because Dodo may add their own subscription_id parameter which would conflict
                checkout_id = checkout_session.get('id', '')
                if checkout_id:
                    return_url = f"{frontend_url}/billing/callback?checkout_id={checkout_id}"
                
                logger.info(f"✅ [Billing] Created Dodo checkout session {checkout_id} for subscription {new_subscription.id}")
                
                return Response(
                    {
                        'message': 'Checkout session created',
                        'checkout_url': checkout_session.get('checkout_url'),
                        'checkout_id': checkout_id,
                        'subscription_id': str(new_subscription.id),
                        'plan': plan.name
                    },
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                logger.error(f"❌ [Billing] Failed to create Dodo checkout: {str(e)}", exc_info=True)
                return Response(
                    {
                        'error': 'Failed to create checkout session',
                        'message': str(e)
                    },
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        subscription_serializer = SubscriptionSerializer(new_subscription)
        
        return Response(
            {
                'message': f'Successfully subscribed to {plan.name} plan',
                'subscription': subscription_serializer.data
            },
            status=status.HTTP_201_CREATED
        )
        
    except Plan.DoesNotExist:
        return Response(
            {'error': 'Plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        logger.error(f"❌ [Billing] Subscribe error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to create subscription: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_plan(request):
    """
    Upgrade to a higher plan
    """
    try:
        serializer = SubscriptionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_plan_id = serializer.validated_data['plan_id']
        new_plan = Plan.objects.get(id=new_plan_id, is_active=True)
        
        current_subscription = get_user_subscription(request.user)
        
        if not current_subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        current_plan = current_subscription.plan
        
        # Check if it's actually an upgrade
        if new_plan.price <= current_plan.price:
            return Response(
                {'error': 'This is not an upgrade. Use downgrade endpoint or subscribe endpoint.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel current subscription
        current_subscription.status = Subscription.Status.CANCELLED
        current_subscription.end_date = timezone.now()
        current_subscription.save()
        
        # Create new subscription
        new_subscription = Subscription.objects.create(
            user=request.user,
            plan=new_plan,
            status=Subscription.Status.ACTIVE,
            start_date=timezone.now()
        )
        
        subscription_serializer = SubscriptionSerializer(new_subscription)
        
        return Response(
            {
                'message': f'Successfully upgraded to {new_plan.name} plan',
                'subscription': subscription_serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Plan.DoesNotExist:
        return Response(
            {'error': 'Plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to upgrade: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel current subscription
    """
    try:
        current_subscription = get_user_subscription(request.user)
        
        if not current_subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Can't cancel free plan (just switch to it)
        if current_subscription.plan.price == 0:
            return Response(
                {'error': 'Free plan cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel subscription in payment provider for end-of-period cancellation
        if current_subscription.provider_subscription_id and current_subscription.payment_provider == Subscription.PaymentProvider.DODO:
            try:
                dodo_service = get_dodo_service()
                # Cancel in Dodo (they handle end-of-period cancellation)
                dodo_service.cancel_subscription(current_subscription.provider_subscription_id)
                logger.info(f"✅ [Billing] Cancelled Dodo subscription: {current_subscription.provider_subscription_id}")
            except Exception as e:
                logger.error(f"❌ [Billing] Failed to cancel Dodo subscription: {str(e)}", exc_info=True)
                # Continue with local cancellation even if Dodo cancellation fails
        
        # End-of-period cancellation - user keeps access until end_date
        # Don't change end_date if it exists (user paid until then)
        if not current_subscription.end_date:
            # If no end_date, set it to 30 days from start_date
            from billing.utils import calculate_subscription_end_date
            current_subscription.end_date = calculate_subscription_end_date(
                current_subscription.start_date,
                billing_period_days=30
            )
        
        # Mark as canceling (user keeps access until end_date)
        # Clear any scheduled downgrade if user is cancelling instead
        current_subscription.status = Subscription.Status.CANCELING
        current_subscription.downgrade_to_plan = None  # Clear scheduled downgrade
        current_subscription.save()
        
        logger.info(f"📅 [Billing] Subscription set to cancel at period end: {current_subscription.id}, end_date: {current_subscription.end_date}")
        
        # Don't assign free plan immediately - user keeps current plan until end_date
        # Free plan will be assigned when subscription expires (can be done via scheduled task later)
        
        subscription_serializer = SubscriptionSerializer(current_subscription)
        
        return Response(
            {
                'message': 'Subscription cancelled successfully',
                'subscription': subscription_serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"❌ [Billing] Cancel error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to cancel subscription: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_history(request):
    """
    Get user's subscription history
    """
    try:
        subscriptions = Subscription.objects.filter(
            user=request.user
        ).select_related('plan').order_by('-created_at')
        
        serializer = SubscriptionSerializer(subscriptions, many=True)
        
        return Response(
            {
                'subscriptions': serializer.data,
                'count': len(serializer.data)
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch subscription history: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@require_http_methods(["POST"])
def dodo_webhook(request):
    """
    Handle webhooks from Dodo Payments
    
    Events handled:
    - checkout.session.completed: Activate subscription
    - payment.succeeded: Create Payment record
    - subscription.active: Update subscription status
    - subscription.on_hold: Handle failed payment
    - payment.failed: Handle payment failure
    """
    try:
        # Get raw payload for signature verification
        payload = request.body
        
        # ========== DEBUG: Log all webhook data ==========
        logger.info("=" * 80)
        logger.info("🔍 [DODO WEBHOOK DEBUG] Full Webhook Data")
        logger.info("=" * 80)
        
        # Log all headers
        logger.info("\n📋 ALL HEADERS:")
        logger.info("-" * 80)
        for key, value in request.headers.items():
            logger.info(f"  {key}: {value}")
        
        # Log META headers (Django's raw headers)
        logger.info("\n📋 META HEADERS (HTTP_*):")
        logger.info("-" * 80)
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                logger.info(f"  {key}: {value}")
        
        # Log specific signature headers
        logger.info("\n🔐 SIGNATURE HEADERS:")
        logger.info("-" * 80)
        logger.info(f"  svix-signature: {request.headers.get('svix-signature', 'NOT FOUND')}")
        logger.info(f"  X-Dodo-Signature: {request.headers.get('X-Dodo-Signature', 'NOT FOUND')}")
        logger.info(f"  webhook-signature: {request.headers.get('webhook-signature', 'NOT FOUND')}")
        logger.info(f"  svix-id: {request.headers.get('svix-id', 'NOT FOUND')}")
        logger.info(f"  svix-timestamp: {request.headers.get('svix-timestamp', 'NOT FOUND')}")
        
        # Log payload info
        logger.info("\n📦 PAYLOAD INFO:")
        logger.info("-" * 80)
        logger.info(f"  Payload length: {len(payload)} bytes")
        logger.info(f"  Payload type: {type(payload)}")
        try:
            payload_str = payload.decode('utf-8')
            logger.info(f"  Payload preview (first 500 chars): {payload_str[:500]}")
            logger.info(f"  Full payload: {payload_str}")
        except Exception as e:
            logger.error(f"  Error decoding payload: {e}")
        
        # Log webhook secret status
        logger.info("\n🔑 WEBHOOK SECRET:")
        logger.info("-" * 80)
        dodo_service = get_dodo_service()
        if dodo_service.webhook_secret:
            secret_preview = dodo_service.webhook_secret[:10] + "..." if len(dodo_service.webhook_secret) > 10 else dodo_service.webhook_secret
            logger.info(f"  Secret configured: YES (preview: {secret_preview})")
            logger.info(f"  Secret length: {len(dodo_service.webhook_secret)}")
        else:
            logger.warning(f"  Secret configured: NO")
        
        logger.info("=" * 80)
        logger.info("")
        # ========== END DEBUG ==========
        
        # Check if this is a Svix webhook (Dodo uses Svix/Svix-like headers)
        # Dodo is sending: Webhook-Signature, Webhook-Timestamp, Webhook-Id (Svix format)
        svix_signature = request.headers.get('svix-signature', '') or request.headers.get('Webhook-Signature', '')
        svix_timestamp = request.headers.get('svix-timestamp', '') or request.headers.get('Webhook-Timestamp', '')
        svix_id = request.headers.get('svix-id', '') or request.headers.get('Webhook-Id', '')
        
        logger.info(f"🔍 [Dodo Webhook] svix_signature found: {bool(svix_signature)}")
        if svix_signature:
            logger.info(f"🔍 [Dodo Webhook] svix_signature value: {svix_signature[:100]}...")
        logger.info(f"🔍 [Dodo Webhook] svix_timestamp found: {bool(svix_timestamp)}")
        logger.info(f"🔍 [Dodo Webhook] svix_id found: {bool(svix_id)}")
        
        # Verify webhook signature
        dodo_service = get_dodo_service()
        
        if svix_signature or svix_timestamp or svix_id:
            # Use Svix verification if svix headers are present (or their Dodo aliases)
            # Convert Django HttpRequest headers to dict for Svix library and add aliases
            headers_dict = {k: v for k, v in request.headers.items()}
            # Mirror into canonical Svix keys if missing
            if 'svix-signature' not in headers_dict and svix_signature:
                headers_dict['svix-signature'] = svix_signature
            if 'svix-timestamp' not in headers_dict and svix_timestamp:
                headers_dict['svix-timestamp'] = svix_timestamp
            if 'svix-id' not in headers_dict and svix_id:
                headers_dict['svix-id'] = svix_id
            
            logger.info(f"🔍 [Dodo Webhook] Using Svix verification")
            logger.info(f"🔍 [Dodo Webhook] Headers dict keys: {list(headers_dict.keys())}")
            logger.info(f"🔍 [Dodo Webhook] svix-signature in headers_dict: {'svix-signature' in headers_dict}")
            
            if not dodo_service.verify_webhook_signature_svix(payload, headers_dict):
                logger.warning(f"⚠️ [Dodo Webhook] Invalid Svix signature")
                return HttpResponse('Invalid signature', status=401)
        else:
            # Use legacy HMAC verification for non-Svix webhooks
            signature = request.headers.get('X-Dodo-Signature', '') or request.headers.get('webhook-signature', '')
            logger.info(f"🔍 [Dodo Webhook] Using legacy HMAC verification")
            logger.info(f"🔍 [Dodo Webhook] Signature: {signature[:100] if signature else 'NOT FOUND'}...")
            if not dodo_service.verify_webhook_signature(payload, signature):
                logger.warning(f"⚠️ [Dodo Webhook] Invalid signature")
                return HttpResponse('Invalid signature', status=401)
        
        # Parse event data
        event_data = json.loads(payload.decode('utf-8'))
        event_type = event_data.get('type')
        event_data_obj = event_data.get('data', {})  # Dodo uses 'data', not 'object'
        
        if not event_type:
            logger.error("❌ [Dodo Webhook] Missing event type")
            return HttpResponse('Missing event type', status=400)
        
        logger.info(f"📨 [Dodo Webhook] Received event: {event_type}")
        
        # Check for duplicate events (idempotency)
        webhook_id = request.headers.get('webhook-id', '') or event_data.get('id', '')
        
        # Generate unique ID if not provided (for testing or if Dodo doesn't send one)
        if not webhook_id or webhook_id.strip() == '':
            import uuid
            webhook_id = f"dodo_{uuid.uuid4()}_{int(timezone.now().timestamp())}"
            logger.warning(f"⚠️ [Dodo Webhook] No webhook ID provided, generated: {webhook_id}")
        
        # Check for duplicates
        existing_event = BillingEvent.objects.filter(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id=webhook_id,
            processed=True
        ).first()
        if existing_event:
            logger.info(f"ℹ️ [Dodo Webhook] Duplicate event ignored: {webhook_id}")
            return JsonResponse({'received': True, 'duplicate': True}, status=200)
        
        # Create billing event record
        billing_event = BillingEvent.objects.create(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id=webhook_id,
            event_type=event_type,
            event_data=event_data,
            processed=False
        )
        
        # Handle different event types using new handlers
        try:
            if event_type == 'payment.succeeded':
                handle_payment_succeeded(event_data_obj, billing_event)
            elif event_type == 'subscription.active':
                handle_subscription_active(event_data_obj, billing_event)
            elif event_type == 'subscription.renewed':
                handle_subscription_renewed(event_data_obj, billing_event)
            elif event_type == 'subscription.plan_changed':
                handle_subscription_plan_changed(event_data_obj, billing_event)
            elif event_type == 'subscription.failed':
                handle_subscription_failed(event_data_obj, billing_event)
            elif event_type == 'payment.failed':
                handle_payment_failed(event_data_obj, billing_event)
            elif event_type == 'refund.succeeded':
                handle_refund_succeeded(event_data_obj, billing_event)
            elif event_type == 'refund.failed':
                handle_refund_failed(event_data_obj, billing_event)
            else:
                logger.info(f"ℹ️ [Dodo Webhook] Unhandled event type: {event_type}")
        except Exception as handler_error:
            logger.error(f"❌ [Dodo Webhook] Error in handler for {event_type}: {str(handler_error)}", exc_info=True)
            billing_event.error_message = str(handler_error)
        
        # Mark event as processed
        billing_event.processed = True
        billing_event.processed_at = timezone.now()
        billing_event.save()
        
        return JsonResponse({'received': True}, status=200)
        
    except json.JSONDecodeError:
        logger.error("❌ [Dodo Webhook] Invalid JSON payload")
        return HttpResponse('Invalid JSON', status=400)
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error processing webhook: {str(e)}", exc_info=True)
        if 'billing_event' in locals():
            billing_event.error_message = str(e)
            billing_event.save()
        return HttpResponse('Error processing webhook', status=500)


def _handle_checkout_completed(checkout_data: Dict, billing_event: BillingEvent):
    """Handle checkout.session.completed event"""
    try:
        metadata = checkout_data.get('metadata', {})
        # Get subscription_id from metadata (we passed it when creating checkout)
        subscription_id = metadata.get('subscription_id')
        user_id = metadata.get('user_id')
        
        if not subscription_id:
            logger.warning("⚠️ [Dodo Webhook] No subscription_id in checkout metadata")
            return
        
        subscription = Subscription.objects.get(id=subscription_id)
        subscription.status = Subscription.Status.ACTIVE
        
        # Get Dodo subscription ID from checkout (if available)
        dodo_subscription_id = checkout_data.get('subscription', {}).get('id') or checkout_data.get('subscription_id', '')
        if dodo_subscription_id:
            subscription.provider_subscription_id = dodo_subscription_id
        
        subscription.save()
        
        logger.info(f"✅ [Dodo Webhook] Activated subscription: {subscription_id}")
        
        # Link user if available
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                billing_event.user = user
                billing_event.subscription = subscription
                billing_event.save()
            except User.DoesNotExist:
                pass
                
    except Subscription.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] Subscription not found: {subscription_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling checkout completed: {str(e)}", exc_info=True)


def _handle_payment_succeeded(payment_data: Dict, billing_event: BillingEvent):
    """Handle payment.succeeded event"""
    try:
        # Extract user from metadata or payment data
        user_id = payment_data.get('metadata', {}).get('user_id')
        if not user_id:
            logger.warning("⚠️ [Dodo Webhook] No user_id in payment metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Find associated subscription
        subscription = None
        subscription_id = payment_data.get('metadata', {}).get('subscription_id')
        if subscription_id:
            try:
                subscription = Subscription.objects.get(id=subscription_id)
            except Subscription.DoesNotExist:
                pass
        
        # Create Payment record
        payment = Payment.objects.create(
            user=user,
            subscription=subscription,
            payment_provider=Payment.PaymentProvider.DODO,
            provider_payment_intent_id=payment_data.get('id', ''),
            provider_charge_id=payment_data.get('charge_id', ''),
            amount=payment_data.get('amount', 0) / 100,  # Convert from cents
            currency=payment_data.get('currency', 'usd'),
            payment_type=Payment.PaymentType.SUBSCRIPTION if subscription else Payment.PaymentType.ONE_TIME,
            status=Payment.Status.SUCCEEDED,
            paid_at=timezone.now(),
            metadata=payment_data
        )
        
        logger.info(f"✅ [Dodo Webhook] Created payment record: {payment.id}")
        
        billing_event.user = user
        billing_event.subscription = subscription
        billing_event.save()
        
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling payment succeeded: {str(e)}", exc_info=True)


def _handle_subscription_active(subscription_data: Dict, billing_event: BillingEvent):
    """Handle subscription.active event"""
    try:
        subscription_id = subscription_data.get('id')
        metadata = subscription_data.get('metadata', {})
        user_id = metadata.get('user_id')
        
        if user_id:
            user = User.objects.get(id=user_id)
            subscription = Subscription.objects.filter(
                user=user,
                provider_subscription_id=subscription_id
            ).first()
            
            if subscription:
                subscription.status = Subscription.Status.ACTIVE
                subscription.save()
                logger.info(f"✅ [Dodo Webhook] Subscription activated: {subscription.id}")
                
                billing_event.user = user
                billing_event.subscription = subscription
                billing_event.save()
                
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling subscription active: {str(e)}", exc_info=True)


def _handle_subscription_on_hold(subscription_data: Dict, billing_event: BillingEvent):
    """Handle subscription.on_hold event"""
    try:
        subscription_id = subscription_data.get('id')
        metadata = subscription_data.get('metadata', {})
        user_id = metadata.get('user_id')
        
        if user_id:
            user = User.objects.get(id=user_id)
            subscription = Subscription.objects.filter(
                user=user,
                provider_subscription_id=subscription_id
            ).first()
            
            if subscription:
                subscription.status = Subscription.Status.EXPIRED  # Or create ON_HOLD status
                subscription.save()
                logger.info(f"⚠️ [Dodo Webhook] Subscription on hold: {subscription.id}")
                
                billing_event.user = user
                billing_event.subscription = subscription
                billing_event.save()
                
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling subscription on hold: {str(e)}", exc_info=True)


def _handle_payment_failed(payment_data: Dict, billing_event: BillingEvent):
    """Handle payment.failed event"""
    try:
        user_id = payment_data.get('metadata', {}).get('user_id')
        if not user_id:
            return
        
        user = User.objects.get(id=user_id)
        
        # Create failed payment record
        payment = Payment.objects.create(
            user=user,
            payment_provider=Payment.PaymentProvider.DODO,
            provider_payment_intent_id=payment_data.get('id', ''),
            amount=payment_data.get('amount', 0) / 100,
            currency=payment_data.get('currency', 'usd'),
            status=Payment.Status.FAILED,
            failed_at=timezone.now(),
            failure_reason=payment_data.get('failure_reason', ''),
            failure_code=payment_data.get('failure_code', ''),
            metadata=payment_data
        )
        
        logger.info(f"❌ [Dodo Webhook] Payment failed: {payment.id}")
        
        billing_event.user = user
        billing_event.save()
        
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling payment failed: {str(e)}", exc_info=True)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_success(request):
    """
    Success page after payment completion - checks actual payment status
    """
    checkout_id = request.GET.get('checkout_id')
    subscription_id = request.GET.get('subscription_id')
    
    if not checkout_id and not subscription_id:
        return Response(
            {'error': 'Missing checkout_id or subscription_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get subscription from our DB - use checkout_id as primary method (most reliable)
        subscription = None
        
        # Priority 1: Use checkout_id to get subscription from metadata (most reliable)
        # This works even if webhook hasn't set provider_subscription_id yet
        if checkout_id:
            try:
                dodo_service = get_dodo_service()
                checkout = dodo_service.get_checkout_session(checkout_id)
                checkout_metadata = checkout.get('metadata', {})
                our_subscription_id = checkout_metadata.get('subscription_id')
                if our_subscription_id:
                    try:
                        subscription = Subscription.objects.get(
                            id=our_subscription_id,
                            user=request.user
                        )
                        logger.info(f"✅ [Billing] Found subscription from checkout metadata: {our_subscription_id}")
                        
                        # If Dodo added their subscription_id to redirect, update our record
                        if subscription_id and subscription_id.startswith('sub_'):
                            if not subscription.provider_subscription_id:
                                subscription.provider_subscription_id = subscription_id
                                subscription.save()
                                logger.info(f"✅ [Billing] Updated provider_subscription_id from redirect: {subscription_id}")
                    except Subscription.DoesNotExist:
                        logger.warning(f"⚠️ [Billing] Subscription from checkout metadata not found: {our_subscription_id}")
            except Exception as e:
                logger.error(f"❌ [Billing] Error fetching checkout: {str(e)}")
        
        # Priority 2: If subscription_id is provided and we haven't found subscription yet
        # subscription_id from Dodo redirect is ALWAYS their provider_subscription_id (sub_xxx format)
        if not subscription and subscription_id:
            # Check if it's a UUID (our internal ID) or Dodo's ID
            import uuid
            try:
                # Try to parse as UUID - if successful, it's our internal ID
                uuid.UUID(subscription_id)
                subscription = Subscription.objects.get(id=subscription_id, user=request.user)
                logger.info(f"✅ [Billing] Found subscription by internal UUID: {subscription_id}")
            except (ValueError, TypeError):
                # Not a UUID, so it's Dodo's subscription ID format (e.g., "sub_xxx")
                subscription = Subscription.objects.filter(
                    provider_subscription_id=subscription_id,
                    user=request.user
                ).first()
                if subscription:
                    logger.info(f"✅ [Billing] Found subscription by provider_subscription_id: {subscription_id}")
                else:
                    logger.warning(f"⚠️ [Billing] Subscription not found by provider_subscription_id: {subscription_id}")
        
        # NO FALLBACK - if we can't find it by ID, return error
        if not subscription:
            return Response({
                'success': False,
                'message': 'Subscription not found. Please contact support with your checkout ID.',
                'error': 'SUBSCRIPTION_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check subscription status in our DB (most reliable)
        if subscription:
            if subscription.status == Subscription.Status.ACTIVE:
                return Response({
                    'success': True,
                    'message': 'Payment successful! Your subscription is now active.',
                    'subscription': SubscriptionSerializer(subscription).data
                })
            elif subscription.status == Subscription.Status.PENDING:
                return Response({
                    'success': False,
                    'pending': True,
                    'message': 'Payment is being processed. Please wait a moment and refresh.',
                    'subscription': SubscriptionSerializer(subscription).data
                })
            elif subscription.status == Subscription.Status.FAILED:
                return Response({
                    'success': False,
                    'failed': True,
                    'message': 'Payment failed. Please try again or contact support.',
                    'subscription': SubscriptionSerializer(subscription).data
                })
            else:
                return Response({
                    'success': False,
                    'message': f'Payment was not successful. Status: {subscription.status}',
                    'subscription': SubscriptionSerializer(subscription).data
                })
        else:
            # Fallback: check with Dodo API if we have checkout_id
            if checkout_id:
                try:
                    dodo_service = get_dodo_service()
                    checkout = dodo_service.get_checkout_session(checkout_id)
                    
                    # Check payment status from Dodo
                    payment_status = checkout.get('status', '')
                    if payment_status == 'succeeded':
                        return Response({
                            'success': True,
                            'message': 'Payment successful! Your subscription will be activated shortly.'
                        })
                    else:
                        return Response({
                            'success': False,
                            'message': f'Payment status: {payment_status}. Please check your subscription in settings.'
                        })
                except Exception as e:
                    logger.error(f"❌ [Billing] Error fetching checkout from Dodo: {str(e)}")
            
            return Response({
                'success': False,
                'message': 'Unable to verify payment status. Please check your subscription in settings.'
            })
                
    except Exception as e:
        logger.error(f"❌ [Billing] Error checking payment status: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Unable to verify payment status. Please check your subscription in settings.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_cancel(request):
    """
    Cancel page if user cancels payment
    """
    return Response(
        {
            'message': 'Payment was cancelled. You can try again anytime.'
        },
        status=status.HTTP_200_OK
    )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def upgrade_plan(request):
    """
    Upgrade to a higher plan
    """
    try:
        serializer = SubscriptionCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {'error': 'Invalid input', 'details': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        new_plan_id = serializer.validated_data['plan_id']
        new_plan = Plan.objects.get(id=new_plan_id, is_active=True)
        
        current_subscription = get_user_subscription(request.user)
        
        if not current_subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        current_plan = current_subscription.plan
        
        # Check if it's actually an upgrade
        if new_plan.price <= current_plan.price:
            return Response(
                {'error': 'This is not an upgrade. Use downgrade endpoint or subscribe endpoint.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel current subscription
        current_subscription.status = Subscription.Status.CANCELLED
        current_subscription.end_date = timezone.now()
        current_subscription.save()
        
        # Create new subscription
        new_subscription = Subscription.objects.create(
            user=request.user,
            plan=new_plan,
            status=Subscription.Status.ACTIVE,
            start_date=timezone.now()
        )
        
        subscription_serializer = SubscriptionSerializer(new_subscription)
        
        return Response(
            {
                'message': f'Successfully upgraded to {new_plan.name} plan',
                'subscription': subscription_serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Plan.DoesNotExist:
        return Response(
            {'error': 'Plan not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': f'Failed to upgrade: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel current subscription
    """
    try:
        current_subscription = get_user_subscription(request.user)
        
        if not current_subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Can't cancel free plan (just switch to it)
        if current_subscription.plan.price == 0:
            return Response(
                {'error': 'Free plan cannot be cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel subscription in payment provider for end-of-period cancellation
        if current_subscription.provider_subscription_id and current_subscription.payment_provider == Subscription.PaymentProvider.DODO:
            try:
                dodo_service = get_dodo_service()
                # Cancel in Dodo (they handle end-of-period cancellation)
                dodo_service.cancel_subscription(current_subscription.provider_subscription_id)
                logger.info(f"✅ [Billing] Cancelled Dodo subscription: {current_subscription.provider_subscription_id}")
            except Exception as e:
                logger.error(f"❌ [Billing] Failed to cancel Dodo subscription: {str(e)}", exc_info=True)
                # Continue with local cancellation even if Dodo cancellation fails
        
        # End-of-period cancellation - user keeps access until end_date
        # Don't change end_date if it exists (user paid until then)
        if not current_subscription.end_date:
            # If no end_date, set it to 30 days from start_date
            from billing.utils import calculate_subscription_end_date
            current_subscription.end_date = calculate_subscription_end_date(
                current_subscription.start_date,
                billing_period_days=30
            )
        
        # Mark as canceling (user keeps access until end_date)
        # Clear any scheduled downgrade if user is cancelling instead
        current_subscription.status = Subscription.Status.CANCELING
        current_subscription.downgrade_to_plan = None  # Clear scheduled downgrade
        current_subscription.save()
        
        logger.info(f"📅 [Billing] Subscription set to cancel at period end: {current_subscription.id}, end_date: {current_subscription.end_date}")
        
        # Don't assign free plan immediately - user keeps current plan until end_date
        # Free plan will be assigned when subscription expires (can be done via scheduled task later)
        
        subscription_serializer = SubscriptionSerializer(current_subscription)
        
        return Response(
            {
                'message': 'Subscription cancelled successfully',
                'subscription': subscription_serializer.data
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        logger.error(f"❌ [Billing] Cancel error: {str(e)}", exc_info=True)
        return Response(
            {'error': f'Failed to cancel subscription: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_history(request):
    """
    Get user's subscription history
    """
    try:
        subscriptions = Subscription.objects.filter(
            user=request.user
        ).select_related('plan').order_by('-created_at')
        
        serializer = SubscriptionSerializer(subscriptions, many=True)
        
        return Response(
            {
                'subscriptions': serializer.data,
                'count': len(serializer.data)
            },
            status=status.HTTP_200_OK
        )
        
    except Exception as e:
        return Response(
            {'error': f'Failed to fetch subscription history: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@require_http_methods(["POST"])
def dodo_webhook(request):
    """
    Handle webhooks from Dodo Payments
    
    Events handled:
    - checkout.session.completed: Activate subscription
    - payment.succeeded: Create Payment record
    - subscription.active: Update subscription status
    - subscription.on_hold: Handle failed payment
    - payment.failed: Handle payment failure
    """
    try:
        # Get raw payload for signature verification
        payload = request.body
        
        # ========== DEBUG: Log all webhook data ==========
        logger.info("=" * 80)
        logger.info("🔍 [DODO WEBHOOK DEBUG] Full Webhook Data")
        logger.info("=" * 80)
        
        # Log all headers
        logger.info("\n📋 ALL HEADERS:")
        logger.info("-" * 80)
        for key, value in request.headers.items():
            logger.info(f"  {key}: {value}")
        
        # Log META headers (Django's raw headers)
        logger.info("\n📋 META HEADERS (HTTP_*):")
        logger.info("-" * 80)
        for key, value in request.META.items():
            if key.startswith('HTTP_'):
                logger.info(f"  {key}: {value}")
        
        # Log specific signature headers
        logger.info("\n🔐 SIGNATURE HEADERS:")
        logger.info("-" * 80)
        logger.info(f"  svix-signature: {request.headers.get('svix-signature', 'NOT FOUND')}")
        logger.info(f"  X-Dodo-Signature: {request.headers.get('X-Dodo-Signature', 'NOT FOUND')}")
        logger.info(f"  webhook-signature: {request.headers.get('webhook-signature', 'NOT FOUND')}")
        logger.info(f"  svix-id: {request.headers.get('svix-id', 'NOT FOUND')}")
        logger.info(f"  svix-timestamp: {request.headers.get('svix-timestamp', 'NOT FOUND')}")
        
        # Log payload info
        logger.info("\n📦 PAYLOAD INFO:")
        logger.info("-" * 80)
        logger.info(f"  Payload length: {len(payload)} bytes")
        logger.info(f"  Payload type: {type(payload)}")
        try:
            payload_str = payload.decode('utf-8')
            logger.info(f"  Payload preview (first 500 chars): {payload_str[:500]}")
            logger.info(f"  Full payload: {payload_str}")
        except Exception as e:
            logger.error(f"  Error decoding payload: {e}")
        
        # Log webhook secret status
        logger.info("\n🔑 WEBHOOK SECRET:")
        logger.info("-" * 80)
        dodo_service = get_dodo_service()
        if dodo_service.webhook_secret:
            secret_preview = dodo_service.webhook_secret[:10] + "..." if len(dodo_service.webhook_secret) > 10 else dodo_service.webhook_secret
            logger.info(f"  Secret configured: YES (preview: {secret_preview})")
            logger.info(f"  Secret length: {len(dodo_service.webhook_secret)}")
        else:
            logger.warning(f"  Secret configured: NO")
        
        logger.info("=" * 80)
        logger.info("")
        # ========== END DEBUG ==========
        
        # Check if this is a Svix webhook (Dodo uses Svix/Svix-like headers)
        # Dodo is sending: Webhook-Signature, Webhook-Timestamp, Webhook-Id (Svix format)
        svix_signature = request.headers.get('svix-signature', '') or request.headers.get('Webhook-Signature', '')
        svix_timestamp = request.headers.get('svix-timestamp', '') or request.headers.get('Webhook-Timestamp', '')
        svix_id = request.headers.get('svix-id', '') or request.headers.get('Webhook-Id', '')
        
        logger.info(f"🔍 [Dodo Webhook] svix_signature found: {bool(svix_signature)}")
        if svix_signature:
            logger.info(f"🔍 [Dodo Webhook] svix_signature value: {svix_signature[:100]}...")
        logger.info(f"🔍 [Dodo Webhook] svix_timestamp found: {bool(svix_timestamp)}")
        logger.info(f"🔍 [Dodo Webhook] svix_id found: {bool(svix_id)}")
        
        # Verify webhook signature
        dodo_service = get_dodo_service()
        
        if svix_signature or svix_timestamp or svix_id:
            # Use Svix verification if svix headers are present (or their Dodo aliases)
            # Convert Django HttpRequest headers to dict for Svix library and add aliases
            headers_dict = {k: v for k, v in request.headers.items()}
            # Mirror into canonical Svix keys if missing
            if 'svix-signature' not in headers_dict and svix_signature:
                headers_dict['svix-signature'] = svix_signature
            if 'svix-timestamp' not in headers_dict and svix_timestamp:
                headers_dict['svix-timestamp'] = svix_timestamp
            if 'svix-id' not in headers_dict and svix_id:
                headers_dict['svix-id'] = svix_id
            
            logger.info(f"🔍 [Dodo Webhook] Using Svix verification")
            logger.info(f"🔍 [Dodo Webhook] Headers dict keys: {list(headers_dict.keys())}")
            logger.info(f"🔍 [Dodo Webhook] svix-signature in headers_dict: {'svix-signature' in headers_dict}")
            
            if not dodo_service.verify_webhook_signature_svix(payload, headers_dict):
                logger.warning(f"⚠️ [Dodo Webhook] Invalid Svix signature")
                return HttpResponse('Invalid signature', status=401)
        else:
            # Use legacy HMAC verification for non-Svix webhooks
            signature = request.headers.get('X-Dodo-Signature', '') or request.headers.get('webhook-signature', '')
            logger.info(f"🔍 [Dodo Webhook] Using legacy HMAC verification")
            logger.info(f"🔍 [Dodo Webhook] Signature: {signature[:100] if signature else 'NOT FOUND'}...")
            if not dodo_service.verify_webhook_signature(payload, signature):
                logger.warning(f"⚠️ [Dodo Webhook] Invalid signature")
                return HttpResponse('Invalid signature', status=401)
        
        # Parse event data
        event_data = json.loads(payload.decode('utf-8'))
        event_type = event_data.get('type')
        event_data_obj = event_data.get('data', {})  # Dodo uses 'data', not 'object'
        
        if not event_type:
            logger.error("❌ [Dodo Webhook] Missing event type")
            return HttpResponse('Missing event type', status=400)
        
        logger.info(f"📨 [Dodo Webhook] Received event: {event_type}")
        
        # Check for duplicate events (idempotency)
        webhook_id = request.headers.get('webhook-id', '') or event_data.get('id', '')
        
        # Generate unique ID if not provided (for testing or if Dodo doesn't send one)
        if not webhook_id or webhook_id.strip() == '':
            import uuid
            webhook_id = f"dodo_{uuid.uuid4()}_{int(timezone.now().timestamp())}"
            logger.warning(f"⚠️ [Dodo Webhook] No webhook ID provided, generated: {webhook_id}")
        
        # Check for duplicates
        existing_event = BillingEvent.objects.filter(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id=webhook_id,
            processed=True
        ).first()
        if existing_event:
            logger.info(f"ℹ️ [Dodo Webhook] Duplicate event ignored: {webhook_id}")
            return JsonResponse({'received': True, 'duplicate': True}, status=200)
        
        # Create billing event record
        billing_event = BillingEvent.objects.create(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id=webhook_id,
            event_type=event_type,
            event_data=event_data,
            processed=False
        )
        
        # Handle different event types using new handlers
        try:
            if event_type == 'payment.succeeded':
                handle_payment_succeeded(event_data_obj, billing_event)
            elif event_type == 'subscription.active':
                handle_subscription_active(event_data_obj, billing_event)
            elif event_type == 'subscription.renewed':
                handle_subscription_renewed(event_data_obj, billing_event)
            elif event_type == 'subscription.plan_changed':
                handle_subscription_plan_changed(event_data_obj, billing_event)
            elif event_type == 'subscription.failed':
                handle_subscription_failed(event_data_obj, billing_event)
            elif event_type == 'payment.failed':
                handle_payment_failed(event_data_obj, billing_event)
            elif event_type == 'refund.succeeded':
                handle_refund_succeeded(event_data_obj, billing_event)
            elif event_type == 'refund.failed':
                handle_refund_failed(event_data_obj, billing_event)
            else:
                logger.info(f"ℹ️ [Dodo Webhook] Unhandled event type: {event_type}")
        except Exception as handler_error:
            logger.error(f"❌ [Dodo Webhook] Error in handler for {event_type}: {str(handler_error)}", exc_info=True)
            billing_event.error_message = str(handler_error)
        
        # Mark event as processed
        billing_event.processed = True
        billing_event.processed_at = timezone.now()
        billing_event.save()
        
        return JsonResponse({'received': True}, status=200)
        
    except json.JSONDecodeError:
        logger.error("❌ [Dodo Webhook] Invalid JSON payload")
        return HttpResponse('Invalid JSON', status=400)
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error processing webhook: {str(e)}", exc_info=True)
        if 'billing_event' in locals():
            billing_event.error_message = str(e)
            billing_event.save()
        return HttpResponse('Error processing webhook', status=500)


def _handle_checkout_completed(checkout_data: Dict, billing_event: BillingEvent):
    """Handle checkout.session.completed event"""
    try:
        metadata = checkout_data.get('metadata', {})
        # Get subscription_id from metadata (we passed it when creating checkout)
        subscription_id = metadata.get('subscription_id')
        user_id = metadata.get('user_id')
        
        if not subscription_id:
            logger.warning("⚠️ [Dodo Webhook] No subscription_id in checkout metadata")
            return
        
        subscription = Subscription.objects.get(id=subscription_id)
        subscription.status = Subscription.Status.ACTIVE
        
        # Get Dodo subscription ID from checkout (if available)
        dodo_subscription_id = checkout_data.get('subscription', {}).get('id') or checkout_data.get('subscription_id', '')
        if dodo_subscription_id:
            subscription.provider_subscription_id = dodo_subscription_id
        
        subscription.save()
        
        logger.info(f"✅ [Dodo Webhook] Activated subscription: {subscription_id}")
        
        # Link user if available
        if user_id:
            try:
                user = User.objects.get(id=user_id)
                billing_event.user = user
                billing_event.subscription = subscription
                billing_event.save()
            except User.DoesNotExist:
                pass
                
    except Subscription.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] Subscription not found: {subscription_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling checkout completed: {str(e)}", exc_info=True)


def _handle_payment_succeeded(payment_data: Dict, billing_event: BillingEvent):
    """Handle payment.succeeded event"""
    try:
        # Extract user from metadata or payment data
        user_id = payment_data.get('metadata', {}).get('user_id')
        if not user_id:
            logger.warning("⚠️ [Dodo Webhook] No user_id in payment metadata")
            return
        
        user = User.objects.get(id=user_id)
        
        # Find associated subscription
        subscription = None
        subscription_id = payment_data.get('metadata', {}).get('subscription_id')
        if subscription_id:
            try:
                subscription = Subscription.objects.get(id=subscription_id)
            except Subscription.DoesNotExist:
                pass
        
        # Create Payment record
        payment = Payment.objects.create(
            user=user,
            subscription=subscription,
            payment_provider=Payment.PaymentProvider.DODO,
            provider_payment_intent_id=payment_data.get('id', ''),
            provider_charge_id=payment_data.get('charge_id', ''),
            amount=payment_data.get('amount', 0) / 100,  # Convert from cents
            currency=payment_data.get('currency', 'usd'),
            payment_type=Payment.PaymentType.SUBSCRIPTION if subscription else Payment.PaymentType.ONE_TIME,
            status=Payment.Status.SUCCEEDED,
            paid_at=timezone.now(),
            metadata=payment_data
        )
        
        logger.info(f"✅ [Dodo Webhook] Created payment record: {payment.id}")
        
        billing_event.user = user
        billing_event.subscription = subscription
        billing_event.save()
        
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling payment succeeded: {str(e)}", exc_info=True)


def _handle_subscription_active(subscription_data: Dict, billing_event: BillingEvent):
    """Handle subscription.active event"""
    try:
        subscription_id = subscription_data.get('id')
        metadata = subscription_data.get('metadata', {})
        user_id = metadata.get('user_id')
        
        if user_id:
            user = User.objects.get(id=user_id)
            subscription = Subscription.objects.filter(
                user=user,
                provider_subscription_id=subscription_id
            ).first()
            
            if subscription:
                subscription.status = Subscription.Status.ACTIVE
                subscription.save()
                logger.info(f"✅ [Dodo Webhook] Subscription activated: {subscription.id}")
                
                billing_event.user = user
                billing_event.subscription = subscription
                billing_event.save()
                
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling subscription active: {str(e)}", exc_info=True)


def _handle_subscription_on_hold(subscription_data: Dict, billing_event: BillingEvent):
    """Handle subscription.on_hold event"""
    try:
        subscription_id = subscription_data.get('id')
        metadata = subscription_data.get('metadata', {})
        user_id = metadata.get('user_id')
        
        if user_id:
            user = User.objects.get(id=user_id)
            subscription = Subscription.objects.filter(
                user=user,
                provider_subscription_id=subscription_id
            ).first()
            
            if subscription:
                subscription.status = Subscription.Status.EXPIRED  # Or create ON_HOLD status
                subscription.save()
                logger.info(f"⚠️ [Dodo Webhook] Subscription on hold: {subscription.id}")
                
                billing_event.user = user
                billing_event.subscription = subscription
                billing_event.save()
                
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling subscription on hold: {str(e)}", exc_info=True)


def _handle_payment_failed(payment_data: Dict, billing_event: BillingEvent):
    """Handle payment.failed event"""
    try:
        user_id = payment_data.get('metadata', {}).get('user_id')
        if not user_id:
            return
        
        user = User.objects.get(id=user_id)
        
        # Create failed payment record
        payment = Payment.objects.create(
            user=user,
            payment_provider=Payment.PaymentProvider.DODO,
            provider_payment_intent_id=payment_data.get('id', ''),
            amount=payment_data.get('amount', 0) / 100,
            currency=payment_data.get('currency', 'usd'),
            status=Payment.Status.FAILED,
            failed_at=timezone.now(),
            failure_reason=payment_data.get('failure_reason', ''),
            failure_code=payment_data.get('failure_code', ''),
            metadata=payment_data
        )
        
        logger.info(f"❌ [Dodo Webhook] Payment failed: {payment.id}")
        
        billing_event.user = user
        billing_event.save()
        
    except User.DoesNotExist:
        logger.error(f"❌ [Dodo Webhook] User not found: {user_id}")
    except Exception as e:
        logger.error(f"❌ [Dodo Webhook] Error handling payment failed: {str(e)}", exc_info=True)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_success(request):
    """
    Success page after payment completion - checks actual payment status
    """
    checkout_id = request.GET.get('checkout_id')
    subscription_id = request.GET.get('subscription_id')
    
    if not checkout_id and not subscription_id:
        return Response(
            {'error': 'Missing checkout_id or subscription_id'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        # Get subscription from our DB - use checkout_id as primary method (most reliable)
        subscription = None
        
        # Priority 1: Use checkout_id to get subscription from metadata (most reliable)
        # This works even if webhook hasn't set provider_subscription_id yet
        if checkout_id:
            try:
                dodo_service = get_dodo_service()
                checkout = dodo_service.get_checkout_session(checkout_id)
                checkout_metadata = checkout.get('metadata', {})
                our_subscription_id = checkout_metadata.get('subscription_id')
                if our_subscription_id:
                    try:
                        subscription = Subscription.objects.get(
                            id=our_subscription_id,
                            user=request.user
                        )
                        logger.info(f"✅ [Billing] Found subscription from checkout metadata: {our_subscription_id}")
                        
                        # If Dodo added their subscription_id to redirect, update our record
                        if subscription_id and subscription_id.startswith('sub_'):
                            if not subscription.provider_subscription_id:
                                subscription.provider_subscription_id = subscription_id
                                subscription.save()
                                logger.info(f"✅ [Billing] Updated provider_subscription_id from redirect: {subscription_id}")
                    except Subscription.DoesNotExist:
                        logger.warning(f"⚠️ [Billing] Subscription from checkout metadata not found: {our_subscription_id}")
            except Exception as e:
                logger.error(f"❌ [Billing] Error fetching checkout: {str(e)}")
        
        # Priority 2: If subscription_id is provided and we haven't found subscription yet
        # subscription_id from Dodo redirect is ALWAYS their provider_subscription_id (sub_xxx format)
        if not subscription and subscription_id:
            # Check if it's a UUID (our internal ID) or Dodo's ID
            import uuid
            try:
                # Try to parse as UUID - if successful, it's our internal ID
                uuid.UUID(subscription_id)
                subscription = Subscription.objects.get(id=subscription_id, user=request.user)
                logger.info(f"✅ [Billing] Found subscription by internal UUID: {subscription_id}")
            except (ValueError, TypeError):
                # Not a UUID, so it's Dodo's subscription ID format (e.g., "sub_xxx")
                subscription = Subscription.objects.filter(
                    provider_subscription_id=subscription_id,
                    user=request.user
                ).first()
                if subscription:
                    logger.info(f"✅ [Billing] Found subscription by provider_subscription_id: {subscription_id}")
                else:
                    logger.warning(f"⚠️ [Billing] Subscription not found by provider_subscription_id: {subscription_id}")
        
        # NO FALLBACK - if we can't find it by ID, return error
        if not subscription:
            return Response({
                'success': False,
                'message': 'Subscription not found. Please contact support with your checkout ID.',
                'error': 'SUBSCRIPTION_NOT_FOUND'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Check subscription status in our DB (most reliable)
        if subscription:
            if subscription.status == Subscription.Status.ACTIVE:
                return Response({
                    'success': True,
                    'message': 'Payment successful! Your subscription is now active.',
                    'subscription': SubscriptionSerializer(subscription).data
                })
            elif subscription.status == Subscription.Status.PENDING:
                return Response({
                    'success': False,
                    'pending': True,
                    'message': 'Payment is being processed. Please wait a moment and refresh.',
                    'subscription': SubscriptionSerializer(subscription).data
                })
            elif subscription.status == Subscription.Status.FAILED:
                return Response({
                    'success': False,
                    'failed': True,
                    'message': 'Payment failed. Please try again or contact support.',
                    'subscription': SubscriptionSerializer(subscription).data
                })
            else:
                return Response({
                    'success': False,
                    'message': f'Payment was not successful. Status: {subscription.status}',
                    'subscription': SubscriptionSerializer(subscription).data
                })
        else:
            # Fallback: check with Dodo API if we have checkout_id
            if checkout_id:
                try:
                    dodo_service = get_dodo_service()
                    checkout = dodo_service.get_checkout_session(checkout_id)
                    
                    # Check payment status from Dodo
                    payment_status = checkout.get('status', '')
                    if payment_status == 'succeeded':
                        return Response({
                            'success': True,
                            'message': 'Payment successful! Your subscription will be activated shortly.'
                        })
                    else:
                        return Response({
                            'success': False,
                            'message': f'Payment status: {payment_status}. Please check your subscription in settings.'
                        })
                except Exception as e:
                    logger.error(f"❌ [Billing] Error fetching checkout from Dodo: {str(e)}")
            
            return Response({
                'success': False,
                'message': 'Unable to verify payment status. Please check your subscription in settings.'
            })
                
    except Exception as e:
        logger.error(f"❌ [Billing] Error checking payment status: {str(e)}", exc_info=True)
        return Response(
            {'error': 'Unable to verify payment status. Please check your subscription in settings.'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def subscription_cancel(request):
    """
    Cancel page if user cancels payment
    """
    return Response(
        {
            'message': 'Payment was cancelled. You can try again anytime.'
        },
        status=status.HTTP_200_OK
    )
