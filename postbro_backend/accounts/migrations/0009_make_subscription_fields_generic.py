# Generated migration to make subscription payment fields generic

from django.db import migrations, models


def set_existing_subscription_provider_to_stripe(apps, schema_editor):
    """
    Set existing subscription records to 'stripe' provider.
    These records were created before Dodo integration.
    """
    Subscription = apps.get_model('accounts', 'Subscription')
    Subscription.objects.all().update(payment_provider='stripe')


def reverse_set_subscription_provider(apps, schema_editor):
    """Reverse operation - no-op"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0008_update_plans_for_mvp'),
    ]

    operations = [
        # Add payment_provider field
        migrations.AddField(
            model_name='subscription',
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
            model_name='subscription',
            old_name='stripe_customer_id',
            new_name='provider_customer_id',
        ),
        migrations.RenameField(
            model_name='subscription',
            old_name='stripe_subscription_id',
            new_name='provider_subscription_id',
        ),
        # Add composite indexes for better query performance
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(
                fields=['payment_provider', 'provider_customer_id'],
                name='accounts_sub_provider_cust_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(
                fields=['payment_provider', 'provider_subscription_id'],
                name='accounts_sub_provider_sub_idx'
            ),
        ),
        # Keep individual indexes for direct lookups
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(
                fields=['provider_customer_id'],
                name='accounts_sub_provider_cust_id_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='subscription',
            index=models.Index(
                fields=['provider_subscription_id'],
                name='accounts_sub_provider_sub_id_idx'
            ),
        ),
        # Data migration
        migrations.RunPython(
            set_existing_subscription_provider_to_stripe,
            reverse_set_subscription_provider
        ),
    ]

