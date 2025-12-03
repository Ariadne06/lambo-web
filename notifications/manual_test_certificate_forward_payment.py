"""
Test script to simulate forwarding a certificate application to treasurer (For Payment).
This will trigger a notification to the resident.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lambo.settings')
django.setup()

from secretary_module.models import SecretaryHelpers
from notifications.service import NotificationService
from django.db import connection

def test_forward_to_payment():
    """Test forwarding an application to payment and sending notification."""
    
    # First, let's check what applications exist for resident user_id 57
    print("Checking applications for resident user_id 57...")
    with connection.cursor() as cursor:
        # Get resident_id from user_id
        cursor.execute("SELECT resident_id FROM resident WHERE user_id = %s", [57])
        result = cursor.fetchone()
        
        if not result:
            print("❌ No resident found for user_id 57")
            return
        
        resident_id = result[0]
        print(f"✅ Found resident_id: {resident_id}")
        
        # Check for applications by this resident
        cursor.execute("""
            SELECT application_id, application_code, request, application_status, payment_status
            FROM get_all_application(NULL, NULL, NULL, 100, 0)
            WHERE requested_by = 'resident' AND requested_by_id = %s
            ORDER BY application_id DESC
            LIMIT 5
        """, [resident_id])
        
        applications = cursor.fetchall()
        
        if not applications:
            print(f"❌ No applications found for resident_id {resident_id}")
            print("\nYou need to create an application first through the secretary module.")
            return
        
        print(f"\n📋 Found {len(applications)} application(s):")
        for app in applications:
            app_id, code, request_type, app_status, pay_status = app
            print(f"  - ID: {app_id}, Code: {code}, Type: {request_type}, Status: {app_status}, Payment: {pay_status}")
        
        # Find first Pending application
        pending_app = None
        for app in applications:
            if app[3] == 'Pending':  # application_status
                pending_app = app
                break
        
        if not pending_app:
            print("\n❌ No Pending applications found to forward.")
            print("All applications are already processed or in other states.")
            return
        
        application_id = pending_app[0]
        print(f"\n🎯 Will forward application ID {application_id} ({pending_app[1]}) to treasurer...")
        
        # Get application details
        app_data = SecretaryHelpers.get_specific_application(application_id)
        print(f"\nApplication details:")
        print(f"  - Type: {app_data.get('request')}")
        print(f"  - Applicant: {app_data.get('applicant_name')}")
        print(f"  - Code: {app_data.get('application_code')}")
        print(f"  - Status: {app_data.get('application_status')}")
        
        # Forward to payment (this should trigger the notification)
        print(f"\n📤 Forwarding to treasurer...")
        SecretaryHelpers.set_application_to_for_payment(application_id)
        
        # Manually send notification (since we're not going through the view)
        if app_data.get('requested_by') == 'resident' and app_data.get('requested_by_id'):
            cursor.execute("SELECT user_id FROM resident WHERE resident_id = %s", [app_data['requested_by_id']])
            user_result = cursor.fetchone()
            
            if user_result and user_result[0]:
                user_id = user_result[0]
                certificate_type = app_data.get('request', 'Certificate')
                application_code = app_data.get('application_code', '')
                
                print(f"\n📲 Sending notification to user_id {user_id}...")
                NotificationService.send_to_resident(
                    resident_id=user_id,
                    title="✅ Certificate Ready for Payment",
                    body=f"Your {certificate_type} request ({application_code}) has been approved! Please visit the barangay office to complete your payment.",
                    deep_link="/(tabs)/documents"
                )
                print("✅ Notification sent successfully!")
        
        # Verify the status changed
        updated_app = SecretaryHelpers.get_specific_application(application_id)
        print(f"\n✅ Application status updated to: {updated_app.get('application_status')}")
        
        # Check notification was saved
        cursor.execute("""
            SELECT notification_id, title, body, created_at
            FROM notification
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        """, [user_id])
        
        notif = cursor.fetchone()
        if notif:
            print(f"\n📬 Latest notification:")
            print(f"  - ID: {notif[0]}")
            print(f"  - Title: {notif[1]}")
            print(f"  - Body: {notif[2]}")
            print(f"  - Created: {notif[3]}")
        
        print(f"\n🎉 Test completed! Check the mobile app for the notification.")

if __name__ == '__main__':
    test_forward_to_payment()
