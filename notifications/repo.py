"""
Database repository for notifications using raw SQL.
All database operations are done through this layer.
"""
from django.db import connection
from typing import List, Dict, Optional, Tuple


def register_push_device(
    user_type: str,
    resident_id: Optional[int] = None,
    personnel_id: Optional[int] = None,
    expo_push_token: str = None,
    platform: Optional[str] = None
) -> Dict:
    """
    Register or update push device token.
    
    Args:
        user_type: 'RESIDENT' or 'PERSONNEL'
        resident_id: Required if RESIDENT
        personnel_id: Required if PERSONNEL
        expo_push_token: Expo push token
        platform: 'ios' or 'android'
    
    Returns:
        Dict with 'push_device_id' and 'message'
    """
    with connection.cursor() as cursor:
        # Get user_type_id
        cursor.execute(
            "SELECT user_type_id FROM user_type WHERE type_name = %s",
            [user_type]
        )
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Invalid user type: {user_type}")
        
        user_type_id = result[0]
        
        # Validate required fields
        if user_type == 'RESIDENT' and not resident_id:
            raise ValueError("resident_id required for RESIDENT")
        if user_type == 'PERSONNEL' and not personnel_id:
            raise ValueError("personnel_id required for PERSONNEL")
        
        # Check if device already exists
        if user_type == 'RESIDENT':
            cursor.execute(
                """
                SELECT push_device_id FROM push_device
                WHERE user_type_id = %s AND resident_id = %s AND expo_push_token = %s
                """,
                [user_type_id, resident_id, expo_push_token]
            )
        else:
            cursor.execute(
                """
                SELECT push_device_id FROM push_device
                WHERE user_type_id = %s AND personnel_id = %s AND expo_push_token = %s
                """,
                [user_type_id, personnel_id, expo_push_token]
            )
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing device
            cursor.execute(
                """
                UPDATE push_device
                SET last_seen = NOW(), platform = COALESCE(%s, platform)
                WHERE push_device_id = %s
                RETURNING push_device_id
                """,
                [platform, existing[0]]
            )
            device_id = cursor.fetchone()[0]
            message = 'Push token updated'
        else:
            # Insert new device
            cursor.execute(
                """
                INSERT INTO push_device (user_type_id, resident_id, personnel_id, platform, expo_push_token, last_seen)
                VALUES (%s, %s, %s, %s, %s, NOW())
                RETURNING push_device_id
                """,
                [user_type_id, resident_id, personnel_id, platform, expo_push_token]
            )
            device_id = cursor.fetchone()[0]
            message = 'Push token registered'
        
        return {
            'push_device_id': device_id,
            'message': message
        }


def get_user_notifications(
    user_type: str,
    resident_id: Optional[int] = None,
    personnel_id: Optional[int] = None,
    limit: int = 50
) -> List[Dict]:
    """
    Get notifications for a user.
    
    Returns:
        List of notification dicts
    """
    with connection.cursor() as cursor:
        # Get user_type_id
        cursor.execute(
            "SELECT user_type_id FROM user_type WHERE type_name = %s",
            [user_type]
        )
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Invalid user type: {user_type}")
        
        user_type_id = result[0]
        
        # Get notifications
        if user_type == 'RESIDENT':
            cursor.execute(
                """
                SELECT notification_id, title, body, deep_link, is_read, created_at
                FROM notification
                WHERE user_type_id = %s AND resident_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                [user_type_id, resident_id, limit]
            )
        else:
            cursor.execute(
                """
                SELECT notification_id, title, body, deep_link, is_read, created_at
                FROM notification
                WHERE user_type_id = %s AND personnel_id = %s
                ORDER BY created_at DESC
                LIMIT %s
                """,
                [user_type_id, personnel_id, limit]
            )
        
        columns = [col[0] for col in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]


def get_unread_count(
    user_type: str,
    resident_id: Optional[int] = None,
    personnel_id: Optional[int] = None
) -> int:
    """Get count of unread notifications."""
    with connection.cursor() as cursor:
        # Get user_type_id
        cursor.execute(
            "SELECT user_type_id FROM user_type WHERE type_name = %s",
            [user_type]
        )
        result = cursor.fetchone()
        if not result:
            return 0
        
        user_type_id = result[0]
        
        if user_type == 'RESIDENT':
            cursor.execute(
                """
                SELECT COUNT(*) FROM notification
                WHERE user_type_id = %s AND resident_id = %s AND is_read = FALSE
                """,
                [user_type_id, resident_id]
            )
        else:
            cursor.execute(
                """
                SELECT COUNT(*) FROM notification
                WHERE user_type_id = %s AND personnel_id = %s AND is_read = FALSE
                """,
                [user_type_id, personnel_id]
            )
        
        result = cursor.fetchone()
        return result[0] if result else 0


def mark_notification_read(notification_id: int) -> bool:
    """Mark a single notification as read."""
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE notification
            SET is_read = TRUE
            WHERE notification_id = %s
            RETURNING notification_id
            """,
            [notification_id]
        )
        result = cursor.fetchone()
        return result is not None


def mark_all_notifications_read(
    user_type: str,
    resident_id: Optional[int] = None,
    personnel_id: Optional[int] = None
) -> int:
    """
    Mark all notifications as read for a user.
    
    Returns:
        Number of notifications updated
    """
    with connection.cursor() as cursor:
        # Get user_type_id
        cursor.execute(
            "SELECT user_type_id FROM user_type WHERE type_name = %s",
            [user_type]
        )
        result = cursor.fetchone()
        if not result:
            return 0
        
        user_type_id = result[0]
        
        if user_type == 'RESIDENT':
            cursor.execute(
                """
                UPDATE notification
                SET is_read = TRUE
                WHERE user_type_id = %s AND resident_id = %s AND is_read = FALSE
                """,
                [user_type_id, resident_id]
            )
        else:
            cursor.execute(
                """
                UPDATE notification
                SET is_read = TRUE
                WHERE user_type_id = %s AND personnel_id = %s AND is_read = FALSE
                """,
                [user_type_id, personnel_id]
            )
        
        return cursor.rowcount


def create_notification(
    user_type: str,
    resident_id: Optional[int] = None,
    personnel_id: Optional[int] = None,
    title: str = None,
    body: str = None,
    deep_link: Optional[str] = None
) -> int:
    """
    Create a notification record in database.
    
    Returns:
        notification_id
    """
    with connection.cursor() as cursor:
        # Get user_type_id
        cursor.execute(
            "SELECT user_type_id FROM user_type WHERE type_name = %s",
            [user_type]
        )
        result = cursor.fetchone()
        if not result:
            raise ValueError(f"Invalid user type: {user_type}")
        
        user_type_id = result[0]
        
        cursor.execute(
            """
            INSERT INTO notification (user_type_id, resident_id, personnel_id, title, body, deep_link, is_read, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, FALSE, NOW())
            RETURNING notification_id
            """,
            [user_type_id, resident_id, personnel_id, title, body, deep_link]
        )
        
        result = cursor.fetchone()
        return result[0] if result else None


def get_user_push_tokens(
    user_type: str,
    resident_id: Optional[int] = None,
    personnel_id: Optional[int] = None
) -> List[Dict[str, str]]:
    """
    Get all push tokens for a user (can have multiple devices).
    
    Returns:
        List of dicts with 'expo_push_token' and 'platform'
    """
    with connection.cursor() as cursor:
        # Get user_type_id
        cursor.execute(
            "SELECT user_type_id FROM user_type WHERE type_name = %s",
            [user_type]
        )
        result = cursor.fetchone()
        if not result:
            return []
        
        user_type_id = result[0]
        
        if user_type == 'RESIDENT':
            cursor.execute(
                """
                SELECT expo_push_token, platform
                FROM push_device
                WHERE user_type_id = %s AND resident_id = %s
                """,
                [user_type_id, resident_id]
            )
        else:
            cursor.execute(
                """
                SELECT expo_push_token, platform
                FROM push_device
                WHERE user_type_id = %s AND personnel_id = %s
                """,
                [user_type_id, personnel_id]
            )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'expo_push_token': row[0],
                'platform': row[1]
            })
        return results


def get_all_resident_push_tokens() -> List[Dict]:
    """
    Get all resident push tokens (for broadcast announcements).
    
    Returns:
        List of dicts with 'resident_id' and 'expo_push_token'
    """
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT resident_id, expo_push_token
            FROM push_device
            WHERE user_type_id = 1
            """
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'resident_id': row[0],
                'expo_push_token': row[1]
            })
        return results


def remove_push_token(expo_push_token: str) -> bool:
    """Remove invalid push token from database."""
    with connection.cursor() as cursor:
        cursor.execute(
            "DELETE FROM push_device WHERE expo_push_token = %s RETURNING push_device_id",
            [expo_push_token]
        )
        result = cursor.fetchone()
        return result is not None
