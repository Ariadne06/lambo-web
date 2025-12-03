"""
Notification service for sending push notifications.
Handles all push notification logic using Expo Push Notification Service with FCM.
"""
import os
import json
import logging
from pathlib import Path
from exponent_server_sdk import (
    DeviceNotRegisteredError,
    PushClient,
    PushMessage,
    PushTicketError,
    PushServerError
)
from .repo import (
    create_notification,
    get_user_push_tokens,
    get_all_resident_push_tokens,
    remove_push_token
)

logger = logging.getLogger(__name__)

# Load FCM credentials for Expo
BASE_DIR = Path(__file__).resolve().parent.parent
FIREBASE_CREDENTIALS_PATH = os.path.join(BASE_DIR, 'firebase-credentials.json')

# Initialize Expo Push Client with extra headers for FCM
push_client = PushClient()

try:
    with open(FIREBASE_CREDENTIALS_PATH, 'r') as f:
        firebase_config = json.load(f)
        logger.info("Firebase credentials loaded for Expo push service")
except Exception as e:
    logger.warning(f"Could not load Firebase credentials: {e}")


class NotificationService:
    """Service for sending push notifications using Expo."""
    
    @staticmethod
    def send_to_resident(
        resident_id: int,
        title: str,
        body: str,
        deep_link: str = None,
        data: dict = None
    ) -> bool:
        """Send notification to a specific resident."""
        return NotificationService._send_notification(
            user_type='RESIDENT',
            resident_id=resident_id,
            personnel_id=None,
            title=title,
            body=body,
            deep_link=deep_link,
            data=data
        )
    
    @staticmethod
    def send_to_personnel(
        personnel_id: int,
        title: str,
        body: str,
        deep_link: str = None,
        data: dict = None
    ) -> bool:
        """Send notification to a specific personnel."""
        return NotificationService._send_notification(
            user_type='PERSONNEL',
            resident_id=None,
            personnel_id=personnel_id,
            title=title,
            body=body,
            deep_link=deep_link,
            data=data
        )
    
    @staticmethod
    def send_to_all_residents(
        title: str,
        body: str,
        deep_link: str = None,
        data: dict = None
    ) -> bool:
        """Send notification to ALL residents (broadcast)."""
        try:
            # Get all resident push tokens
            tokens = get_all_resident_push_tokens()
            
            if not tokens:
                logger.warning("No resident push tokens found")
                return False
            
            messages = []
            for token_data in tokens:
                # Create notification in database
                create_notification(
                    user_type='RESIDENT',
                    resident_id=token_data['resident_id'],
                    personnel_id=None,
                    title=title,
                    body=body,
                    deep_link=deep_link
                )
                
                # Prepare push message
                notification_data = data or {}
                notification_data.update({
                    'deep_link': deep_link,
                    'type': 'broadcast'
                })
                
                messages.append(
                    PushMessage(
                        to=token_data['expo_push_token'],
                        title=title,
                        body=body,
                        data=notification_data,
                        sound='default',
                        badge=1,
                        channel_id='default'
                    )
                )
            
            # Send in batches of 100
            for i in range(0, len(messages), 100):
                batch = messages[i:i+100]
                try:
                    push_client.publish_multiple(batch)
                    logger.info(f"Sent batch of {len(batch)} notifications")
                except Exception as e:
                    logger.error(f"Batch send failed: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to send broadcast: {e}")
            return False
    
    @staticmethod
    def _send_notification(
        user_type: str,
        resident_id: int = None,
        personnel_id: int = None,
        title: str = None,
        body: str = None,
        deep_link: str = None,
        data: dict = None
    ) -> bool:
        """Internal method to send notification using Expo Push Service."""
        try:
            # Create notification in database
            notification_id = create_notification(
                user_type=user_type,
                resident_id=resident_id,
                personnel_id=personnel_id,
                title=title,
                body=body,
                deep_link=deep_link
            )
            
            if not notification_id:
                logger.error("Failed to create notification in database")
                return False
            
            # Get user's push tokens
            tokens = get_user_push_tokens(
                user_type=user_type,
                resident_id=resident_id,
                personnel_id=personnel_id
            )
            
            if not tokens:
                logger.warning(f"No push tokens for {user_type} - resident_id:{resident_id} personnel_id:{personnel_id}")
                # Still return True since notification was saved
                return True
            
            # Send to all user's devices using Expo Push Service
            sent_count = 0
            for token_data in tokens:
                notification_data = data or {}
                notification_data.update({
                    'deep_link': deep_link,
                    'resident_id': resident_id,
                    'personnel_id': personnel_id,
                    'notification_id': notification_id
                })
                
                try:
                    response = push_client.publish(
                        PushMessage(
                            to=token_data['expo_push_token'],
                            title=title,
                            body=body,
                            data=notification_data,
                            sound='default',
                            badge=1,
                            channel_id='default'
                        )
                    )
                    response.validate_response()
                    sent_count += 1
                    logger.info(f"Sent notification to {token_data['expo_push_token']}")
                    
                except DeviceNotRegisteredError:
                    logger.warning(f"Removing invalid token: {token_data['expo_push_token']}")
                    remove_push_token(token_data['expo_push_token'])
                    
                except PushTicketError as exc:
                    logger.error(f"Push ticket error: {exc}")
                    
                except PushServerError as exc:
                    logger.error(f"Push server error: {exc}")
            
            logger.info(f"Sent notification to {sent_count}/{len(tokens)} devices")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            import traceback
            traceback.print_exc()
            return False


# ========================================
# Convenience Functions
# ========================================

def notify_certificate_approved(resident_id: int, document_type_name: str, application_id: int):
    """Send notification when certificate is approved."""
    NotificationService.send_to_resident(
        resident_id=resident_id,
        title="Certificate Approved ✅",
        body=f"Your {document_type_name} is ready for pickup!",
        deep_link=f"/(tabs)/documents/{application_id}",
        data={'type': 'certificate_approved', 'application_id': application_id}
    )


def notify_certificate_rejected(resident_id: int, document_type_name: str, reason: str):
    """Send notification when certificate is rejected."""
    NotificationService.send_to_resident(
        resident_id=resident_id,
        title="Certificate Request Declined ❌",
        body=f"Your {document_type_name} was declined. Reason: {reason}",
        deep_link="/(tabs)/documents",
        data={'type': 'certificate_rejected'}
    )


def notify_new_announcement(title: str, content: str):
    """Send notification to all residents about new announcement."""
    NotificationService.send_to_all_residents(
        title=f"📢 {title}",
        body=content[:100] + "..." if len(content) > 100 else content,
        deep_link="/(tabs)/announcement",
        data={'type': 'new_announcement'}
    )


def notify_payment_confirmed(resident_id: int, amount: float, or_number: str):
    """Send notification when payment is confirmed."""
    NotificationService.send_to_resident(
        resident_id=resident_id,
        title="Payment Confirmed 💰",
        body=f"Your payment of ₱{amount:.2f} (OR #{or_number}) has been confirmed.",
        deep_link="/(tabs)/transactions",
        data={'type': 'payment_confirmed', 'or_number': or_number}
    )


def notify_account_verified(resident_id: int):
    """Send notification when resident account is verified."""
    NotificationService.send_to_resident(
        resident_id=resident_id,
        title="Account Verified ✅",
        body="Your account has been verified! You can now access all features.",
        deep_link="/(tabs)/profile/profile",
        data={'type': 'account_verified'}
    )


def notify_household_visit_scheduled(personnel_id: int, household_number: str, scheduled_date: str):
    """Send notification to BHW about scheduled household visit."""
    NotificationService.send_to_personnel(
        personnel_id=personnel_id,
        title="Household Visit Scheduled 🏠",
        body=f"Visit scheduled for Household {household_number} on {scheduled_date}",
        deep_link="/(bhw)/household",
        data={'type': 'household_visit', 'household_number': household_number}
    )
