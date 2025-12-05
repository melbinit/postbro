from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from social.models import Post, PostMedia
from analysis.models import PostAnalysisRequest
import uuid


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_posts_by_analysis_request(request, analysis_request_id):
    """
    Get all posts associated with an analysis request.
    
    Uses ManyToMany relationship for fast, direct access to posts.
    """
    try:
        # Get the analysis request and verify ownership
        # Prefetch posts via ManyToMany (professional way - instant access)
        analysis_request = get_object_or_404(
            PostAnalysisRequest.objects.prefetch_related('posts'),
            id=analysis_request_id,
            user=request.user
        )
        
        # Get posts directly from ManyToMany relationship (already prefetched)
        posts = analysis_request.posts.all().select_related('platform').prefetch_related('media')
        
        if not posts.exists():
            return Response({
                'posts': [],
                'count': 0,
                'analysis_request_id': str(analysis_request.id),
            }, status=status.HTTP_200_OK)
        
        # Serialize posts
        posts_data = []
        for post in posts:
            # Get media - refresh to ensure we have latest supabase_url
            media = list(post.media.all())
            media_data = []
            for m in media:
                media_data.append({
                    'id': str(m.id),
                    'media_type': m.media_type,
                    'source_url': m.source_url,
                    'supabase_url': m.supabase_url,
                    'uploaded_to_supabase': m.uploaded_to_supabase,
                })
            
            # Get thumbnail (first image or video thumbnail)
            thumbnail = None
            thumbnail_media = post.media.filter(
                media_type__in=['image', 'video_thumbnail']
            ).first()
            if thumbnail_media:
                thumbnail = thumbnail_media.supabase_url or thumbnail_media.source_url
            
            posts_data.append({
                'id': str(post.id),
                'platform': post.platform.name,
                'platform_post_id': post.platform_post_id,
                'username': post.username,
                'content': post.content,
                'url': post.url,
                'engagement_score': post.engagement_score,
                'metrics': post.metrics,
                'posted_at': post.posted_at.isoformat(),
                'thumbnail': thumbnail,
                'media': media_data,
                'transcript': post.transcript,
                'formatted_transcript': post.formatted_transcript,
            })
        
        return Response({
            'posts': posts_data,
            'count': len(posts_data),
            'analysis_request_id': str(analysis_request.id),
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {
                'error': 'Failed to fetch posts',
                'details': str(e)
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
