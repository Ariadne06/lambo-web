"""
Management command to set all active businesses to "For Renewal" status
and send push notifications to business owners.

This is designed to be run as a cronjob (e.g., on January 1st each year).

Usage:
    python manage.py set_business_for_renewal
    
Cronjob setup (Linux/Mac):
    # Run on January 1st at 8:00 AM
    0 8 1 1 * cd /path/to/lambo-web-1 && /path/to/.venv/bin/python manage.py set_business_for_renewal
    
Windows Task Scheduler:
    Program: C:\Users\Adrianne\Projects\LamboRepos\lambo-web-1\.venv\Scripts\python.exe
    Arguments: manage.py set_business_for_renewal
    Start in: C:\Users\Adrianne\Projects\LamboRepos\lambo-web-1
"""
from django.core.management.base import BaseCommand
from django.db import connection
from notifications.service import notify_business_renewal_required


class Command(BaseCommand):
    help = 'Set all active businesses to "For Renewal" status and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--deadline',
            type=str,
            default='March 31, 2025',
            help='Renewal deadline date (default: March 31, 2025)'
        )

    def handle(self, *args, **options):
        deadline = options['deadline']
        
        self.stdout.write('Setting active businesses to "For Renewal" status...')
        
        try:
            with connection.cursor() as cursor:
                # Get active and for_renewal status IDs
                cursor.execute("""
                    SELECT business_status_id 
                    FROM business_status 
                    WHERE LOWER(business_status_name) = 'for renewal' 
                    LIMIT 1
                """)
                for_renewal_status = cursor.fetchone()
                
                cursor.execute("""
                    SELECT business_status_id 
                    FROM business_status 
                    WHERE LOWER(business_status_name) = 'active' 
                    LIMIT 1
                """)
                active_status = cursor.fetchone()
                
                if not for_renewal_status or not active_status:
                    self.stdout.write(
                        self.style.ERROR('✗ Required business statuses not found in database')
                    )
                    return
                
                for_renewal_status_id = for_renewal_status[0]
                active_status_id = active_status[0]
                
                # Get all active businesses with owner details
                cursor.execute("""
                    SELECT 
                        b.business_id,
                        b.business_name,
                        b.resident_id,
                        r.first_name,
                        r.last_name
                    FROM business b
                    JOIN resident r ON b.resident_id = r.resident_id
                    WHERE b.business_status_id = %s
                """, [active_status_id])
                
                businesses = cursor.fetchall()
                
                if not businesses:
                    self.stdout.write(
                        self.style.WARNING('⚠ No active businesses found')
                    )
                    return
                
                updated_count = 0
                notification_count = 0
                errors = []
                
                # Process each business
                for business_id, business_name, resident_id, first_name, last_name in businesses:
                    try:
                        # Update business status
                        cursor.execute("""
                            UPDATE business 
                            SET business_status_id = %s, 
                                updated_at = NOW() 
                            WHERE business_id = %s
                        """, [for_renewal_status_id, business_id])
                        
                        updated_count += 1
                        
                        # Send push notification
                        notify_business_renewal_required(
                            resident_id=resident_id,
                            business_name=business_name,
                            deadline=deadline
                        )
                        notification_count += 1
                        
                        self.stdout.write(
                            f'  ✓ {business_name} (Owner: {first_name} {last_name})'
                        )
                        
                    except Exception as e:
                        error_msg = f'{business_name}: {str(e)}'
                        errors.append(error_msg)
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ {error_msg}')
                        )
                
                # Log the activity
                cursor.execute("""
                    INSERT INTO activity_log (activity_type, description, created_at)
                    VALUES ('BUSINESS_RENEWAL', %s, NOW())
                """, [f'Set {updated_count} businesses to For Renewal status'])
                
                # Summary
                self.stdout.write('')
                self.stdout.write(self.style.SUCCESS('=' * 60))
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Updated {updated_count} businesses to "For Renewal" status')
                )
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Sent {notification_count} push notifications')
                )
                
                if errors:
                    self.stdout.write(
                        self.style.WARNING(f'⚠ {len(errors)} errors occurred')
                    )
                
                self.stdout.write(self.style.SUCCESS('=' * 60))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'✗ Failed: {str(e)}')
            )
            import traceback
            traceback.print_exc()
