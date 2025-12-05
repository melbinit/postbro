from django.db import migrations


def update_plan_limits(apps, schema_editor):
    """Update plan limits to URLs-only mode with new pricing"""
    Plan = apps.get_model('accounts', 'Plan')
    
    # Update Free plan: $0/month, 3 URLs/day
    free_plan = Plan.objects.filter(name__iexact='Free').first()
    if free_plan:
        free_plan.price = 0.00
        free_plan.max_urls = 3
        free_plan.max_handles = 0  # Disable username analyses
        free_plan.max_analyses_per_day = 1000  # Keep high for suggestions
        free_plan.save()
        print(f"✅ Updated Free plan: {free_plan.max_urls} URLs/day")
    
    # Update Basic plan: $19/month, 10 URLs/day
    basic_plan = Plan.objects.filter(name__iexact='Basic').first()
    if basic_plan:
        basic_plan.price = 19.00
        basic_plan.max_urls = 10
        basic_plan.max_handles = 0  # Disable username analyses
        basic_plan.max_analyses_per_day = 1000  # Keep high for suggestions
        basic_plan.save()
        print(f"✅ Updated Basic plan: {basic_plan.max_urls} URLs/day")
    
    # Update Pro plan: $49/month, 30 URLs/day
    pro_plan = Plan.objects.filter(name__iexact='Pro').first()
    if pro_plan:
        pro_plan.price = 49.00
        pro_plan.max_urls = 30
        pro_plan.max_handles = 0  # Disable username analyses
        pro_plan.max_analyses_per_day = 1000  # Keep high for suggestions
        pro_plan.save()
        print(f"✅ Updated Pro plan: {pro_plan.max_urls} URLs/day")


def reverse_update_plan_limits(apps, schema_editor):
    """Reverse migration - restore old limits"""
    Plan = apps.get_model('accounts', 'Plan')
    
    # Restore Free plan
    free_plan = Plan.objects.filter(name__iexact='Free').first()
    if free_plan:
        free_plan.price = 0.00
        free_plan.max_urls = 1000
        free_plan.max_handles = 1000
        free_plan.save()
    
    # Restore Basic plan
    basic_plan = Plan.objects.filter(name__iexact='Basic').first()
    if basic_plan:
        basic_plan.price = 10.00
        basic_plan.max_urls = 1000
        basic_plan.max_handles = 1000
        basic_plan.save()
    
    # Restore Pro plan
    pro_plan = Plan.objects.filter(name__iexact='Pro').first()
    if pro_plan:
        pro_plan.price = 25.00
        pro_plan.max_urls = 1000
        pro_plan.max_handles = 1000
        pro_plan.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_remove_user_email_verification_sent_at_and_more'),
    ]

    operations = [
        migrations.RunPython(update_plan_limits, reverse_update_plan_limits),
    ]






