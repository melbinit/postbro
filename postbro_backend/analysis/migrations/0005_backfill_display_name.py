# Generated migration to backfill display_name for existing analyses

from django.db import migrations
from django.db.models import Q


def backfill_display_name(apps, schema_editor):
    """
    Backfill display_name for existing analyses that have posts.
    This ensures old analyses also show usernames in the sidebar.
    
    Strategy:
    1. Try to get username from ManyToMany posts (new analyses)
    2. Fallback to status metadata post_ids (old analyses)
    3. Use bulk_update for performance
    """
    PostAnalysisRequest = apps.get_model('analysis', 'PostAnalysisRequest')
    Post = apps.get_model('social', 'Post')
    AnalysisStatusHistory = apps.get_model('analysis', 'AnalysisStatusHistory')
    
    # Get all analyses that don't have display_name
    analyses = PostAnalysisRequest.objects.filter(
        display_name__isnull=True
    ).prefetch_related('posts', 'status_history')
    
    updates = []
    updated_count = 0
    
    for analysis in analyses:
        display_name = None
        
        # Method 1: Try ManyToMany posts (new analyses)
        posts = list(analysis.posts.all()[:2])
        if posts:
            # Sort by posted_at (most recent first)
            posts.sort(key=lambda p: p.posted_at if p.posted_at else None, reverse=True)
            first_post = posts[0]
            if first_post and first_post.username:
                display_name = first_post.username
        else:
            # Method 2: Fallback to status metadata (old analyses without ManyToMany links)
            # Check social_data_fetched status for post_ids
            status = analysis.status_history.filter(
                stage='social_data_fetched'
            ).first()
            
            if status and status.metadata:
                post_ids = status.metadata.get('post_ids', [])
                if post_ids:
                    # Try to get first post by ID
                    try:
                        first_post = Post.objects.filter(id=post_ids[0]).first()
                        if first_post and first_post.username:
                            display_name = first_post.username
                    except Exception:
                        pass
        
        # Update if we found a display_name
        if display_name:
            analysis.display_name = display_name
            updates.append(analysis)
            updated_count += 1
            
            # Use bulk_update for better performance (every 100 records)
            if len(updates) >= 100:
                PostAnalysisRequest.objects.bulk_update(updates, ['display_name'])
                updates = []
    
    # Update remaining records
    if updates:
        PostAnalysisRequest.objects.bulk_update(updates, ['display_name'])
    
    print(f'✅ Backfilled display_name for {updated_count} analyses')


def reverse_backfill(apps, schema_editor):
    """
    Reverse migration - clear display_name for all analyses.
    This is safe because display_name will be repopulated on next social_data_fetched.
    """
    PostAnalysisRequest = apps.get_model('analysis', 'PostAnalysisRequest')
    PostAnalysisRequest.objects.update(display_name=None)
    print('✅ Cleared display_name for all analyses')


class Migration(migrations.Migration):

    dependencies = [
        ('analysis', '0004_add_display_name_field'),
        ('social', '0004_add_supabase_storage_fields'),  # Ensure Post model exists
    ]

    operations = [
        migrations.RunPython(backfill_display_name, reverse_backfill),
    ]

