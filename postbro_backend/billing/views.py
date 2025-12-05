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
        
        if current_subscription:
            # User already has subscription
            if current_subscription.plan.id == plan.id:
                return Response(
                    {'error': 'You are already subscribed to this plan'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cancel current subscription
            current_subscription.status = Subscription.Status.CANCELLED
            current_subscription.end_date = timezone.now()
            current_subscription.save()
        
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
                # Get or create Dodo customer
                dodo_service = get_dodo_service()
                customer = dodo_service.get_or_create_customer(
                    email=request.user.email,
                    name=request.user.get_full_name() or request.user.email,
                    metadata={
                        'user_id': str(request.user.id),
                        'clerk_user_id': request.user.clerk_user_id or '',
                    }
                )
                
                # Create pending subscription
                new_subscription = Subscription.objects.create(
                    user=request.user,
                    plan=plan,
                    status=Subscription.Status.TRIAL,  # Will be activated after payment
                    start_date=timezone.now(),
                    payment_provider=Subscription.PaymentProvider.DODO,
                    provider_customer_id=customer.get('id', '')
                )
                
                # Build return URL (frontend success page)
                # Dodo will redirect here after payment
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
                return_url = f"{frontend_url}/billing/success"
                
                # Create checkout session
                checkout_session = dodo_service.create_checkout_session(
                    product_id=plan.provider_product_id,
                    customer_id=customer.get('id'),
                    return_url=return_url,
                    metadata={
                        'subscription_id': str(new_subscription.id),
                        'user_id': str(request.user.id),
                        'plan_id': str(plan.id),
                        'plan_name': plan.name,
                    }
                )
                
                logger.info(f"✅ [Billing] Created Dodo checkout session {checkout_session.get('id')} for subscription {new_subscription.id}")
                
                return Response(
                    {
                        'message': 'Checkout session created',
                        'checkout_url': checkout_session.get('checkout_url'),
                        'checkout_id': checkout_session.get('id'),
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
        
        # Cancel subscription in payment provider if it exists
        if current_subscription.provider_subscription_id and current_subscription.payment_provider == Subscription.PaymentProvider.DODO:
            try:
                dodo_service = get_dodo_service()
                dodo_service.cancel_subscription(current_subscription.provider_subscription_id)
                logger.info(f"✅ [Billing] Cancelled Dodo subscription: {current_subscription.provider_subscription_id}")
            except Exception as e:
                logger.error(f"❌ [Billing] Failed to cancel Dodo subscription: {str(e)}", exc_info=True)
                # Continue with local cancellation even if Dodo cancellation fails
        
        # Cancel subscription locally
        current_subscription.status = Subscription.Status.CANCELLED
        current_subscription.end_date = timezone.now()
        current_subscription.save()
        
        # Assign free plan
        try:
            free_plan = Plan.objects.get(name='Free', is_active=True)
            free_subscription = Subscription.objects.create(
                user=request.user,
                plan=free_plan,
                status=Subscription.Status.ACTIVE,
                start_date=timezone.now()
            )
        except Plan.DoesNotExist:
            pass
        
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
        signature = request.headers.get('X-Dodo-Signature', '')
        
        # Verify webhook signature
        dodo_service = get_dodo_service()
        if not dodo_service.verify_webhook_signature(payload, signature):
            logger.warning(f"⚠️ [Dodo Webhook] Invalid signature")
            return HttpResponse('Invalid signature', status=401)
        
        # Parse event data
        event_data = json.loads(payload.decode('utf-8'))
        event_type = event_data.get('type')
        event_object = event_data.get('object', {})
        
        logger.info(f"📨 [Dodo Webhook] Received event: {event_type}")
        
        # Create billing event record
        billing_event = BillingEvent.objects.create(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id=event_data.get('id', ''),
            event_type=event_type,
            event_data=event_data,
            processed=False
        )
        
        # Handle different event types
        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(event_object, billing_event)
        elif event_type == 'payment.succeeded':
            _handle_payment_succeeded(event_object, billing_event)
        elif event_type == 'subscription.active':
            _handle_subscription_active(event_object, billing_event)
        elif event_type == 'subscription.on_hold':
            _handle_subscription_on_hold(event_object, billing_event)
        elif event_type == 'payment.failed':
            _handle_payment_failed(event_object, billing_event)
        else:
            logger.info(f"ℹ️ [Dodo Webhook] Unhandled event type: {event_type}")
        
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
    Success page after payment completion
    """
    checkout_id = request.GET.get('checkout_id')
    
    if checkout_id:
        try:
            dodo_service = get_dodo_service()
            checkout = dodo_service.get_checkout_session(checkout_id)
            logger.info(f"✅ [Billing] Checkout success: {checkout_id}")
        except Exception as e:
            logger.error(f"❌ [Billing] Error fetching checkout: {str(e)}")
    
    return Response(
        {
            'message': 'Payment successful! Your subscription is now active.',
            'checkout_id': checkout_id
        },
        status=status.HTTP_200_OK
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
        
        if current_subscription:
            # User already has subscription
            if current_subscription.plan.id == plan.id:
                return Response(
                    {'error': 'You are already subscribed to this plan'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cancel current subscription
            current_subscription.status = Subscription.Status.CANCELLED
            current_subscription.end_date = timezone.now()
            current_subscription.save()
        
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
                # Get or create Dodo customer
                dodo_service = get_dodo_service()
                customer = dodo_service.get_or_create_customer(
                    email=request.user.email,
                    name=request.user.get_full_name() or request.user.email,
                    metadata={
                        'user_id': str(request.user.id),
                        'clerk_user_id': request.user.clerk_user_id or '',
                    }
                )
                
                # Create pending subscription
                new_subscription = Subscription.objects.create(
                    user=request.user,
                    plan=plan,
                    status=Subscription.Status.TRIAL,  # Will be activated after payment
                    start_date=timezone.now(),
                    payment_provider=Subscription.PaymentProvider.DODO,
                    provider_customer_id=customer.get('id', '')
                )
                
                # Build return URL (frontend success page)
                # Dodo will redirect here after payment
                frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:3000')
                return_url = f"{frontend_url}/billing/success"
                
                # Create checkout session
                checkout_session = dodo_service.create_checkout_session(
                    product_id=plan.provider_product_id,
                    customer_id=customer.get('id'),
                    return_url=return_url,
                    metadata={
                        'subscription_id': str(new_subscription.id),
                        'user_id': str(request.user.id),
                        'plan_id': str(plan.id),
                        'plan_name': plan.name,
                    }
                )
                
                logger.info(f"✅ [Billing] Created Dodo checkout session {checkout_session.get('id')} for subscription {new_subscription.id}")
                
                return Response(
                    {
                        'message': 'Checkout session created',
                        'checkout_url': checkout_session.get('checkout_url'),
                        'checkout_id': checkout_session.get('id'),
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
        
        # Cancel subscription in payment provider if it exists
        if current_subscription.provider_subscription_id and current_subscription.payment_provider == Subscription.PaymentProvider.DODO:
            try:
                dodo_service = get_dodo_service()
                dodo_service.cancel_subscription(current_subscription.provider_subscription_id)
                logger.info(f"✅ [Billing] Cancelled Dodo subscription: {current_subscription.provider_subscription_id}")
            except Exception as e:
                logger.error(f"❌ [Billing] Failed to cancel Dodo subscription: {str(e)}", exc_info=True)
                # Continue with local cancellation even if Dodo cancellation fails
        
        # Cancel subscription locally
        current_subscription.status = Subscription.Status.CANCELLED
        current_subscription.end_date = timezone.now()
        current_subscription.save()
        
        # Assign free plan
        try:
            free_plan = Plan.objects.get(name='Free', is_active=True)
            free_subscription = Subscription.objects.create(
                user=request.user,
                plan=free_plan,
                status=Subscription.Status.ACTIVE,
                start_date=timezone.now()
            )
        except Plan.DoesNotExist:
            pass
        
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
        signature = request.headers.get('X-Dodo-Signature', '')
        
        # Verify webhook signature
        dodo_service = get_dodo_service()
        if not dodo_service.verify_webhook_signature(payload, signature):
            logger.warning(f"⚠️ [Dodo Webhook] Invalid signature")
            return HttpResponse('Invalid signature', status=401)
        
        # Parse event data
        event_data = json.loads(payload.decode('utf-8'))
        event_type = event_data.get('type')
        event_object = event_data.get('object', {})
        
        logger.info(f"📨 [Dodo Webhook] Received event: {event_type}")
        
        # Create billing event record
        billing_event = BillingEvent.objects.create(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id=event_data.get('id', ''),
            event_type=event_type,
            event_data=event_data,
            processed=False
        )
        
        # Handle different event types
        if event_type == 'checkout.session.completed':
            _handle_checkout_completed(event_object, billing_event)
        elif event_type == 'payment.succeeded':
            _handle_payment_succeeded(event_object, billing_event)
        elif event_type == 'subscription.active':
            _handle_subscription_active(event_object, billing_event)
        elif event_type == 'subscription.on_hold':
            _handle_subscription_on_hold(event_object, billing_event)
        elif event_type == 'payment.failed':
            _handle_payment_failed(event_object, billing_event)
        else:
            logger.info(f"ℹ️ [Dodo Webhook] Unhandled event type: {event_type}")
        
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
    Success page after payment completion
    """
    checkout_id = request.GET.get('checkout_id')
    
    if checkout_id:
        try:
            dodo_service = get_dodo_service()
            checkout = dodo_service.get_checkout_session(checkout_id)
            logger.info(f"✅ [Billing] Checkout success: {checkout_id}")
        except Exception as e:
            logger.error(f"❌ [Billing] Error fetching checkout: {str(e)}")
    
    return Response(
        {
            'message': 'Payment successful! Your subscription is now active.',
            'checkout_id': checkout_id
        },
        status=status.HTTP_200_OK
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
