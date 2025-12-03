"""
Check notifications in the database
Run with: python manage.py shell < notifications/check_notifications.py
"""

from notifications.repo import get_user_notifications

print("\n" + "=" * 60)
print("📬 Checking Notifications in Database")
print("=" * 60)

# Check notifications for resident_id 57
print("\n📱 Checking notifications for resident_id: 57")
notifications = get_user_notifications(
    user_type='RESIDENT',
    resident_id=57,
    personnel_id=None,
    limit=10
)

if notifications:
    print(f"✅ Found {len(notifications)} notification(s):\n")
    for notif in notifications:
        read_status = "✅ Read" if notif['is_read'] else "🔔 Unread"
        print(f"  {read_status} - {notif['title']}")
        print(f"    {notif['body']}")
        print(f"    Created: {notif['created_at']}")
        print(f"    ID: {notif['notification_id']}\n")
else:
    print("❌ No notifications found")

print("=" * 60 + "\n")
