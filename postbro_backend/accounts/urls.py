from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Authentication endpoints (Supabase handles email verification)
    path('signup/', views.signup, name='signup'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('reset-password/', views.reset_password, name='reset_password'),
    
    # Profile endpoints
    path('me/', views.profile, name='profile'),
    
    # Subscription endpoints
    path('subscription/', views.current_subscription, name='current_subscription'),
    
    # Plans endpoint (public)
    path('plans/', views.plans_list, name='plans_list'),
    
    # Usage endpoints
    path('usage/', views.usage_stats, name='usage_stats'),
    path('usage/limits/', views.usage_limits, name='usage_limits'),
    path('usage/history/', views.usage_history, name='usage_history'),
]

