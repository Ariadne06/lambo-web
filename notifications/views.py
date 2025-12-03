"""
API views for notification endpoints.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .repo import (
    register_push_device,
    get_user_notifications,
    get_unread_count,
    mark_notification_read,
    mark_all_notifications_read
)


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
