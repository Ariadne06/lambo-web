from django.db import models, connection

class Admin(models.Model):
    class Meta:
        managed = False  # just a helper for DB calls

    @staticmethod
    def sp_search_residents_live_with_id(text: str):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('search_residents_live_with_id', [text])
                rows = cursor.fetchall()
                return rows
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_resident_profile(id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_resident_profile', [id])
                result = cursor.fetchone()
                return result
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_insert_personnel_credentials(id, role_id, username, email):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_personnel_credentials', [id, role_id, username, email])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_all_personnels(limit, offset, sort_by, sort_dir):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_all_personnels_simple_initial', [limit, offset, sort_by, sort_dir])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e

    @staticmethod
    def sp_search_personnels(query, approval_status, is_active, limit, offset, sort_by, sort_dir):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('search_personnels', [query, approval_status, is_active, limit, offset, sort_by, sort_dir])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def get_personnel_by_id(pid: int):
        with connection.cursor() as cursor:
            cursor.callproc('get_personnel_by_id', [pid])
            row = cursor.fetchone()
            if not row:
                return None
            return {"pid": row[0], "username": row[5] or "", "email": row[6] or "", "role_id": row[3], "role_name": row[4]}
        
    @staticmethod
    def sp_update_personnel_credentials(id, username, email, role_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('update_personnel_credentials', [id, username, email, role_id])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_set_personnel_active_status(id, active, admin_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('admin_set_personnel_active_status', [id, active, admin_id])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_admin_reset_personnel_to_pending(id, admin_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('admin_reset_personnel_to_pending', [id, admin_id])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_edit_personnel_draft(id, admin_id, role_id, username, email):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('edit_personnel_draft', [id, admin_id, role_id, username, email])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_activty_logs(limit, offset, sort_by, sort_dir):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_activity_logs', [limit, offset, sort_by, sort_dir])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_personnel_password_requests_forgot(
        query, 
        approval_status, 
        is_active,
        role_id,
        start_ts, 
        end_ts, 
        limit, 
        offset, 
        sort_by, 
        sort_dir
    ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_personnel_password_requests_forgot', [
                    query, 
                    approval_status, 
                    is_active,
                    role_id,
                    start_ts, 
                    end_ts,  
                    limit, 
                    offset, 
                    sort_by, 
                    sort_dir
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_admin_review_personnel_password_request(pid, action):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('admin_review_personnel_password_request', [pid, action])
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e
