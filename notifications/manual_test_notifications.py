"""
Quick test script for notification system
Run with: python manage.py shell < notifications/test_notifications.py

NOTE: This is NOT a Django unit test. This is a manual test script.
Do not run this with 'python manage.py test' - it will fail.
"""

import sys

# Skip this file when running Django tests
if 'test' in sys.argv:
    print("Skipping manual test script (not a unit test)")
    sys.exit(0)

from notifications.service import NotificationService, notify_certificate_approved, notify_new_announcement

# Test 1: Send notification to a specific resident
print("=" * 50)
print("Test 1: Sending test notification to resident_id=1")
print("=" * 50)

service = NotificationService()
result = service.send_to_resident(
    resident_id=1,
    title="🔔 Test Notification",
    body="This is a test notification from the LAMBO system!",
    deep_link="/(tabs)/notifications"
)
print(f"Result: {result}")

# Test 2: Use convenience function for certificate approval
print("\n" + "=" * 50)
print("Test 2: Certificate approval notification")
print("=" * 50)

notify_certificate_approved(
    resident_id=1,
    document_type_name="Barangay Clearance",
    application_id=1
)
print("Certificate approval notification sent!")

# Test 3: Broadcast to all residents
print("\n" + "=" * 50)
print("Test 3: Broadcast announcement to all residents")
print("=" * 50)

notify_new_announcement(
    title="📢 Important Announcement",
    message="This is a test broadcast to all residents",
    deep_link="/(tabs)/announcement"
)
print("Broadcast sent to all residents!")

print("\n" + "=" * 50)
print("✅ All tests completed!")
print("=" * 50)
