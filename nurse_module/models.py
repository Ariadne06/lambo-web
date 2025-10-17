from django.db import models, connection
import json
from typing import Optional, List, Dict, Any
# Create your models here.

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
    Thin wrapper around your SQL functions:
      - insert_announcement(title, details, image_path, created_by, audience) -> INT
      - get_all_announcement(q, date_from, date_to, created_by, sort, limit, offset, audience) -> rows
      - get_specific_announcement(id) -> row (includes audience)
      - update_announcement(id, updated_by, title?, details?, image_path?, audience?) -> BOOLEAN
      - delete_announcement(id, deleted_by) -> BOOLEAN
    """
    class Meta:
        managed = False
        db_table = 'Announcement'
    
    @staticmethod
    def latest_for_residents(limit=3, offset=0, q=None, date_from=None, date_to=None):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_latest_announcements_for_residents(%s,%s,%s,%s,%s)",
                [limit, offset, q, date_from, date_to]
            )
            return AnnouncementRepo._dictfetchall(cur)

    # NEW: latest for personnel (SQL: get_latest_announcements_for_personnel)
    @staticmethod
    def latest_for_personnel(limit=3, offset=0, q=None, date_from=None, date_to=None):
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_latest_announcements_for_personnel(%s,%s,%s,%s,%s)",
                [limit, offset, q, date_from, date_to]
            )
            return AnnouncementRepo._dictfetchall(cur)
