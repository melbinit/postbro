from django.urls import path
from . import views

app_name = 'social'

urlpatterns = [
    path('posts/analysis/<uuid:analysis_request_id>/', views.get_posts_by_analysis_request, name='get_posts_by_analysis_request'),
]


