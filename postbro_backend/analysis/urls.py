from django.urls import path
from . import views

app_name = 'analysis'

urlpatterns = [
    # Main analysis endpoint
    path('analyze/', views.analyze_posts, name='analyze_posts'),
    
    # Get all analysis requests for the current user
    path('requests/', views.get_analysis_requests, name='get_analysis_requests'),
    
    # Get a specific analysis request by ID
    path('requests/<uuid:request_id>/', views.get_analysis_request, name='get_analysis_request'),
    
    # Retry a failed analysis request
    path('requests/<uuid:request_id>/retry/', views.retry_analysis, name='retry_analysis'),
    
    # Chat endpoints
    # POST to create, GET to list (same URL, different methods handled by view)
    path('chat/sessions/', views.create_chat_session, name='create_chat_session'),  # POST
    path('chat/sessions/list/', views.list_chat_sessions, name='list_chat_sessions'),  # GET (separate path to avoid conflict)
    path('chat/sessions/<uuid:session_id>/messages/', views.chat_session_messages, name='chat_session_messages'),  # POST (non-streaming)
    path('chat/sessions/<uuid:session_id>/messages/stream/', views.chat_session_messages_stream, name='chat_session_messages_stream'),  # POST (streaming)
    path('chat/sessions/<uuid:session_id>/', views.get_chat_session, name='get_chat_session'),  # GET
    
    # Notes endpoints
    path('notes/', views.list_analysis_notes, name='list_analysis_notes'),  # GET - list all user notes
    path('notes/<uuid:post_analysis_id>/', views.get_analysis_note, name='get_analysis_note'),  # GET - get note for specific analysis
    path('notes/save/', views.create_or_update_analysis_note, name='create_or_update_analysis_note'),  # POST/PUT - create/update note
    path('notes/<uuid:note_id>/delete/', views.delete_analysis_note, name='delete_analysis_note'),  # DELETE - delete note
] 
