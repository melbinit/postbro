# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0011_add_chat_models'),
    ]

    operations = [
        migrations.AddField(
            model_name='postanalysis',
            name='analysis_completed',
            field=models.BooleanField(
                default=False,
                help_text='Whether the analysis has been completed (first Gemini call done)'
            ),
        ),
    ]

