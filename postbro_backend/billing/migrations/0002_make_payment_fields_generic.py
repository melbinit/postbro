# Generated migration to make payment fields generic for multi-provider support

from django.db import migrations, models


def set_existing_provider_to_stripe(apps, schema_editor):
    """
    Set existing records to 'stripe' provider.
    These records were created before Dodo integration, so they're Stripe records.
    """
    PaymentMethod = apps.get_model('billing', 'PaymentMethod')
    Payment = apps.get_model('billing', 'Payment')
    Invoice = apps.get_model('billing', 'Invoice')
    BillingEvent = apps.get_model('billing', 'BillingEvent')
    Refund = apps.get_model('billing', 'Refund')
    
    # Update existing records to 'stripe' (they were created before Dodo integration)
    PaymentMethod.objects.all().update(payment_provider='stripe')
    Payment.objects.all().update(payment_provider='stripe')
    Invoice.objects.all().update(payment_provider='stripe')
    BillingEvent.objects.all().update(payment_provider='stripe')
    Refund.objects.all().update(payment_provider='stripe')


def reverse_set_provider(apps, schema_editor):
    """Reverse operation - no-op since we're just setting defaults"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
        ('accounts', '0008_update_plans_for_mvp'),
    ]

    operations = [
        # ========== PaymentMethod Changes ==========
        # Add payment_provider field first (before renaming)
        migrations.AddField(
            model_name='paymentmethod',
            name='payment_provider',
            field=models.CharField(
                choices=[('stripe', 'Stripe'), ('dodo', 'Dodo Payments')],
                default='dodo',
                help_text='Payment provider (stripe, dodo, etc.)',
                max_length=20
            ),
        ),
        # Rename stripe_payment_method_id to provider_payment_method_id
        migrations.RenameField(
            model_name='paymentmethod',
            old_name='stripe_payment_method_id',
            new_name='provider_payment_method_id',
        ),
        # Update help texts
        migrations.AlterField(
            model_name='paymentmethod',
            name='deleted_at',
            field=models.DateTimeField(
                blank=True,
                help_text='Soft delete when removed from payment provider',
                null=True
            ),
        ),
        migrations.AlterField(
            model_name='paymentmethod',
            name='metadata',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Additional payment provider data'
            ),
        ),
        
        # ========== Payment Changes ==========
        # Add payment_provider field
        migrations.AddField(
            model_name='payment',
            name='payment_provider',
            field=models.CharField(
                choices=[('stripe', 'Stripe'), ('dodo', 'Dodo Payments')],
                default='dodo',
                help_text='Payment provider (stripe, dodo, etc.)',
                max_length=20
            ),
        ),
        # Rename fields
        migrations.RenameField(
            model_name='payment',
            old_name='stripe_payment_intent_id',
            new_name='provider_payment_intent_id',
        ),
        migrations.RenameField(
            model_name='payment',
            old_name='stripe_charge_id',
            new_name='provider_charge_id',
        ),
        # Update help texts
        migrations.AlterField(
            model_name='payment',
            name='failure_code',
            field=models.CharField(
                blank=True,
                help_text='Payment provider error code',
                max_length=50,
                null=True
            ),
        ),
        migrations.AlterField(
            model_name='payment',
            name='metadata',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Additional payment provider data'
            ),
        ),
        
        # ========== Invoice Changes ==========
        # Add payment_provider field
        migrations.AddField(
            model_name='invoice',
            name='payment_provider',
            field=models.CharField(
                choices=[('stripe', 'Stripe'), ('dodo', 'Dodo Payments')],
                default='dodo',
                help_text='Payment provider (stripe, dodo, etc.)',
                max_length=20
            ),
        ),
        # Rename fields
        migrations.RenameField(
            model_name='invoice',
            old_name='stripe_invoice_id',
            new_name='provider_invoice_id',
        ),
        migrations.RenameField(
            model_name='invoice',
            old_name='stripe_invoice_number',
            new_name='invoice_number',
        ),
        # Update help texts
        migrations.AlterField(
            model_name='invoice',
            name='invoice_pdf_url',
            field=models.URLField(
                blank=True,
                help_text='Payment provider invoice PDF URL',
                max_length=500
            ),
        ),
        migrations.AlterField(
            model_name='invoice',
            name='invoice_data',
            field=models.JSONField(
                blank=True,
                default=dict,
                help_text='Full payment provider invoice object'
            ),
        ),
        
        # ========== BillingEvent Changes ==========
        # Add payment_provider field
        migrations.AddField(
            model_name='billingevent',
            name='payment_provider',
            field=models.CharField(
                choices=[('stripe', 'Stripe'), ('dodo', 'Dodo Payments')],
                default='dodo',
                help_text='Payment provider (stripe, dodo, etc.)',
                max_length=20
            ),
        ),
        # Rename field
        migrations.RenameField(
            model_name='billingevent',
            old_name='stripe_event_id',
            new_name='provider_event_id',
        ),
        # Update help text
        migrations.AlterField(
            model_name='billingevent',
            name='event_data',
            field=models.JSONField(
                default=dict,
                help_text='Full payment provider event object'
            ),
        ),
        
        # ========== Refund Changes ==========
        # Add payment_provider field
        migrations.AddField(
            model_name='refund',
            name='payment_provider',
            field=models.CharField(
                choices=[('stripe', 'Stripe'), ('dodo', 'Dodo Payments')],
                default='dodo',
                help_text='Payment provider (stripe, dodo, etc.)',
                max_length=20
            ),
        ),
        # Rename field
        migrations.RenameField(
            model_name='refund',
            old_name='stripe_refund_id',
            new_name='provider_refund_id',
        ),
        
        # ========== Update Indexes ==========
        # Remove old indexes
        migrations.RemoveIndex(
            model_name='paymentmethod',
            name='billing_pay_stripe__44aa09_idx',
        ),
        migrations.RemoveIndex(
            model_name='payment',
            name='billing_pay_stripe__5c9ebe_idx',
        ),
        migrations.RemoveIndex(
            model_name='payment',
            name='billing_pay_stripe__b4a1f1_idx',
        ),
        migrations.RemoveIndex(
            model_name='invoice',
            name='billing_inv_stripe__1798ef_idx',
        ),
        migrations.RemoveIndex(
            model_name='billingevent',
            name='billing_bil_stripe__b2aeb1_idx',
        ),
        migrations.RemoveIndex(
            model_name='refund',
            name='billing_ref_stripe__86d03b_idx',
        ),
        
        # Add new composite indexes for better query performance
        migrations.AddIndex(
            model_name='paymentmethod',
            index=models.Index(
                fields=['payment_provider', 'provider_payment_method_id'],
                name='billing_pay_provider_pm_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['payment_provider', 'provider_payment_intent_id'],
                name='billing_pay_provider_pi_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['payment_provider', 'provider_charge_id'],
                name='billing_pay_provider_ch_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['payment_provider', 'provider_invoice_id'],
                name='billing_inv_provider_inv_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='billingevent',
            index=models.Index(
                fields=['payment_provider', 'provider_event_id'],
                name='billing_bil_provider_evt_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='refund',
            index=models.Index(
                fields=['payment_provider', 'provider_refund_id'],
                name='billing_ref_provider_ref_idx'
            ),
        ),
        
        # Keep individual indexes for backward compatibility and direct lookups
        migrations.AddIndex(
            model_name='paymentmethod',
            index=models.Index(
                fields=['provider_payment_method_id'],
                name='billing_pay_provider_pm_id_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['provider_payment_intent_id'],
                name='billing_pay_provider_pi_id_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='payment',
            index=models.Index(
                fields=['provider_charge_id'],
                name='billing_pay_provider_ch_id_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='invoice',
            index=models.Index(
                fields=['provider_invoice_id'],
                name='billing_inv_provider_inv_id_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='billingevent',
            index=models.Index(
                fields=['provider_event_id'],
                name='billing_bil_provider_evt_id_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='refund',
            index=models.Index(
                fields=['provider_refund_id'],
                name='billing_ref_provider_ref_id_idx'
            ),
        ),
        
        # ========== Data Migration ==========
        # Set existing records to 'stripe' provider
        migrations.RunPython(
            set_existing_provider_to_stripe,
            reverse_set_provider
        ),
    ]

