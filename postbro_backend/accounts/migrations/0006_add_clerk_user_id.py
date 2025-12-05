# Generated migration to add Clerk user ID field

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_update_plan_limits_urls_only'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='clerk_user_id',
            field=models.CharField(blank=True, help_text='Clerk user ID', max_length=255, null=True, unique=True),
        ),
    ]





from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_update_plan_limits_urls_only'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='clerk_user_id',
            field=models.CharField(blank=True, help_text='Clerk user ID', max_length=255, null=True, unique=True),
        ),
    ]




