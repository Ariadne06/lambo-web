from django.db import models, connection
from typing import Tuple
from typing import List, Dict, Tuple
from django.utils import timezone

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
    def sp_get_activty_logs(limit, offset, sort_by, sort_dir, query):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_activity_logs', [limit, offset, sort_by, sort_dir, query])
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

    @staticmethod
    def fn_personnel_counts() -> Tuple[int, int]:
        """
        Returns (total_count, active_count).
        active_count uses your get_all_personnel_count() SQL FUNCTION.
        total_count uses a direct COUNT(*) on Personnel_Credentials.
        """
        TOTAL_QUERY = 'SELECT COUNT(*)::int FROM "Personnel_Credentials";'  # use lowercased table name if yours is unquoted
        ACTIVE_QUERY = 'SELECT get_all_personnel_count();'

        with connection.cursor() as cursor:
            # Active via your SQL function
            try:
                cursor.execute(ACTIVE_QUERY)
                (active_count,) = cursor.fetchone()
                active_count = int(active_count or 0)
            except Exception:
                # Fallback if function isn't present yet
                active_count = 0

            # Total via direct count
            try:
                cursor.execute(TOTAL_QUERY)
            except Exception:
                # Fallback to unquoted name if your table wasn’t created quoted
                cursor.execute('SELECT COUNT(*)::int FROM personnel_credentials;')
            (total_count,) = cursor.fetchone()
            total_count = int(total_count or 0)

        return total_count, active_count
    
    @staticmethod
    def get_password_reset_requests(limit: int = 50) -> List[Dict]:
        """
        Maps rows from get_all_personnel_password_request_reset_with_date()
        to what your template expects: id, name, when (and optional role).
        """
        sql = "SELECT * FROM get_all_personnel_password_request_reset_with_date(%s);"
        with connection.cursor() as cursor:
            cursor.execute(sql, [limit])
            rows = cursor.fetchall()

        data: List[Dict] = []
        for request_id, personnel_id, requester_name, requested_at, requested_ago in rows:
            data.append({
                "id": int(request_id),
                "personnel_id": int(personnel_id),
                "name": requester_name,
                "when": requested_ago,
                "requested_at": requested_at,
                "role": None,  # optional in your HTML
            })
        return data
    
    @staticmethod
    def get_recent_activity_for_ui() -> List[Dict]:
        """
        Calls get_recent_activity_log_limit_ten() and maps rows to what the
        template expects: user, role, ip, when, status.
        """
        sql = "SELECT log_timestamp, display_text FROM get_recent_activity_log_limit_ten();"
        with connection.cursor() as cursor:
            cursor.execute(sql)
            rows = cursor.fetchall()  # [(timestamp, text), ...]

        now = timezone.now()
        tz = timezone.get_current_timezone()

        def fmt_ago(ts):
            if ts is None:
                return ""
            # Ensure tz-aware in current timezone for display
            try:
                local_ts = timezone.localtime(ts, tz)
            except Exception:
                local_ts = ts

            delta = now - ts
            secs = int(delta.total_seconds())
            if secs < 60:
                return "just now"
            if secs < 3600:
                return f"{secs // 60} mins ago"
            if secs < 86400:
                return f"{secs // 3600} hours ago"
            if secs < 172800:
                return "Yesterday"
            # Fallback absolute
            return local_ts.strftime("%b %d, %Y %I:%M %p")

        data: List[Dict] = []
        for ts, text in rows:
            data.append({
                "user": text,        # use the formatted display_text as the main line
                "role": "Activity",  # label to keep your "•" separator looking tidy
                "ip": "—",           # not available from this SQL; placeholder
                "when": fmt_ago(ts),
                "status": "Log",     # shows as a gray chip in your template
            })
        return data