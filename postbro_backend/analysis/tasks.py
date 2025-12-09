"""
Celery Tasks for Analysis Processing

This module contains Celery tasks for processing analysis requests.
The main task orchestrates different processors for each stage of analysis.
"""

import logging
import time
from typing import Dict, List
from celery import shared_task
from django.utils import timezone

from .models import PostAnalysisRequest
from .utils import (
    create_status,
    create_error_status,
    create_partial_success_status,
    estimate_cost,
    handle_analysis_error,
)
from accounts.utils import increment_usage
from social.services.url_parser import detect_platform_from_url
from analysis.processors.social_collector import collect_social_posts
from analysis.processors.post_linker import verify_and_relink_posts
from analysis.processors.media_extractor import extract_media_for_analysis, check_transcription_status
from analysis.processors.gemini_analyzer import analyze_posts_with_gemini

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_analysis_request(self, analysis_request_id: str):
    """
    Main Celery task to process an analysis request.
    
    This task orchestrates:
    - URL parsing and platform detection
    - Social media collection (via social_collector)
    - Post linking verification (via post_linker)
    - Media extraction (via media_extractor)
    - Gemini AI analysis (via gemini_analyzer)
    - Status history creation
    - Error handling with partial failures
    
    Args:
        analysis_request_id: UUID of the PostAnalysisRequest
        
    Returns:
        Dictionary with processing results
    """
    analysis_request_id_str = str(analysis_request_id)
    
    logger.info(f"🚀 [CeleryTask] Task received - analysis_request_id: {analysis_request_id_str}, task_id: {self.request.id}")
    logger.info(f"📋 [CeleryTask] Task details - retries: {self.request.retries}, max_retries: {self.max_retries}")
    
    start_time = timezone.now()
    
    try:
        # Get the analysis request
        logger.info(f"🔍 [CeleryTask] Fetching analysis request from database...")
        analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
        
        logger.info(f"✅ [CeleryTask] Analysis request found: {analysis_request_id}")
        logger.info(f"📊 [CeleryTask] Request details - platform: {analysis_request.platform}, "
                   f"status: {analysis_request.status}, "
                   f"post_urls: {len(analysis_request.post_urls) if analysis_request.post_urls else 0}")
        
        # Status 1: Request created (already done in view, but ensure it exists)
        try:
            latest_status = analysis_request.status_history.order_by('-created_at').first()
            if not latest_status or latest_status.stage != 'request_created':
                create_status(
                    analysis_request,
                    'request_created',
                    'Analysis request created',
                    metadata={'urls_count': len(analysis_request.post_urls)},
                    progress_percentage=0
                )
        except Exception as e:
            logger.warning(
                f"⚠️ [Analysis] Could not create initial status for analysis_request_id={analysis_request_id_str}: {e}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
        
        # Validate that we have URLs
        if not analysis_request.post_urls:
            raise ValueError("post_urls is required. Username-based analysis not yet implemented.")
        
        # Status 2: Fetching posts
        create_status(
            analysis_request,
            'fetching_posts',
            'Fetching posts...',
            metadata={'urls_count': len(analysis_request.post_urls)},
            progress_percentage=10,
            api_calls_made=0
        )
        
        # Parse URLs and group by platform
        urls_by_platform: Dict[str, List[str]] = {}
        invalid_urls = []
        
        for url in analysis_request.post_urls:
            platform = detect_platform_from_url(url)
            if not platform:
                logger.warning(f"Invalid URL format: {url}")
                invalid_urls.append(url)
                create_error_status(
                    analysis_request,
                    'INVALID_URL',
                    f'Invalid URL format: {url}',
                    retryable=False,
                    actionable_message='Please check the URL format and try again',
                    metadata={'url': url}
                )
                continue
            
            if platform not in urls_by_platform:
                urls_by_platform[platform] = []
            urls_by_platform[platform].append(url)
        
        if not urls_by_platform:
            raise ValueError("No valid URLs found. All URLs were invalid.")
        
        # Store media bytes separately (not on Post objects, so they survive refresh_from_db())
        # Structure: {post_id: {media_id: [{'bytes': bytes, 'mime_type': str, 'media_type': str}]}}
        media_bytes_by_post_id = {}
        
        # Stage 1: Social Media Collection
        try:
            all_posts, failed_urls, total_api_calls, fast_path_post_ids = collect_social_posts(
                analysis_request,
                urls_by_platform,
                media_bytes_by_post_id,
            )
        except Exception as e:
            handle_analysis_error(
                analysis_request,
                error_stage=PostAnalysisRequest.ErrorStage.SOCIAL_COLLECTION,
                exception=e,
                failed_at_stage='fetching_posts',
                metadata={'urls_by_platform': list(urls_by_platform.keys())}
            )
            return {
                'success': False,
                'error': 'Social media collection failed',
            }
        
        # Calculate cost estimate
        cost_estimate = estimate_cost(
            platform=analysis_request.platform,
            api_calls=total_api_calls,
            operation_type='scraping'
        )
        
        # Verify and re-link all posts
        verify_and_relink_posts(analysis_request, all_posts)
        
        # Verify all media uploads completed
        for post in all_posts:
            post.refresh_from_db()
            pending_media = post.media.filter(
                media_type__in=['image', 'video_thumbnail'],
                supabase_url__isnull=True,
                uploaded_to_supabase=False
            )
            if pending_media.exists():
                logger.warning(f"Post {post.id} has {pending_media.count()} media items still uploading")
        
        # Status 3: Social data fetched (or partial success)
        succeeded_count = len(all_posts)
        
        if failed_urls and succeeded_count > 0:
            # Partial success
            create_partial_success_status(
                analysis_request,
                succeeded=succeeded_count,
                failed=len(failed_urls),
                total=len(analysis_request.post_urls),
                failed_urls=failed_urls,
                succeeded_post_ids=[str(p.id) for p in all_posts]
            )
        elif succeeded_count > 0:
            # Extract username from first post for sidebar display
            display_name = None
            if all_posts:
                first_post = all_posts[0]
                first_post.refresh_from_db()
                if first_post and first_post.username:
                    display_name = first_post.username
                    logger.info(f"✅ Extracted display_name from post: {display_name}")
            
            # Store display_name
            if display_name:
                analysis_request.display_name = display_name
                analysis_request.save(update_fields=['display_name'])
                logger.info(f"✅ Saved display_name '{display_name}' to analysis {analysis_request.id}")
            
            # Full success - CREATE STATUS IMMEDIATELY
            logger.info(f"📤 Creating social_data_fetched status for {analysis_request.id} with username: {display_name}")
            create_status(
                analysis_request,
                'social_data_fetched',
                f'Fetched {succeeded_count} posts successfully',
                metadata={
                    'posts_count': succeeded_count,
                    'post_ids': [str(p.id) for p in all_posts],
                    'platforms': list(urls_by_platform.keys()),
                    'username': display_name,
                },
                progress_percentage=30,
                api_calls_made=total_api_calls,
                cost_estimate=cost_estimate,
            )
            logger.info(f"✅ social_data_fetched status created and sent to frontend for {analysis_request.id}")
            
            # Status: Collecting media
            create_status(
                analysis_request,
                'collecting_media',
                'Collecting media and extracting frames...',
                metadata={
                    'posts_count': succeeded_count,
                    'platforms': list(urls_by_platform.keys()),
                },
                progress_percentage=40,
            )
            
            # Stage 2: Media Extraction
            try:
                extract_media_for_analysis(
                    analysis_request,
                    all_posts,
                    media_bytes_by_post_id,
                    fast_path_post_ids,
                )
            except Exception as e:
                handle_analysis_error(
                    analysis_request,
                    error_stage=PostAnalysisRequest.ErrorStage.MEDIA_EXTRACTION,
                    exception=e,
                    failed_at_stage='social_data_fetched',
                    metadata={'posts_count': len(all_posts), 'platform': analysis_request.platform}
                )
                return {
                    'success': False,
                    'error': 'Media extraction failed',
                    'posts_fetched': len(all_posts)
                }
            
            # Check transcription status
            has_videos = check_transcription_status(all_posts)
            if has_videos:
                create_status(
                    analysis_request,
                    'transcribing',
                    'Transcribing video audio...',
                    metadata={'posts_count': succeeded_count},
                    progress_percentage=45,
                )
                logger.info(f"📝 Transcription status created for {analysis_request.id}")
            
            # Status 4: Displaying content
            post_previews = []
            for p in all_posts[:10]:  # Limit to first 10 for preview
                thumbnail_media = p.media.filter(media_type__in=['image', 'video_thumbnail']).first()
                thumbnail = thumbnail_media.source_url if thumbnail_media and thumbnail_media.source_url else None
                
                post_previews.append({
                    'id': str(p.id),
                    'username': p.username,
                    'platform': p.platform.name,
                    'thumbnail': thumbnail,
                    'caption': p.content[:100] + '...' if len(p.content) > 100 else p.content,
                })
            
            create_status(
                analysis_request,
                'displaying_content',
                'Displaying post previews...',
                metadata={'posts': post_previews},
                progress_percentage=60,
            )
            
            # Status 5: Analysing
            create_status(
                analysis_request,
                'analysing',
                'PostBro is analyzing these posts...',
                metadata={
                    'analysis_type': 'ai_insights',
                    'posts_to_analyze': len(all_posts)
                },
                progress_percentage=70,
            )
            
            # Stage 3: Gemini Analysis
            try:
                analysis_results, successful_analyses, failed_analyses = analyze_posts_with_gemini(
                    analysis_request,
                    all_posts,
                    media_bytes_by_post_id,
                )
                
                # Store analysis results
                analysis_request.results = {
                    'analyses': analysis_results,
                    'total_posts': len(all_posts),
                    'analyzed_posts': len(analysis_results),
                }
                analysis_request.save(update_fields=['results'])
                
                logger.info(f"✅ Completed AI analysis for {len(analysis_results)}/{len(all_posts)} posts")
            except Exception as e:
                handle_analysis_error(
                    analysis_request,
                    error_stage=PostAnalysisRequest.ErrorStage.GEMINI_ANALYSIS,
                    exception=e,
                    failed_at_stage='collecting_media',
                    metadata={'posts_count': len(all_posts)}
                )
                return {
                    'success': False,
                    'error': 'Gemini analysis failed',
                    'posts_fetched': len(all_posts),
                }
            
            # Status 6: Complete
            duration = (timezone.now() - start_time).total_seconds()
            create_status(
                analysis_request,
                'analysis_complete',
                'Analysis complete!',
                metadata={
                    'posts_analyzed': len(all_posts),
                    'duration_seconds': duration,
                    'api_calls_made': total_api_calls,
                },
                progress_percentage=100,
                api_calls_made=total_api_calls,
                cost_estimate=cost_estimate,
            )
            
            # Update analysis request status to completed with business metrics
            analysis_request.status = PostAnalysisRequest.Status.COMPLETED
            analysis_request.completed_at = timezone.now()
            analysis_request.duration_seconds = duration
            analysis_request.total_api_calls = total_api_calls
            analysis_request.posts_processed = succeeded_count
            analysis_request.save(update_fields=['status', 'completed_at', 'duration_seconds', 'total_api_calls', 'posts_processed'])
            logger.info(f"✅ Updated analysis {analysis_request.id} status to completed "
                       f"(duration: {duration:.2f}s, API calls: {total_api_calls}, posts: {succeeded_count})")
            
            # Increment usage only after successful completion (not on retries)
            # Retries should not increment usage as they're the same analysis being retried
            if analysis_request.retry_count == 0:
                increment_usage(analysis_request.user, analysis_request.platform, 'url_lookups')
                logger.info(f"📊 [Analysis] Incremented usage for user {analysis_request.user.id} after successful completion")
            else:
                logger.info(f"📊 [Analysis] Skipping usage increment for retry (retry_count: {analysis_request.retry_count})")
            
            logger.info(
                f"Completed analysis request {analysis_request_id}: "
                f"{succeeded_count} posts saved, {len(failed_urls)} failed"
            )
            
            return {
                'success': True,
                'posts_saved': succeeded_count,
                'posts_failed': len(failed_urls),
                'post_ids': [str(p.id) for p in all_posts],
                'failed_urls': failed_urls,
                'duration_seconds': duration,
                'api_calls_made': total_api_calls,
                'cost_estimate': float(cost_estimate),
            }
        else:
            # Complete failure
            create_error_status(
                analysis_request,
                'ALL_FAILED',
                'Failed to fetch any posts',
                retryable=True,
                actionable_message='Please check your URLs and try again',
                metadata={'failed_urls': failed_urls}
            )
            analysis_request.status = 'failed'
            analysis_request.save()
            return {
                'success': False,
                'error': 'All posts failed to scrape',
                'failed_urls': failed_urls
            }
        
    except PostAnalysisRequest.DoesNotExist:
        logger.error(
            f"❌ [Analysis] Analysis request not found: analysis_request_id={analysis_request_id_str}",
            extra={'analysis_request_id': analysis_request_id_str}
        )
        return {
            'success': False,
            'error': 'Analysis request not found'
        }
    
    except ValueError as e:
        # Validation errors - don't retry
        logger.error(
            f"❌ [Analysis] Validation error for analysis_request_id={analysis_request_id_str}: {str(e)}",
            extra={'analysis_request_id': analysis_request_id_str}
        )
        try:
            analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
            create_error_status(
                analysis_request,
                'VALIDATION_ERROR',
                str(e),
                retryable=False,
                actionable_message='Please check your input and try again',
            )
        except:
            pass
        return {
            'success': False,
            'error': str(e)
        }
    
    except Exception as e:
        # Unexpected error - use handle_analysis_error for proper tracking
        try:
            analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
            # Determine error stage based on what we know
            error_stage = PostAnalysisRequest.ErrorStage.SOCIAL_COLLECTION  # Default
            failed_at_stage = 'request_created'
            
            # Try to determine stage from status history
            last_status = analysis_request.status_history.filter(is_error=False).last()
            if last_status:
                if last_status.stage in ['social_data_fetched', 'collecting_media']:
                    error_stage = PostAnalysisRequest.ErrorStage.MEDIA_EXTRACTION
                    failed_at_stage = 'social_data_fetched'
                elif last_status.stage == 'analysing':
                    error_stage = PostAnalysisRequest.ErrorStage.GEMINI_ANALYSIS
                    failed_at_stage = 'collecting_media'
            
            handle_analysis_error(
                analysis_request,
                error_stage=error_stage,
                exception=e,
                failed_at_stage=failed_at_stage,
                metadata={'unexpected_error': True}
            )
        except Exception as inner_e:
            logger.exception(
                f"❌ [Analysis] Unexpected error processing analysis_request_id={analysis_request_id_str}: {str(e)}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
            logger.error(
                f"❌ [Analysis] Also failed to handle error: {str(inner_e)}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
        
        return {
            'success': False,
            'error': str(e),
        }


        create_status(
            analysis_request,
            'fetching_posts',
            'Fetching posts...',
            metadata={'urls_count': len(analysis_request.post_urls)},
            progress_percentage=10,
            api_calls_made=0
        )
        
        # Parse URLs and group by platform
        urls_by_platform: Dict[str, List[str]] = {}
        invalid_urls = []
        
        for url in analysis_request.post_urls:
            platform = detect_platform_from_url(url)
            if not platform:
                logger.warning(f"Invalid URL format: {url}")
                invalid_urls.append(url)
                create_error_status(
                    analysis_request,
                    'INVALID_URL',
                    f'Invalid URL format: {url}',
                    retryable=False,
                    actionable_message='Please check the URL format and try again',
                    metadata={'url': url}
                )
                continue
            
            if platform not in urls_by_platform:
                urls_by_platform[platform] = []
            urls_by_platform[platform].append(url)
        
        if not urls_by_platform:
            raise ValueError("No valid URLs found. All URLs were invalid.")
        
        # Store media bytes separately (not on Post objects, so they survive refresh_from_db())
        # Structure: {post_id: {media_id: [{'bytes': bytes, 'mime_type': str, 'media_type': str}]}}
        media_bytes_by_post_id = {}
        
        # Stage 1: Social Media Collection
        try:
            all_posts, failed_urls, total_api_calls, fast_path_post_ids = collect_social_posts(
                analysis_request,
                urls_by_platform,
                media_bytes_by_post_id,
            )
        except Exception as e:
            handle_analysis_error(
                analysis_request,
                error_stage=PostAnalysisRequest.ErrorStage.SOCIAL_COLLECTION,
                exception=e,
                failed_at_stage='fetching_posts',
                metadata={'urls_by_platform': list(urls_by_platform.keys())}
            )
            return {
                'success': False,
                'error': 'Social media collection failed',
            }
        
        # Calculate cost estimate
        cost_estimate = estimate_cost(
            platform=analysis_request.platform,
            api_calls=total_api_calls,
            operation_type='scraping'
        )
        
        # Verify and re-link all posts
        verify_and_relink_posts(analysis_request, all_posts)
        
        # Verify all media uploads completed
        for post in all_posts:
            post.refresh_from_db()
            pending_media = post.media.filter(
                media_type__in=['image', 'video_thumbnail'],
                supabase_url__isnull=True,
                uploaded_to_supabase=False
            )
            if pending_media.exists():
                logger.warning(f"Post {post.id} has {pending_media.count()} media items still uploading")
        
        # Status 3: Social data fetched (or partial success)
        succeeded_count = len(all_posts)
        
        if failed_urls and succeeded_count > 0:
            # Partial success
            create_partial_success_status(
                analysis_request,
                succeeded=succeeded_count,
                failed=len(failed_urls),
                total=len(analysis_request.post_urls),
                failed_urls=failed_urls,
                succeeded_post_ids=[str(p.id) for p in all_posts]
            )
        elif succeeded_count > 0:
            # Extract username from first post for sidebar display
            display_name = None
            if all_posts:
                first_post = all_posts[0]
                first_post.refresh_from_db()
                if first_post and first_post.username:
                    display_name = first_post.username
                    logger.info(f"✅ Extracted display_name from post: {display_name}")
            
            # Store display_name
            if display_name:
                analysis_request.display_name = display_name
                analysis_request.save(update_fields=['display_name'])
                logger.info(f"✅ Saved display_name '{display_name}' to analysis {analysis_request.id}")
            
            # Full success - CREATE STATUS IMMEDIATELY
            logger.info(f"📤 Creating social_data_fetched status for {analysis_request.id} with username: {display_name}")
            create_status(
                analysis_request,
                'social_data_fetched',
                f'Fetched {succeeded_count} posts successfully',
                metadata={
                    'posts_count': succeeded_count,
                    'post_ids': [str(p.id) for p in all_posts],
                    'platforms': list(urls_by_platform.keys()),
                    'username': display_name,
                },
                progress_percentage=30,
                api_calls_made=total_api_calls,
                cost_estimate=cost_estimate,
            )
            logger.info(f"✅ social_data_fetched status created and sent to frontend for {analysis_request.id}")
            
            # Status: Collecting media
            create_status(
                analysis_request,
                'collecting_media',
                'Collecting media and extracting frames...',
                metadata={
                    'posts_count': succeeded_count,
                    'platforms': list(urls_by_platform.keys()),
                },
                progress_percentage=40,
            )
            
            # Stage 2: Media Extraction
            try:
                extract_media_for_analysis(
                    analysis_request,
                    all_posts,
                    media_bytes_by_post_id,
                    fast_path_post_ids,
                )
            except Exception as e:
                handle_analysis_error(
                    analysis_request,
                    error_stage=PostAnalysisRequest.ErrorStage.MEDIA_EXTRACTION,
                    exception=e,
                    failed_at_stage='social_data_fetched',
                    metadata={'posts_count': len(all_posts), 'platform': analysis_request.platform}
                )
                return {
                    'success': False,
                    'error': 'Media extraction failed',
                    'posts_fetched': len(all_posts)
                }
            
            # Check transcription status
            has_videos = check_transcription_status(all_posts)
            if has_videos:
                create_status(
                    analysis_request,
                    'transcribing',
                    'Transcribing video audio...',
                    metadata={'posts_count': succeeded_count},
                    progress_percentage=45,
                )
                logger.info(f"📝 Transcription status created for {analysis_request.id}")
            
            # Status 4: Displaying content
            post_previews = []
            for p in all_posts[:10]:  # Limit to first 10 for preview
                thumbnail_media = p.media.filter(media_type__in=['image', 'video_thumbnail']).first()
                thumbnail = thumbnail_media.source_url if thumbnail_media and thumbnail_media.source_url else None
                
                post_previews.append({
                    'id': str(p.id),
                    'username': p.username,
                    'platform': p.platform.name,
                    'thumbnail': thumbnail,
                    'caption': p.content[:100] + '...' if len(p.content) > 100 else p.content,
                })
            
            create_status(
                analysis_request,
                'displaying_content',
                'Displaying post previews...',
                metadata={'posts': post_previews},
                progress_percentage=60,
            )
            
            # Status 5: Analysing
            create_status(
                analysis_request,
                'analysing',
                'PostBro is analyzing these posts...',
                metadata={
                    'analysis_type': 'ai_insights',
                    'posts_to_analyze': len(all_posts)
                },
                progress_percentage=70,
            )
            
            # Stage 3: Gemini Analysis
            try:
                analysis_results, successful_analyses, failed_analyses = analyze_posts_with_gemini(
                    analysis_request,
                    all_posts,
                    media_bytes_by_post_id,
                )
                
                # Store analysis results
                analysis_request.results = {
                    'analyses': analysis_results,
                    'total_posts': len(all_posts),
                    'analyzed_posts': len(analysis_results),
                }
                analysis_request.save(update_fields=['results'])
                
                logger.info(f"✅ Completed AI analysis for {len(analysis_results)}/{len(all_posts)} posts")
            except Exception as e:
                handle_analysis_error(
                    analysis_request,
                    error_stage=PostAnalysisRequest.ErrorStage.GEMINI_ANALYSIS,
                    exception=e,
                    failed_at_stage='collecting_media',
                    metadata={'posts_count': len(all_posts)}
                )
                return {
                    'success': False,
                    'error': 'Gemini analysis failed',
                    'posts_fetched': len(all_posts),
                }
            
            # Status 6: Complete
            duration = (timezone.now() - start_time).total_seconds()
            create_status(
                analysis_request,
                'analysis_complete',
                'Analysis complete!',
                metadata={
                    'posts_analyzed': len(all_posts),
                    'duration_seconds': duration,
                    'api_calls_made': total_api_calls,
                },
                progress_percentage=100,
                api_calls_made=total_api_calls,
                cost_estimate=cost_estimate,
            )
            
            # Update analysis request status to completed with business metrics
            analysis_request.status = PostAnalysisRequest.Status.COMPLETED
            analysis_request.completed_at = timezone.now()
            analysis_request.duration_seconds = duration
            analysis_request.total_api_calls = total_api_calls
            analysis_request.posts_processed = succeeded_count
            analysis_request.save(update_fields=['status', 'completed_at', 'duration_seconds', 'total_api_calls', 'posts_processed'])
            logger.info(f"✅ Updated analysis {analysis_request.id} status to completed "
                       f"(duration: {duration:.2f}s, API calls: {total_api_calls}, posts: {succeeded_count})")
            
            # Increment usage only after successful completion (not on retries)
            # Retries should not increment usage as they're the same analysis being retried
            if analysis_request.retry_count == 0:
                increment_usage(analysis_request.user, analysis_request.platform, 'url_lookups')
                logger.info(f"📊 [Analysis] Incremented usage for user {analysis_request.user.id} after successful completion")
            else:
                logger.info(f"📊 [Analysis] Skipping usage increment for retry (retry_count: {analysis_request.retry_count})")
            
            logger.info(
                f"Completed analysis request {analysis_request_id}: "
                f"{succeeded_count} posts saved, {len(failed_urls)} failed"
            )
            
            return {
                'success': True,
                'posts_saved': succeeded_count,
                'posts_failed': len(failed_urls),
                'post_ids': [str(p.id) for p in all_posts],
                'failed_urls': failed_urls,
                'duration_seconds': duration,
                'api_calls_made': total_api_calls,
                'cost_estimate': float(cost_estimate),
            }
        else:
            # Complete failure
            create_error_status(
                analysis_request,
                'ALL_FAILED',
                'Failed to fetch any posts',
                retryable=True,
                actionable_message='Please check your URLs and try again',
                metadata={'failed_urls': failed_urls}
            )
            analysis_request.status = 'failed'
            analysis_request.save()
            return {
                'success': False,
                'error': 'All posts failed to scrape',
                'failed_urls': failed_urls
            }
        
    except PostAnalysisRequest.DoesNotExist:
        logger.error(
            f"❌ [Analysis] Analysis request not found: analysis_request_id={analysis_request_id_str}",
            extra={'analysis_request_id': analysis_request_id_str}
        )
        return {
            'success': False,
            'error': 'Analysis request not found'
        }
    
    except ValueError as e:
        # Validation errors - don't retry
        logger.error(
            f"❌ [Analysis] Validation error for analysis_request_id={analysis_request_id_str}: {str(e)}",
            extra={'analysis_request_id': analysis_request_id_str}
        )
        try:
            analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
            create_error_status(
                analysis_request,
                'VALIDATION_ERROR',
                str(e),
                retryable=False,
                actionable_message='Please check your input and try again',
            )
        except:
            pass
        return {
            'success': False,
            'error': str(e)
        }
    
    except Exception as e:
        # Unexpected error - use handle_analysis_error for proper tracking
        try:
            analysis_request = PostAnalysisRequest.objects.get(id=analysis_request_id)
            # Determine error stage based on what we know
            error_stage = PostAnalysisRequest.ErrorStage.SOCIAL_COLLECTION  # Default
            failed_at_stage = 'request_created'
            
            # Try to determine stage from status history
            last_status = analysis_request.status_history.filter(is_error=False).last()
            if last_status:
                if last_status.stage in ['social_data_fetched', 'collecting_media']:
                    error_stage = PostAnalysisRequest.ErrorStage.MEDIA_EXTRACTION
                    failed_at_stage = 'social_data_fetched'
                elif last_status.stage == 'analysing':
                    error_stage = PostAnalysisRequest.ErrorStage.GEMINI_ANALYSIS
                    failed_at_stage = 'collecting_media'
            
            handle_analysis_error(
                analysis_request,
                error_stage=error_stage,
                exception=e,
                failed_at_stage=failed_at_stage,
                metadata={'unexpected_error': True}
            )
        except Exception as inner_e:
            logger.exception(
                f"❌ [Analysis] Unexpected error processing analysis_request_id={analysis_request_id_str}: {str(e)}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
            logger.error(
                f"❌ [Analysis] Also failed to handle error: {str(inner_e)}",
                extra={'analysis_request_id': analysis_request_id_str}
            )
        
        return {
            'success': False,
            'error': str(e),
        }

