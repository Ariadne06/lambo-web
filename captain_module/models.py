from django.db import models, connection

class Captain(models.Model):
    class Meta:
        managed = False
        
    @staticmethod
    def sp_get_pending_personnel_requests(query, limit, offset, sort_by, sort_dir):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_pending_personnel_requests', [query, limit, offset, sort_by, sort_dir])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_review_personnel_account_by_captain(pid, new_status, captain_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('review_personnel_account_by_captain', [pid, new_status, captain_id])
                result = cursor.fetchone()
                return result
        except Exception as e:
            raise e
