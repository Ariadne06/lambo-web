"""
Send a test notification with deep link to home screen
Run with: python manage.py shell < notifications/test_home_notification.py
"""

from notifications.service import NotificationService

RESIDENT_ID = 57

print("\n" + "=" * 60)
print("📱 Sending Notification with Home Deep Link")
print("=" * 60)

service = NotificationService()

try:
    result = service.send_to_resident(
        resident_id=RESIDENT_ID,
        title="🏠 Welcome Back!",
        body="Tap to go to your home screen.",
        deep_link="/(tabs)"  # Navigate to home tab
    )
    print(f"✅ Success! Notification sent")
    print("📱 Tap the notification to navigate to the home screen!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")

print("\n" + "=" * 60 + "\n")
