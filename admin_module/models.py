from django.db import models, connection

# Create your models here.

class admin(models.Model):
    
    @staticmethod
    def sp_view_activity_logs():
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'login_personnel_web', [
                        username, password
                    ]
                )
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e