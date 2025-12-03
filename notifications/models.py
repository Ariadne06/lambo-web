from django.db import models


class UserType(models.Model):
    user_type_id = models.AutoField(primary_key=True, db_column='user_type_id')
    type_name = models.CharField(max_length=50, unique=True, db_column='type_name')
    description = models.TextField(null=True, blank=True, db_column='description')
    
    class Meta:
        managed = False
        db_table = 'user_type'
    
    def __str__(self):
        return self.type_name


class PushDevice(models.Model):
    push_device_id = models.AutoField(primary_key=True, db_column='push_device_id')
    user_type = models.ForeignKey(UserType, on_delete=models.CASCADE, db_column='user_type_id')
    resident_id = models.IntegerField(null=True, blank=True, db_column='resident_id')
    personnel_id = models.IntegerField(null=True, blank=True, db_column='personnel_id')
    platform = models.CharField(max_length=20, null=True, blank=True, db_column='platform')
    expo_push_token = models.TextField(unique=True, db_column='expo_push_token')
    last_seen = models.DateTimeField(auto_now=True, db_column='last_seen')
    
    class Meta:
        managed = False
        db_table = 'push_device'
    
    def __str__(self):
        if self.user_type.type_name == 'RESIDENT':
            return f"Device for Resident {self.resident_id}"
        else:
            return f"Device for Personnel {self.personnel_id}"


class Notification(models.Model):
    notification_id = models.AutoField(primary_key=True, db_column='notification_id')
    user_type = models.ForeignKey(UserType, on_delete=models.CASCADE, db_column='user_type_id')
    resident_id = models.IntegerField(null=True, blank=True, db_column='resident_id')
    personnel_id = models.IntegerField(null=True, blank=True, db_column='personnel_id')
    title = models.CharField(max_length=255, db_column='title')
    body = models.TextField(db_column='body')
    deep_link = models.TextField(null=True, blank=True, db_column='deep_link')
    is_read = models.BooleanField(default=False, db_column='is_read')
    created_at = models.DateTimeField(auto_now_add=True, db_column='created_at')
    
    class Meta:
        managed = False
        db_table = 'notification'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.title} - {'Read' if self.is_read else 'Unread'}"
