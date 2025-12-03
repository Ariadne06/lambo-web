"""
Test script to simulate forwarding an application to payment and sending notification
"""
import sys
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lambo.settings')
django.setup()

from django.db import connection
from notifications.service import NotificationService
from secretary_module.models import SecretaryHelpers

def test_forward_application(application_id=1):
    """Test forwarding an application and sending notification"""
    
    print(f"\n{'='*60}")
    print(f"Testing Forward Application to Payment - App ID: {application_id}")
    print(f"{'='*60}\n")
    
    # Get application details
    print("1. Fetching application details...")
    app_data = SecretaryHelpers.get_specific_application(application_id)
    
    if not app_data:
        print(f"❌ Application {application_id} not found")
        return
    
    print(f"✅ Application found:")
    print(f"   - Application Code: {app_data.get('application_code')}")
    print(f"   - Request Type: {app_data.get('request')}")
    print(f"   - Requested By: {app_data.get('requested_by')}")
    print(f"   - Requested By ID: {app_data.get('requested_by_id')}")
    print(f"   - Current Status: {app_data.get('application_status')}")
    
    # Check if requested by resident
    if app_data.get('requested_by') != 'resident':
        print(f"\n⚠️  Application not requested by resident (requested_by: {app_data.get('requested_by')})")
        print("   No notification will be sent.")
        return
    
    if not app_data.get('requested_by_id'):
        print(f"\n❌ No requested_by_id found")
        return
    
    resident_id = app_data['requested_by_id']
    print(f"\n2. Looking up user_id for resident_id: {resident_id}")
    
    # Get user_id from resident_id
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT user_id, first_name, last_name FROM resident WHERE resident_id = %s",
            [resident_id]
        )
        result = cursor.fetchone()
        
        if not result:
            print(f"❌ Resident {resident_id} not found in database")
            return
        
        user_id, first_name, last_name = result
        
        if not user_id:
            print(f"❌ Resident {first_name} {last_name} has no user_id (not registered in app)")
            return
        
        print(f"✅ Found user: {first_name} {last_name} (user_id: {user_id})")
    
    # Check if user has push tokens
    print(f"\n3. Checking push tokens for user_id: {user_id}")
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT push_token, device_type FROM push_device WHERE user_id = %s AND is_active = TRUE",
            [user_id]
        )
        tokens = cursor.fetchall()
        
        if not tokens:
            print(f"⚠️  No active push tokens found for user {user_id}")
            print("   Notification will be saved to database but won't be pushed")
        else:
            print(f"✅ Found {len(tokens)} active push token(s):")
            for token, device_type in tokens:
                print(f"   - {device_type}: {token[:50]}...")
    
    # Send notification
    print(f"\n4. Sending notification...")
    certificate_type = app_data.get('request', 'Certificate')
    application_code = app_data.get('application_code', '')
    
    try:
        result = NotificationService.send_to_resident(
            resident_id=user_id,
            title="✅ Certificate Ready for Payment",
            body=f"Your {certificate_type} request ({application_code}) has been approved! Please visit the barangay office to complete your payment.",
            deep_link=f"/(tabs)/documents/{application_id}"
        )
        print(f"✅ Notification sent successfully!")
        print(f"   Result: {result}")
    except Exception as e:
        print(f"❌ Error sending notification: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Verify notification was saved
    print(f"\n5. Verifying notification in database...")
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT notification_id, title, body, is_read, created_at 
            FROM notification 
            WHERE user_id = %s 
            ORDER BY created_at DESC 
            LIMIT 1
            """,
            [user_id]
        )
        notif = cursor.fetchone()
        
        if notif:
            notif_id, title, body, is_read, created_at = notif
            print(f"✅ Notification saved to database:")
            print(f"   - ID: {notif_id}")
            print(f"   - Title: {title}")
            print(f"   - Body: {body}")
            print(f"   - Read: {is_read}")
            print(f"   - Created: {created_at}")
        else:
            print(f"❌ No notification found in database")
    
    print(f"\n{'='*60}")
    print("Test completed!")
    print(f"{'='*60}\n")

if __name__ == "__main__":
    # You can pass application_id as command line argument
    app_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    test_forward_application(app_id)
