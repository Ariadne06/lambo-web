"""
Quick test for sending push notifications
Run with: python manage.py shell < notifications/test_send_notification.py

Make sure you:
1. Have the mobile app running and logged in as a resident
2. The resident's push token is registered in the database
3. Check the resident_id matches your logged-in user
"""

from notifications.service import NotificationService

# Get the resident ID from your logged-in user
# Check the console logs in the mobile app to see the user_id
RESIDENT_ID = 57  # Change this to your actual resident_id

print("=" * 60)
print("📱 Testing Push Notification System")
print("=" * 60)

# Test 1: Simple notification
print("\n🔔 Sending test notification...")
service = NotificationService()

try:
    result = service.send_to_resident(
        resident_id=RESIDENT_ID,
        title="🎉 Test Notification",
        body="Hello from LAMBO! This is a test push notification.",
        deep_link="/(tabs)/notifications"
    )
    print(f"✅ Success! Result: {result}")
    print("\n📱 Check your mobile device for the notification!")
    
except Exception as e:
    print(f"❌ Error: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Make sure the mobile app is running")
    print("2. Check that you're logged in as a resident")
    print("3. Verify the resident_id is correct")
    print("4. Check if push token is registered in push_device table")

print("\n" + "=" * 60)
