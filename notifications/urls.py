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
    
    # Mark notification as read (generic)
    path('mark-read/', 
         views.MarkNotificationReadView.as_view(), 
         name='mark-notification-read'),
    
    # Personnel-specific notification endpoints (must come before generic mark-all-read)
    path('<int:notification_id>/mark-read/', 
         views.PersonnelMarkNotificationReadView.as_view(), 
         name='personnel-mark-notification-read'),
    
    path('mark-all-read/', 
         views.PersonnelMarkAllNotificationsReadView.as_view(), 
         name='personnel-mark-all-read'),
    
    # Check for new notifications (polling)
    path('check-new/', 
         views.PersonnelCheckNewNotificationsView.as_view(), 
         name='check-new-notifications'),
    
    # List notifications (for modal refresh)
    path('list/', 
         views.PersonnelListNotificationsView.as_view(), 
         name='list-notifications'),
    
    # Generic mark all notifications as read (for mobile app with explicit user_type)
    path('mobile/mark-all-read/', 
         views.MarkAllNotificationsReadView.as_view(), 
         name='mark-all-notifications-read'),
    
    # Webhook for Supabase triggers to send push notifications
    path('send-push/', 
         views.SendPushNotificationWebhookView.as_view(), 
         name='send-push-webhook'),
]
