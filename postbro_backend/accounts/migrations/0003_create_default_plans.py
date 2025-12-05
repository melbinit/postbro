from django.db import migrations

def create_default_plans(apps, schema_editor):
    Plan = apps.get_model('accounts', 'Plan')
    
    # Create Free plan
    Plan.objects.create(
        name='Free',
        description='Perfect for trying out PostBro',
        price=0.00,
        max_handles=1,
        max_urls=5,
        max_analyses_per_day=10,
        is_active=True
    )
    
    # Create Basic plan
    Plan.objects.create(
        name='Basic',
        description='Great for small businesses and individuals',
        price=10.00,
        max_handles=5,
        max_urls=20,
        max_analyses_per_day=50,
        is_active=True
    )
    
    # Create Pro plan
    Plan.objects.create(
        name='Pro',
        description='Advanced features for growing businesses',
        price=25.00,
        max_handles=20,
        max_urls=100,
        max_analyses_per_day=500,
        is_active=True
    )

def remove_default_plans(apps, schema_editor):
    Plan = apps.get_model('accounts', 'Plan')
    Plan.objects.filter(name__in=['Free', 'Basic', 'Pro']).delete()

class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0002_user_password_reset_sent_at_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_plans, remove_default_plans),
    ] 