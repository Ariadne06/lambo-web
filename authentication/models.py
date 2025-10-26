from django.db import models, connection

class authentication(models.Model):
    class Meta:
        managed = False
    
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
        
    @staticmethod
    def sp_reset_resident_password_by_username(username, password):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'reset_resident_password_by_username', [
                        username,
                        password
                    ]
                )
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_check_resident_username_email(username, email):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'check_resident_username_email', [
                        username,
                        email
                    ]
                )
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_identify_account_type(username, email):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('identify_account_type', [username, email])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e     