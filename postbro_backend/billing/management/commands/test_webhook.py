"""
Django management command to test webhook handlers locally

Usage:
    python manage.py test_webhook payment.succeeded --subscription-id=UUID --user-id=UUID
    python manage.py test_webhook payment.failed --subscription-id=UUID --user-id=UUID
    python manage.py test_webhook subscription.active --subscription-id=UUID --user-id=UUID
    python manage.py test_webhook subscription.failed --subscription-id=UUID --user-id=UUID
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from billing.webhook_handlers import (
    handle_payment_succeeded,
    handle_subscription_active,
    handle_subscription_renewed,
    handle_subscription_failed,
    handle_payment_failed
)
from billing.models import BillingEvent
from accounts.models import Subscription, User
import uuid


class Command(BaseCommand):
    help = 'Test webhook handlers locally with sample Dodo webhook data'

    def add_arguments(self, parser):
        parser.add_argument(
            'event_type',
            type=str,
            choices=['payment.succeeded', 'payment.failed', 'subscription.active', 'subscription.renewed', 'subscription.failed'],
            help='Type of webhook event to test'
        )
        parser.add_argument(
            '--subscription-id',
            type=str,
            required=True,
            help='UUID of the subscription to test with'
        )
        parser.add_argument(
            '--user-id',
            type=str,
            required=True,
            help='UUID of the user to test with'
        )
        parser.add_argument(
            '--dodo-subscription-id',
            type=str,
            default='sub_test123',
            help='Dodo subscription ID (default: sub_test123)'
        )
        parser.add_argument(
            '--payment-id',
            type=str,
            default='pay_test123',
            help='Dodo payment ID (default: pay_test123)'
        )

    def handle(self, *args, **options):
        event_type = options['event_type']
        subscription_id = options['subscription_id']
        user_id = options['user_id']
        dodo_subscription_id = options['dodo_subscription_id']
        payment_id = options['payment_id']

        # Validate UUIDs
        try:
            subscription_uuid = uuid.UUID(subscription_id)
            user_uuid = uuid.UUID(user_id)
        except ValueError:
            self.stdout.write(self.style.ERROR('Invalid UUID format for subscription-id or user-id'))
            return

        # Verify subscription and user exist
        try:
            subscription = Subscription.objects.get(id=subscription_uuid)
            user = User.objects.get(id=user_uuid)
        except Subscription.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Subscription not found: {subscription_id}'))
            return
        except User.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'User not found: {user_id}'))
            return

        self.stdout.write(self.style.SUCCESS(f'\n🧪 Testing webhook: {event_type}'))
        self.stdout.write(f'   Subscription: {subscription.plan.name} ({subscription.status})')
        self.stdout.write(f'   User: {user.email}\n')

        # Create billing event
        billing_event = BillingEvent.objects.create(
            payment_provider=BillingEvent.PaymentProvider.DODO,
            provider_event_id=f'test_event_{timezone.now().timestamp()}',
            event_type=event_type,
            event_data={'type': event_type, 'data': {}},
            processed=False
        )

        # Create event data based on type
        if event_type == 'payment.succeeded':
            event_data = {
                'payment_id': payment_id,
                'subscription_id': dodo_subscription_id,
                'status': 'succeeded',
                'total_amount': 5900,  # $59.00 in cents
                'settlement_amount': 6195,  # With tax
                'currency': 'USD',
                'metadata': {
                    'subscription_id': str(subscription.id),
                    'user_id': str(user.id),
                    'plan_id': str(subscription.plan.id),
                    'plan_name': subscription.plan.name
                }
            }
            handle_payment_succeeded(event_data, billing_event)

        elif event_type == 'payment.failed':
            event_data = {
                'payment_id': payment_id,
                'subscription_id': dodo_subscription_id,
                'status': 'failed',
                'total_amount': 5900,
                'currency': 'USD',
                'error_code': 'INSUFFICIENT_FUNDS',
                'error_message': 'Your card was declined.',
                'metadata': {
                    'subscription_id': str(subscription.id),
                    'user_id': str(user.id),
                    'plan_id': str(subscription.plan.id),
                    'plan_name': subscription.plan.name
                }
            }
            handle_payment_failed(event_data, billing_event)

        elif event_type == 'subscription.active':
            event_data = {
                'subscription_id': dodo_subscription_id,
                'status': 'active',
                'metadata': {
                    'subscription_id': str(subscription.id),
                    'user_id': str(user.id),
                    'plan_id': str(subscription.plan.id),
                    'plan_name': subscription.plan.name
                }
            }
            handle_subscription_active(event_data, billing_event)

        elif event_type == 'subscription.renewed':
            event_data = {
                'subscription_id': dodo_subscription_id,
                'status': 'active',
                'metadata': {
                    'subscription_id': str(subscription.id),
                    'user_id': str(user.id),
                    'plan_id': str(subscription.plan.id),
                    'plan_name': subscription.plan.name
                }
            }
            handle_subscription_renewed(event_data, billing_event)

        elif event_type == 'subscription.failed':
            event_data = {
                'subscription_id': dodo_subscription_id,
                'status': 'failed',
                'metadata': {
                    'subscription_id': str(subscription.id),
                    'user_id': str(user.id),
                    'plan_id': str(subscription.plan.id),
                    'plan_name': subscription.plan.name
                }
            }
            handle_subscription_failed(event_data, billing_event)

        # Refresh subscription to see changes
        subscription.refresh_from_db()
        billing_event.refresh_from_db()

        # Display results
        self.stdout.write(self.style.SUCCESS('\n✅ Webhook test completed!\n'))
        self.stdout.write(f'Subscription Status: {subscription.status}')
        self.stdout.write(f'Billing Event Processed: {billing_event.processed}')
        if billing_event.error_message:
            self.stdout.write(self.style.WARNING(f'Error: {billing_event.error_message}'))
        
        if subscription.status == 'active' and event_type in ['payment.succeeded', 'subscription.active']:
            self.stdout.write(self.style.SUCCESS('✅ Subscription activated successfully!'))
        elif subscription.status == 'cancelled' and event_type in ['payment.failed', 'subscription.failed']:
            self.stdout.write(self.style.SUCCESS('✅ Subscription cancelled as expected!'))

