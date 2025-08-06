from django.db import models, connection

class logging(models.Model):
    
    @staticmethod
    def sp_login_personnel_web(username, password):
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