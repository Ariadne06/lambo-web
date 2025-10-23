from django.db import models, connection
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date

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
        
class Dashboard(models.Model):
    """
    Thin query layer for dashboard-related SQL functions.
    Uses the same 'managed = False' pattern as your other classes.
    """
    class Meta:
        managed = False

    @staticmethod
    def sp_dashboard_totals(barangay: Optional[str] = None, city: Optional[str] = None) -> Dict[str, Any]:
        """
        Calls Postgres function:
            SELECT dashboard_totals(%s, %s);
        Expects a JSON/JSONB result with keys:
            total_resident, total_non_resident, total_pending, total_male, total_female
        Returns a plain dict with 0 defaults if keys are missing.
        """
        with connection.cursor() as cursor:
            # callproc also works, but many Postgres JSON-returning functions are cleaner via execute
            cursor.execute("SELECT dashboard_totals(%s, %s);", [barangay, city])
            row = cursor.fetchone()

        payload = row[0]
        if isinstance(payload, str):
            payload = json.loads(payload or "{}")
        elif payload is None:
            payload = {}

        # Safe defaults
        return {
            "total_resident": int(payload.get("total_resident", 0)),
            "total_non_resident": int(payload.get("total_non_resident", 0)),
            "total_pending": int(payload.get("total_pending", 0)),
            "total_male": int(payload.get("total_male", 0)),
            "total_female": int(payload.get("total_female", 0)),
        }
    
    @staticmethod
    def sp_residents_per_sitio_json() -> list[dict[str, Any]]:
        with connection.cursor() as cursor:
            cursor.execute("SELECT residents_per_sitio_json();")
            row = cursor.fetchone()

        val = row[0] if row else None
        if val is None:
            return []
        if isinstance(val, list):            # jsonb -> Python
            return val
        if isinstance(val, (bytes, bytearray)):
            return json.loads(val.decode("utf-8"))
        if hasattr(val, "tobytes"):          # memoryview
            return json.loads(val.tobytes().decode("utf-8"))
        if isinstance(val, str):
            return json.loads(val)
        return []  # fallback

    @staticmethod
    def sp_age_bracket_distribution() -> list[dict]:
        with connection.cursor() as cur:
            cur.execute("SELECT age_bracket_distribution();")
            row = cur.fetchone()
        val = row[0] if row else None
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            import json
            return json.loads(val)
        return []
    
class AnnouncementRepo(models.Model):
    """
    SQL wrappers for announcements with audience support.
    """
    class Meta:
        managed = False
        db_table = 'Announcement'

    # ---------- helpers ----------
    @staticmethod
    def _dictfetchall(cur) -> List[Dict]:
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def _norm_audience(val: Optional[str]) -> str:
        v = (val or "").strip().lower()
        if v in ("", "both", "everyone", "everybody", "all"): return "both"
        if v in ("resident", "residents"): return "resident"
        if v in ("personnel", "staff", "employee", "employees"): return "personnel"
        return v

    @staticmethod
    def _postprocess(rows: List[Dict]) -> List[Dict]:
        out = []
        for a in rows or []:
            a["audience"] = AnnouncementRepo._norm_audience(a.get("audience") or a.get("p_audience"))
            a["announcement_date"] = a.get("announcement_date") or a.get("created_date")
            out.append(a)
        return out

    # ---------- queries ----------
    @staticmethod
    def list_all(q: Optional[str] = None,
                 date_from: Optional[date] = None,
                 date_to: Optional[date] = None,
                 created_by: Optional[int] = None,
                 sort: str = 'date_desc',
                 limit: int = 100, offset: int = 0,
                 audience: Optional[str] = None) -> List[Dict]:
        with connection.cursor() as cur:
            # Updated function has audience param (8 args). If your DB still has the old one, this falls back.
            try:
                cur.execute(
                    "SELECT * FROM get_all_announcement(%s,%s,%s,%s,%s,%s,%s,%s)",
                    [q, date_from, date_to, created_by, sort, limit, offset, audience]
                )
            except Exception:
                cur.execute(
                    "SELECT * FROM get_all_announcement(%s,%s,%s,%s,%s,%s,%s)",
                    [q, date_from, date_to, created_by, sort, limit, offset]
                )
            rows = AnnouncementRepo._dictfetchall(cur)
        return AnnouncementRepo._postprocess(rows)

    @staticmethod
    def latest_for_personnel(limit: int = 3) -> List[Dict]:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM get_latest_announcements_for_personnel()")
                rows = AnnouncementRepo._dictfetchall(cur)
        except Exception:
            rows = AnnouncementRepo.list_all(sort='date_desc', limit=50, audience=None)
        rows = AnnouncementRepo._postprocess(rows)
        out = [a for a in rows if a["audience"] in ("both", "personnel")]
        return out[:limit]

    @staticmethod
    def latest_for_residents(limit: int = 3) -> List[Dict]:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM get_latest_announcements_for_residents()")
                rows = AnnouncementRepo._dictfetchall(cur)
        except Exception:
            rows = AnnouncementRepo.list_all(sort='date_desc', limit=50, audience=None)
        rows = AnnouncementRepo._postprocess(rows)
        out = [a for a in rows if a["audience"] in ("both", "resident")]
        return out[:limit]