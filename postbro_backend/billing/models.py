import uuid
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from accounts.models import User, Subscription


class PaymentMethod(models.Model):
    """
    Store customer payment methods (cards, etc.) from payment providers
    """
    class PaymentProvider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        DODO = 'dodo', _('Dodo Payments')
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payment_methods')
    payment_provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.DODO,
        help_text='Payment provider (stripe, dodo, etc.)'
    )
    provider_payment_method_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Payment provider PaymentMethod ID (e.g., Stripe pm_xxx or Dodo pm_xxx)'
    )
    type = models.CharField(max_length=50, help_text='card, bank_account, etc.')
    is_default = models.BooleanField(default=False, help_text='Default payment method for user')
    
    # Card details (if type is card)
    card_brand = models.CharField(max_length=50, blank=True, help_text='visa, mastercard, etc.')
    card_last4 = models.CharField(max_length=4, blank=True)
    card_exp_month = models.IntegerField(null=True, blank=True)
    card_exp_year = models.IntegerField(null=True, blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional payment provider data')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True, help_text='Soft delete when removed from payment provider')

    class Meta:
        ordering = ['-is_default', '-created_at']
        indexes = [
            models.Index(fields=['user', 'is_default']),
            models.Index(fields=['provider_payment_method_id']),
            models.Index(fields=['payment_provider', 'provider_payment_method_id']),
        ]

    def __str__(self):
        if self.card_last4:
            return f"{self.user.email} - {self.card_brand} ****{self.card_last4} ({self.payment_provider})"
        return f"{self.user.email} - {self.type} ({self.payment_provider})"


class Payment(models.Model):
    """
    Track all payment attempts and transactions
    Includes both subscription payments and one-time payments
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        PROCESSING = 'processing', _('Processing')
        SUCCEEDED = 'succeeded', _('Succeeded')
        FAILED = 'failed', _('Failed')
        CANCELED = 'canceled', _('Canceled')
        REFUNDED = 'refunded', _('Refunded')
        PARTIALLY_REFUNDED = 'partially_refunded', _('Partially Refunded')

    class PaymentType(models.TextChoices):
        SUBSCRIPTION = 'subscription', _('Subscription Payment')
        ONE_TIME = 'one_time', _('One-Time Payment')
        UPGRADE = 'upgrade', _('Plan Upgrade')
        REFUND = 'refund', _('Refund')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='payments')
    subscription = models.ForeignKey(
        Subscription, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='payments',
        help_text='Null for one-time payments'
    )
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='payments'
    )
    
    class PaymentProvider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        DODO = 'dodo', _('Dodo Payments')
    
    # Payment provider fields
    payment_provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.DODO,
        help_text='Payment provider (stripe, dodo, etc.)'
    )
    provider_payment_intent_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text='Payment provider PaymentIntent ID (e.g., Stripe pi_xxx or Dodo payment ID)'
    )
    provider_charge_id = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        help_text='Payment provider Charge ID (e.g., Stripe ch_xxx or Dodo charge ID)'
    )
    
    # Payment details
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount in cents (e.g., 2999 = $29.99)')
    currency = models.CharField(max_length=3, default='usd')
    payment_type = models.CharField(max_length=20, choices=PaymentType.choices, default=PaymentType.SUBSCRIPTION)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    
    # Failure details
    failure_reason = models.TextField(blank=True, null=True, help_text='Reason for payment failure')
    failure_code = models.CharField(max_length=50, blank=True, null=True, help_text='Payment provider error code')
    
    # Metadata
    description = models.TextField(blank=True, help_text='Payment description')
    metadata = models.JSONField(default=dict, blank=True, help_text='Additional payment provider data')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(null=True, blank=True, help_text='When payment succeeded')
    failed_at = models.DateTimeField(null=True, blank=True, help_text='When payment failed')

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['subscription', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['provider_payment_intent_id']),
            models.Index(fields=['provider_charge_id']),
            models.Index(fields=['payment_provider', 'provider_payment_intent_id']),
        ]

    def __str__(self):
        return f"{self.user.email} - ${self.amount} ({self.status}) - {self.payment_provider}"


class Invoice(models.Model):
    """
    Store invoices for billing records from payment providers
    Includes both subscription invoices and one-time invoices
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Draft')
        OPEN = 'open', _('Open')
        PAID = 'paid', _('Paid')
        VOID = 'void', _('Void')
        UNCOLLECTIBLE = 'uncollectible', _('Uncollectible')
    
    class PaymentProvider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        DODO = 'dodo', _('Dodo Payments')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='invoices')
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoices',
        help_text='Null for one-time invoices'
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice'
    )
    
    # Payment provider fields
    payment_provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.DODO,
        help_text='Payment provider (stripe, dodo, etc.)'
    )
    provider_invoice_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Payment provider Invoice ID (e.g., Stripe in_xxx or Dodo invoice ID)'
    )
    invoice_number = models.CharField(max_length=255, blank=True, help_text='Human-readable invoice number')
    
    # Invoice details
    amount_due = models.DecimalField(max_digits=10, decimal_places=2, help_text='Amount due in cents')
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text='Amount paid in cents')
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    
    # Dates
    invoice_date = models.DateField(default=timezone.now, help_text='Invoice date')
    due_date = models.DateField(null=True, blank=True, help_text='Payment due date')
    paid_at = models.DateTimeField(null=True, blank=True, help_text='When invoice was paid')
    
    # PDF and data
    invoice_pdf_url = models.URLField(max_length=500, blank=True, help_text='Payment provider invoice PDF URL')
    invoice_data = models.JSONField(default=dict, blank=True, help_text='Full payment provider invoice object')
    
    # Metadata
    description = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-invoice_date', '-created_at']
        indexes = [
            models.Index(fields=['user', 'invoice_date']),
            models.Index(fields=['subscription', 'invoice_date']),
            models.Index(fields=['status']),
            models.Index(fields=['provider_invoice_id']),
            models.Index(fields=['payment_provider', 'provider_invoice_id']),
        ]

    def __str__(self):
        return f"Invoice {self.invoice_number or self.id} - {self.user.email} - ${self.amount_due} ({self.payment_provider})"


class BillingEvent(models.Model):
    """
    Track all billing-related events from payment provider webhooks
    Useful for auditing and debugging
    """
    class EventType(models.TextChoices):
        # Subscription events
        SUBSCRIPTION_CREATED = 'subscription.created', _('Subscription Created')
        SUBSCRIPTION_UPDATED = 'subscription.updated', _('Subscription Updated')
        SUBSCRIPTION_DELETED = 'subscription.deleted', _('Subscription Deleted')
        SUBSCRIPTION_RENEWED = 'subscription.renewed', _('Subscription Renewed')
        
        # Payment events
        PAYMENT_SUCCEEDED = 'payment_intent.succeeded', _('Payment Succeeded')
        PAYMENT_FAILED = 'payment_intent.payment_failed', _('Payment Failed')
        CHARGE_SUCCEEDED = 'charge.succeeded', _('Charge Succeeded')
        CHARGE_FAILED = 'charge.failed', _('Charge Failed')
        CHARGE_REFUNDED = 'charge.refunded', _('Charge Refunded')
        
        # Invoice events
        INVOICE_CREATED = 'invoice.created', _('Invoice Created')
        INVOICE_PAID = 'invoice.paid', _('Invoice Paid')
        INVOICE_PAYMENT_FAILED = 'invoice.payment_failed', _('Invoice Payment Failed')
        INVOICE_UPCOMING = 'invoice.upcoming', _('Invoice Upcoming')
        
        # Customer events
        CUSTOMER_CREATED = 'customer.created', _('Customer Created')
        CUSTOMER_UPDATED = 'customer.updated', _('Customer Updated')
        
        # Payment method events
        PAYMENT_METHOD_ATTACHED = 'payment_method.attached', _('Payment Method Attached')
        PAYMENT_METHOD_DETACHED = 'payment_method.detached', _('Payment Method Detached')
        
        # Dodo-specific events
        CHECKOUT_SESSION_COMPLETED = 'checkout.session.completed', _('Checkout Session Completed')
        SUBSCRIPTION_ACTIVE = 'subscription.active', _('Subscription Active')
        SUBSCRIPTION_ON_HOLD = 'subscription.on_hold', _('Subscription On Hold')
    
    class PaymentProvider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        DODO = 'dodo', _('Dodo Payments')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='billing_events', null=True, blank=True)
    subscription = models.ForeignKey(
        Subscription,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='billing_events'
    )
    
    # Payment provider fields
    payment_provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.DODO,
        help_text='Payment provider (stripe, dodo, etc.)'
    )
    provider_event_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Payment provider Event ID (e.g., Stripe evt_xxx or Dodo event ID)'
    )
    event_type = models.CharField(max_length=100, choices=EventType.choices)
    event_data = models.JSONField(default=dict, help_text='Full payment provider event object')
    
    # Processing status
    processed = models.BooleanField(default=False, help_text='Whether we successfully processed this event')
    processed_at = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(blank=True, null=True, help_text='Error if processing failed')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['provider_event_id']),
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['processed']),
            models.Index(fields=['payment_provider', 'provider_event_id']),
        ]

    def __str__(self):
        return f"{self.event_type} - {self.provider_event_id} ({self.payment_provider})"


class Refund(models.Model):
    """
    Track refunds for payments
    """
    class Status(models.TextChoices):
        PENDING = 'pending', _('Pending')
        SUCCEEDED = 'succeeded', _('Succeeded')
        FAILED = 'failed', _('Failed')
        CANCELED = 'canceled', _('Canceled')
    
    class PaymentProvider(models.TextChoices):
        STRIPE = 'stripe', _('Stripe')
        DODO = 'dodo', _('Dodo Payments')

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name='refunds')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='refunds')
    
    # Payment provider fields
    payment_provider = models.CharField(
        max_length=20,
        choices=PaymentProvider.choices,
        default=PaymentProvider.DODO,
        help_text='Payment provider (stripe, dodo, etc.)'
    )
    provider_refund_id = models.CharField(
        max_length=255,
        unique=True,
        help_text='Payment provider Refund ID (e.g., Stripe re_xxx or Dodo refund ID)'
    )
    
    # Refund details
    amount = models.DecimalField(max_digits=10, decimal_places=2, help_text='Refund amount in cents')
    currency = models.CharField(max_length=3, default='usd')
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    reason = models.CharField(max_length=100, blank=True, help_text='Reason for refund')
    description = models.TextField(blank=True)
    
    # Metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['provider_refund_id']),
            models.Index(fields=['payment_provider', 'provider_refund_id']),
        ]

    def __str__(self):
        return f"Refund ${self.amount} for {self.payment} - {self.status} ({self.payment_provider})"
