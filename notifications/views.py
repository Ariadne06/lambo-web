"""
API views for notification endpoints.
"""
import os
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from .repo import (
    register_push_device,
    get_user_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read,
    get_user_push_tokens
)
from .service import NotificationService


class RegisterPushTokenView(APIView):
    """
    Register or update Expo push token.
    
    POST /notifications_api/register-push-token/
    {
        "user_type": "RESIDENT",
        "resident_id": 123,
        "expo_push_token": "ExponentPushToken[xxx]",
        "platform": "android"
    }
    """
    def post(self, request):
        try:
            user_type = request.data.get('user_type')
            resident_id = request.data.get('resident_id')
            personnel_id = request.data.get('personnel_id')
            expo_push_token = request.data.get('expo_push_token')
            platform = request.data.get('platform')
            
            if not user_type or not expo_push_token:
                return Response({
                    'success': False,
                    'error': 'user_type and expo_push_token required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            result = register_push_device(
                user_type=user_type,
                resident_id=resident_id,
                personnel_id=personnel_id,
                expo_push_token=expo_push_token,
                platform=platform
            )
            
            return Response({
                'success': True,
                'message': result['message'],
                'device_id': result['push_device_id']
            }, status=status.HTTP_201_CREATED)
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class GetNotificationsView(APIView):
    """
    Get user notifications.
    
    GET /notifications_api/notifications/?user_type=RESIDENT&resident_id=123
    GET /notifications_api/notifications/?user_type=PERSONNEL&personnel_id=456
    """
    def get(self, request):
        try:
            user_type = request.query_params.get('user_type')
            resident_id = request.query_params.get('resident_id')
            personnel_id = request.query_params.get('personnel_id')
            limit = int(request.query_params.get('limit', 50))
            
            if not user_type:
                return Response({
                    'success': False,
                    'error': 'user_type required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            notifications = get_user_notifications(
                user_type=user_type,
                resident_id=int(resident_id) if resident_id else None,
                personnel_id=int(personnel_id) if personnel_id else None,
                limit=limit
            )
            
            unread = get_unread_count(
                user_type=user_type,
                resident_id=int(resident_id) if resident_id else None,
                personnel_id=int(personnel_id) if personnel_id else None
            )
            
            return Response({
                'success': True,
                'data': notifications,
                'unread_count': unread
            })
            
        except ValueError as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkNotificationReadView(APIView):
    """
    Mark notification as read.
    
    POST /notifications_api/notifications/mark-read/
    { "notification_id": 123 }
    """
    def post(self, request):
        try:
            notification_id = request.data.get('notification_id')
            
            if not notification_id:
                return Response({
                    'success': False,
                    'error': 'notification_id required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            success = mark_notification_read(int(notification_id))
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Notification marked as read'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Notification not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class MarkAllNotificationsReadView(APIView):
    """
    Mark all notifications as read.
    
    POST /notifications_api/notifications/mark-all-read/
    { "user_type": "RESIDENT", "resident_id": 123 }
    """
    def post(self, request):
        try:
            user_type = request.data.get('user_type')
            resident_id = request.data.get('resident_id')
            personnel_id = request.data.get('personnel_id')
            
            if not user_type:
                return Response({
                    'success': False,
                    'error': 'user_type required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            count = mark_all_notifications_read(
                user_type=user_type,
                resident_id=int(resident_id) if resident_id else None,
                personnel_id=int(personnel_id) if personnel_id else None
            )
            
            return Response({
                'success': True,
                'message': f'{count} notifications marked as read',
                'count': count
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@method_decorator(csrf_exempt, name='dispatch')
class SendPushNotificationWebhookView(APIView):
    """
    Webhook endpoint for Supabase triggers to send push notifications.
    
    POST /notifications_api/send-push/
    Headers: X-Cron-Secret: <secret-token>
    {
        "notification_id": 123,
        "user_type_id": 1,
        "user_id": 456,
        "title": "Notification Title",
        "body": "Notification body text",
        "deep_link": "/(tabs)/documents/123"
    }
    """
    def post(self, request):
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # Log that webhook was called
            logger.info(f"Push notification webhook called with data: {request.data}")
            
            # Verify secret token
            secret_token = request.headers.get('X-Cron-Secret')
            expected_token = os.environ.get('CRON_SECRET_TOKEN', 'your-secret-token-here')
            
            logger.info(f"Secret token received: {secret_token[:10]}... (truncated)")
            
            if secret_token != expected_token:
                logger.warning(f"Unauthorized webhook attempt - invalid secret token")
                return Response({
                    'success': False,
                    'error': 'Unauthorized'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            # Extract data from webhook
            user_type_id = request.data.get('user_type_id')
            user_id = request.data.get('user_id')
            title = request.data.get('title')
            body = request.data.get('body')
            deep_link = request.data.get('deep_link')
            
            if not all([user_type_id, user_id, title, body]):
                return Response({
                    'success': False,
                    'error': 'Missing required fields'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Determine user type name from ID
            from django.db import connection as db_connection
            with db_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT type_name FROM user_type WHERE user_type_id = %s",
                    (user_type_id,)
                )
                result = cursor.fetchone()
            
            if not result:
                return Response({
                    'success': False,
                    'error': 'Invalid user_type_id'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            user_type = result[0].upper()
            
            # Get push tokens for the user
            tokens = get_user_push_tokens(
                user_type=user_type,
                resident_id=user_id if user_type == 'RESIDENT' else None,
                personnel_id=user_id if user_type == 'PERSONNEL' else None
            )
            
            if not tokens:
                return Response({
                    'success': True,
                    'message': 'No push tokens found for user',
                    'tokens_sent': 0
                })
            
            # Send push notifications
            from exponent_server_sdk import PushClient, PushMessage
            
            push_client = PushClient()
            messages = []
            
            for token_data in tokens:
                token = token_data['expo_push_token']
                
                message = PushMessage(
                    to=token,
                    title=title,
                    body=body,
                    data={'deep_link': deep_link} if deep_link else None,
                    sound='default',
                    priority='high'
                )
                messages.append(message)
            
            # Send in batches
            response = push_client.publish_multiple(messages)
            
            logger.info(f"Successfully sent push notifications to {len(tokens)} device(s)")
            
            return Response({
                'success': True,
                'message': f'Push notifications sent to {len(tokens)} device(s)',
                'tokens_sent': len(tokens)
            })
            
        except Exception as e:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error in push notification webhook: {str(e)}")
            logger.error(traceback.format_exc())
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonnelMarkNotificationReadView(APIView):
    """
    Mark a single personnel notification as read.
    
    POST /api/notifications/<notification_id>/mark-read/
    """
    def post(self, request, notification_id):
        try:
            # Verify user is logged in personnel
            if not hasattr(request, 'session') or not request.session.get('personnel_id'):
                return Response({
                    'success': False,
                    'error': 'Unauthorized'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            personnel_id = request.session.get('personnel_id')
            
            # Verify notification belongs to this personnel
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT personnel_id FROM notification 
                    WHERE notification_id = %s
                """, [notification_id])
                result = cursor.fetchone()
                
                if not result:
                    return Response({
                        'success': False,
                        'error': 'Notification not found'
                    }, status=status.HTTP_404_NOT_FOUND)
                
                if result[0] != personnel_id:
                    return Response({
                        'success': False,
                        'error': 'Unauthorized'
                    }, status=status.HTTP_403_FORBIDDEN)
            
            # Mark as read
            success = mark_notification_read(notification_id)
            
            if success:
                return Response({
                    'success': True,
                    'message': 'Notification marked as read'
                })
            else:
                return Response({
                    'success': False,
                    'error': 'Failed to update notification'
                }, status=status.HTTP_400_BAD_REQUEST)
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonnelMarkAllNotificationsReadView(APIView):
    """
    Mark all personnel notifications as read.
    
    POST /api/notifications/mark-all-read/
    """
    def post(self, request):
        try:
            # Verify user is logged in personnel
            if not hasattr(request, 'session') or not request.session.get('personnel_id'):
                return Response({
                    'success': False,
                    'error': 'Unauthorized'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            personnel_id = request.session.get('personnel_id')
            
            # Mark all as read
            count = mark_all_notifications_read(
                user_type='PERSONNEL',
                personnel_id=personnel_id
            )
            
            return Response({
                'success': True,
                'message': f'{count} notifications marked as read',
                'count': count
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonnelCheckNewNotificationsView(APIView):
    """
    Check for new notifications (polling endpoint).
    
    GET /api/notifications/check-new/
    
    Returns the current unread count for logged-in personnel.
    """
    def get(self, request):
        try:
            # Verify user is logged in personnel
            if not hasattr(request, 'session') or not request.session.get('personnel_id'):
                return Response({
                    'success': False,
                    'error': 'Unauthorized'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            personnel_id = request.session.get('personnel_id')
            
            # Get unread count
            unread_count = get_unread_count(
                user_type='PERSONNEL',
                personnel_id=personnel_id
            )
            
            return Response({
                'success': True,
                'unread_count': unread_count
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PersonnelListNotificationsView(APIView):
    """
    Get list of notifications for personnel (for refreshing modal).
    
    GET /api/notifications/list/
    
    Returns formatted notification list with timesince for logged-in personnel.
    """
    def get(self, request):
        try:
            # Verify user is logged in personnel
            if not hasattr(request, 'session') or not request.session.get('personnel_id'):
                return Response({
                    'success': False,
                    'error': 'Unauthorized'
                }, status=status.HTTP_401_UNAUTHORIZED)
            
            personnel_id = request.session.get('personnel_id')
            role_name = request.session.get('role_name', '')
            
            # Get recent notifications
            notifications = get_user_notifications(
                user_type='PERSONNEL',
                personnel_id=personnel_id,
                limit=10
            )
            
            # Format notifications for template
            from django.utils.timesince import timesince
            formatted_notifications = []
            for notif in notifications:
                # Determine notification type from deep_link
                notif_type = 'general'
                if notif.get('deep_link'):
                    if 'applications' in notif['deep_link']:
                        notif_type = 'forwarded_to_treasurer' if 'Treasurer' in role_name else 'payment_received'
                
                formatted_notifications.append({
                    'id': notif['notification_id'],
                    'title': notif['title'],
                    'message': notif['body'],
                    'link': notif.get('deep_link', ''),
                    'type': notif_type,
                    'is_read': notif['is_read'],
                    'created_at': timesince(notif['created_at']) + ' ago'
                })
            
            return Response({
                'success': True,
                'notifications': formatted_notifications
            })
            
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
