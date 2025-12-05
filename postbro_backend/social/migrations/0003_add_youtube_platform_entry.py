# Generated manually for Phase 1 implementation
from django.db import migrations
import uuid


def create_youtube_platform(apps, schema_editor):
    """
    Create YouTube platform entry in the database.
    
    This ensures the YouTube platform exists for use in the application.
    """
    Platform = apps.get_model('social', 'Platform')
    
    # Check if YouTube platform already exists
    if not Platform.objects.filter(name='youtube').exists():
        Platform.objects.create(
            id=uuid.uuid4(),
            name='youtube',
            is_active=True
        )


def remove_youtube_platform(apps, schema_editor):
    """
    Remove YouTube platform entry (reverse migration).
    """
    Platform = apps.get_model('social', 'Platform')
    Platform.objects.filter(name='youtube').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('social', '0002_add_youtube_platform_and_transcript_fields'),
    ]

    operations = [
        migrations.RunPython(
            create_youtube_platform,
            reverse_code=remove_youtube_platform
        ),
    ]


