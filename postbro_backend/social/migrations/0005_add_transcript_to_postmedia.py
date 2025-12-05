# Generated manually for adding transcript field to PostMedia

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('social', '0004_add_supabase_storage_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='postmedia',
            name='transcript',
            field=models.TextField(blank=True, help_text='Audio transcript for video media (from Whisper AI or YouTube API)', null=True),
        ),
    ]




from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('social', '0004_add_supabase_storage_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='postmedia',
            name='transcript',
            field=models.TextField(blank=True, help_text='Audio transcript for video media (from Whisper AI or YouTube API)', null=True),
        ),
    ]



