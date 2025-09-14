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
        
    @staticmethod
    def sp_logout_user(session_token):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'logout_user', [
                        session_token
                    ]
                )
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_change_personnel_default_pwd(pid, new_password):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'change_personnel_default_password', [
                        pid, new_password
                    ]
                )
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_request_password_reset(username, email):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'request_password_reset', [
                        username,
                        email
                    ]
                )
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e