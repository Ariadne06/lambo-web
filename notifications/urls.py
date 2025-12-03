"""
URL Configuration for Notifications API.
"""
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    # Register push token
    path('register-push-token/', 
         views.RegisterPushTokenView.as_view(), 
         name='register-push-token'),
    
    # Get notifications
    path('get-notifications/', 
         views.GetNotificationsView.as_view(), 
         name='get-notifications'),
    
    # Mark notification as read
    path('mark-read/', 
         views.MarkNotificationReadView.as_view(), 
         name='mark-notification-read'),
    
    # Mark all notifications as read
    path('mark-all-read/', 
         views.MarkAllNotificationsReadView.as_view(), 
         name='mark-all-notifications-read'),
    
    # Webhook for Supabase triggers to send push notifications
    path('send-push/', 
         views.SendPushNotificationWebhookView.as_view(), 
         name='send-push-webhook'),
]
