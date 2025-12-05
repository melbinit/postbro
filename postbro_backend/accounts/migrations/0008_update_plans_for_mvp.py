# Generated migration to update plans for MVP launch

from django.db import migrations


def update_plans_for_mvp(apps, schema_editor):
    """
    Update existing plans with MVP limits:
    - Free: 3 posts/day, 10 questions/day, $0
    - Starter (Basic): 10 posts/day, 50 questions/day, $29
    - Pro: 25 posts/day, 200 questions/day, $59
    
    Note: max_analyses_per_day = max_urls (1 URL = 1 analysis)
    """
    Plan = apps.get_model('accounts', 'Plan')
    
    # Free Plan
    free_plan = Plan.objects.filter(name='Free').first()
    if free_plan:
        free_plan.max_urls = 3
        free_plan.max_analyses_per_day = 3  # Same as max_urls (1 URL = 1 analysis)
        free_plan.max_questions_per_day = 10
        free_plan.price = 0.00
        free_plan.description = 'Perfect for trying the product'
        free_plan.save()
        print(f"✅ Updated Free plan: {free_plan.max_urls} posts/day, {free_plan.max_questions_per_day} questions/day")
    
    # Basic → Starter Plan
    basic_plan = Plan.objects.filter(name='Basic').first()
    if basic_plan:
        basic_plan.name = 'Starter'  # Rename to Starter
        basic_plan.max_urls = 10
        basic_plan.max_analyses_per_day = 10  # Same as max_urls
        basic_plan.max_questions_per_day = 50
        basic_plan.price = 29.00
        basic_plan.description = 'Good for regular creators'
        basic_plan.save()
        print(f"✅ Updated Starter plan: {basic_plan.max_urls} posts/day, {basic_plan.max_questions_per_day} questions/day, ${basic_plan.price}")
    
    # Pro Plan
    pro_plan = Plan.objects.filter(name='Pro').first()
    if pro_plan:
        pro_plan.max_urls = 25
        pro_plan.max_analyses_per_day = 25  # Same as max_urls
        pro_plan.max_questions_per_day = 200
        pro_plan.price = 59.00
        pro_plan.description = 'For power users/agencies'
        pro_plan.save()
        print(f"✅ Updated Pro plan: {pro_plan.max_urls} posts/day, {pro_plan.max_questions_per_day} questions/day, ${pro_plan.price}")


def reverse_update(apps, schema_editor):
    """
    Revert to previous plan values (for rollback if needed)
    """
    Plan = apps.get_model('accounts', 'Plan')
    
    # Revert Free
    free_plan = Plan.objects.filter(name='Free').first()
    if free_plan:
        free_plan.max_urls = 3
        free_plan.max_analyses_per_day = 1000
        free_plan.max_questions_per_day = 10
        free_plan.price = 0.00
        free_plan.save()
    
    # Revert Starter → Basic
    starter_plan = Plan.objects.filter(name='Starter').first()
    if starter_plan:
        starter_plan.name = 'Basic'
        starter_plan.max_urls = 10
        starter_plan.max_analyses_per_day = 1000
        starter_plan.max_questions_per_day = 50
        starter_plan.price = 19.00
        starter_plan.save()
    
    # Revert Pro
    pro_plan = Plan.objects.filter(name='Pro').first()
    if pro_plan:
        pro_plan.max_urls = 30
        pro_plan.max_analyses_per_day = 1000
        pro_plan.max_questions_per_day = 200
        pro_plan.price = 49.00
        pro_plan.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_questions_tracking'),
    ]

    operations = [
        migrations.RunPython(update_plans_for_mvp, reverse_update),
    ]




from django.db import migrations


def update_plans_for_mvp(apps, schema_editor):
    """
    Update existing plans with MVP limits:
    - Free: 3 posts/day, 10 questions/day, $0
    - Starter (Basic): 10 posts/day, 50 questions/day, $29
    - Pro: 25 posts/day, 200 questions/day, $59
    
    Note: max_analyses_per_day = max_urls (1 URL = 1 analysis)
    """
    Plan = apps.get_model('accounts', 'Plan')
    
    # Free Plan
    free_plan = Plan.objects.filter(name='Free').first()
    if free_plan:
        free_plan.max_urls = 3
        free_plan.max_analyses_per_day = 3  # Same as max_urls (1 URL = 1 analysis)
        free_plan.max_questions_per_day = 10
        free_plan.price = 0.00
        free_plan.description = 'Perfect for trying the product'
        free_plan.save()
        print(f"✅ Updated Free plan: {free_plan.max_urls} posts/day, {free_plan.max_questions_per_day} questions/day")
    
    # Basic → Starter Plan
    basic_plan = Plan.objects.filter(name='Basic').first()
    if basic_plan:
        basic_plan.name = 'Starter'  # Rename to Starter
        basic_plan.max_urls = 10
        basic_plan.max_analyses_per_day = 10  # Same as max_urls
        basic_plan.max_questions_per_day = 50
        basic_plan.price = 29.00
        basic_plan.description = 'Good for regular creators'
        basic_plan.save()
        print(f"✅ Updated Starter plan: {basic_plan.max_urls} posts/day, {basic_plan.max_questions_per_day} questions/day, ${basic_plan.price}")
    
    # Pro Plan
    pro_plan = Plan.objects.filter(name='Pro').first()
    if pro_plan:
        pro_plan.max_urls = 25
        pro_plan.max_analyses_per_day = 25  # Same as max_urls
        pro_plan.max_questions_per_day = 200
        pro_plan.price = 59.00
        pro_plan.description = 'For power users/agencies'
        pro_plan.save()
        print(f"✅ Updated Pro plan: {pro_plan.max_urls} posts/day, {pro_plan.max_questions_per_day} questions/day, ${pro_plan.price}")


def reverse_update(apps, schema_editor):
    """
    Revert to previous plan values (for rollback if needed)
    """
    Plan = apps.get_model('accounts', 'Plan')
    
    # Revert Free
    free_plan = Plan.objects.filter(name='Free').first()
    if free_plan:
        free_plan.max_urls = 3
        free_plan.max_analyses_per_day = 1000
        free_plan.max_questions_per_day = 10
        free_plan.price = 0.00
        free_plan.save()
    
    # Revert Starter → Basic
    starter_plan = Plan.objects.filter(name='Starter').first()
    if starter_plan:
        starter_plan.name = 'Basic'
        starter_plan.max_urls = 10
        starter_plan.max_analyses_per_day = 1000
        starter_plan.max_questions_per_day = 50
        starter_plan.price = 19.00
        starter_plan.save()
    
    # Revert Pro
    pro_plan = Plan.objects.filter(name='Pro').first()
    if pro_plan:
        pro_plan.max_urls = 30
        pro_plan.max_analyses_per_day = 1000
        pro_plan.max_questions_per_day = 200
        pro_plan.price = 49.00
        pro_plan.save()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0007_add_questions_tracking'),
    ]

    operations = [
        migrations.RunPython(update_plans_for_mvp, reverse_update),
    ]



