from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Subscription management
    path('subscribe/', views.subscribe_to_plan, name='subscribe_to_plan'),
    path('upgrade/', views.upgrade_plan, name='upgrade_plan'),
    path('cancel/', views.cancel_subscription, name='cancel_subscription'),
    path('subscription/history/', views.subscription_history, name='subscription_history'),
    
    # Payment provider webhooks
    path('webhook/dodo/', views.dodo_webhook, name='dodo_webhook'),
    
    # Success/cancel pages
    path('subscription/success/', views.subscription_success, name='subscription_success'),
    path('subscription/cancel/', views.subscription_cancel, name='subscription_cancel'),
]
