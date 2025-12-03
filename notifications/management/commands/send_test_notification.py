"""
Management command to send test notifications to all residents.
This properly uses the NotificationService to both create DB records AND send push notifications.

Usage:
    python manage.py send_test_notification
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from notifications.service import NotificationService


class Command(BaseCommand):
    help = 'Send test notification to all residents with push notifications'

    def handle(self, *args, **options):
        current_time = timezone.now().strftime('%H:%M:%S')
        
        self.stdout.write('Sending test notification to all residents...')
        
        success = NotificationService.send_to_all_residents(
            title='Test Notification',
            body=f'Hello! This is a test notification sent at {current_time}. The push notification system is working! 🎉',
            deep_link='/(tabs)/notifications'
        )
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(
                    '✓ Successfully sent notifications to all residents!'
                )
            )
            self.stdout.write(
                self.style.SUCCESS(
                    '✓ Check your mobile device for push notifications'
                )
            )
        else:
            self.stdout.write(
                self.style.ERROR(
                    '✗ Failed to send notifications. Check logs for details.'
                )
            )
