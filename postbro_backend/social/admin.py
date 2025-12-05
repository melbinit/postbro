from django.contrib import admin
from .models import Platform, Post, PostMedia, PostComment, UserPostActivity

@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at')
    search_fields = ('name',)
    ordering = ('name',)

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ('username', 'platform', 'engagement_score', 'posted_at', 'collected_at')
    list_filter = ('platform', 'posted_at', 'collected_at')
    search_fields = ('username', 'content', 'url')
    ordering = ('-posted_at',)
    raw_id_fields = ('platform',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(PostMedia)
class PostMediaAdmin(admin.ModelAdmin):
    list_display = ('post', 'media_type', 'source_url', 'created_at')
    list_filter = ('media_type', 'created_at')
    search_fields = ('post__username', 'source_url')
    ordering = ('-created_at',)
    raw_id_fields = ('post',)

@admin.register(PostComment)
class PostCommentAdmin(admin.ModelAdmin):
    list_display = ('post', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('post__username', 'comment_data')
    ordering = ('-created_at',)
    raw_id_fields = ('post',)

@admin.register(UserPostActivity)
class UserPostActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'post', 'source', 'viewed_at')
    list_filter = ('source', 'viewed_at', 'created_at')
    search_fields = ('user__email', 'post__username')
    ordering = ('-viewed_at',)
    raw_id_fields = ('user', 'post')
