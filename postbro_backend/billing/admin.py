from django.contrib import admin
from .models import PaymentMethod, Payment, Invoice, BillingEvent, Refund


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'payment_provider', 'type', 'card_brand', 'card_last4', 'is_default', 'created_at']
    list_filter = ['payment_provider', 'type', 'is_default', 'created_at']
    search_fields = ['user__email', 'provider_payment_method_id', 'card_last4']
    readonly_fields = ['id', 'created_at', 'updated_at', 'deleted_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'payment_provider', 'provider_payment_method_id', 'type', 'is_default')
        }),
        ('Card Details', {
            'fields': ('card_brand', 'card_last4', 'card_exp_month', 'card_exp_year'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata', 'deleted_at'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'payment_provider', 'amount', 'currency', 'payment_type', 'status', 'created_at', 'paid_at']
    list_filter = ['payment_provider', 'status', 'payment_type', 'currency', 'created_at']
    search_fields = ['user__email', 'provider_payment_intent_id', 'provider_charge_id', 'description']
    readonly_fields = ['id', 'created_at', 'updated_at', 'paid_at', 'failed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'subscription', 'payment_method', 'payment_provider', 'payment_type', 'status')
        }),
        ('Payment Provider IDs', {
            'fields': ('provider_payment_intent_id', 'provider_charge_id')
        }),
        ('Payment Details', {
            'fields': ('amount', 'currency', 'description')
        }),
        ('Failure Information', {
            'fields': ('failure_reason', 'failure_code', 'failed_at'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ['invoice_number', 'user', 'payment_provider', 'amount_due', 'amount_paid', 'status', 'invoice_date', 'due_date']
    list_filter = ['payment_provider', 'status', 'currency', 'invoice_date']
    search_fields = ['user__email', 'provider_invoice_id', 'invoice_number']
    readonly_fields = ['id', 'created_at', 'updated_at', 'paid_at']
    date_hierarchy = 'invoice_date'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'subscription', 'payment', 'payment_provider', 'status')
        }),
        ('Payment Provider IDs', {
            'fields': ('provider_invoice_id', 'invoice_number')
        }),
        ('Invoice Details', {
            'fields': ('amount_due', 'amount_paid', 'currency', 'invoice_date', 'due_date', 'description')
        }),
        ('PDF & Data', {
            'fields': ('invoice_pdf_url', 'invoice_data'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(BillingEvent)
class BillingEventAdmin(admin.ModelAdmin):
    list_display = ['provider_event_id', 'payment_provider', 'event_type', 'user', 'processed', 'created_at']
    list_filter = ['payment_provider', 'event_type', 'processed', 'created_at']
    search_fields = ['user__email', 'provider_event_id', 'event_type']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'subscription', 'payment_provider', 'provider_event_id', 'event_type', 'processed')
        }),
        ('Event Data', {
            'fields': ('event_data',),
            'classes': ('collapse',)
        }),
        ('Processing', {
            'fields': ('processed_at', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'payment', 'payment_provider', 'amount', 'status', 'created_at', 'processed_at']
    list_filter = ['payment_provider', 'status', 'currency', 'created_at']
    search_fields = ['user__email', 'provider_refund_id', 'reason']
    readonly_fields = ['id', 'created_at', 'updated_at', 'processed_at']
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'user', 'payment', 'payment_provider', 'provider_refund_id', 'status')
        }),
        ('Refund Details', {
            'fields': ('amount', 'currency', 'reason', 'description')
        }),
        ('Metadata', {
            'fields': ('metadata',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )
