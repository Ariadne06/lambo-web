from django.contrib import admin
from .models import UserType, PushDevice, Notification


@admin.register(UserType)
class UserTypeAdmin(admin.ModelAdmin):
    list_display = ['user_type_id', 'type_name', 'description']
    search_fields = ['type_name']


@admin.register(PushDevice)
class PushDeviceAdmin(admin.ModelAdmin):
    list_display = ['push_device_id', 'user_type', 'resident_id', 'personnel_id', 'platform', 'last_seen']
    list_filter = ['user_type', 'platform']
    search_fields = ['expo_push_token', 'resident_id', 'personnel_id']
    readonly_fields = ['last_seen']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'title', 'user_type', 'resident_id', 'personnel_id', 'is_read', 'created_at']
    list_filter = ['user_type', 'is_read', 'created_at']
    search_fields = ['title', 'body', 'resident_id', 'personnel_id']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
