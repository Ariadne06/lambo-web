from django.db import models, connection
from django.db.utils import ProgrammingError, DatabaseError  # ✅ use Django’s wrappers
import json
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, date
from math import ceil
from dataclasses import dataclass
from psycopg2.errors import UndefinedFunction as PGUndefinedFunction

# Optional: catch the specific Postgres error when a SQL function is missing
try:
    from psycopg.errors import UndefinedFunction as PGUndefinedFunction
except Exception:
    class PGUndefinedFunction(Exception):
        """Fallback so we can safely 'except PGUndefinedFunction' even if psycopg.errors is unavailable."""
        pass


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
    

class ResidentList(models.Model):
    """
    Thin query layer for the Postgres function:
      view_all_resident(p_query, p_sex, p_status_id, p_min_age, p_max_age, p_limit, p_offset)
    """
    class Meta:
        managed = False

    @staticmethod
    def _rows_to_dicts(cursor) -> List[Dict[str, Any]]:
        cols = [col[0] for col in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]

    @staticmethod
    def search(
        p_query: Optional[str] = None,
        p_sex: Optional[str] = None,          # 'male'/'female'
        p_status_id: Optional[int] = None,
        p_min_age: Optional[int] = None,
        p_max_age: Optional[int] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Dict[str, Any]:
        page = max(1, int(page or 1))
        limit = max(0, int(page_size or 50))
        offset = (page - 1) * limit

        norm_sex = None
        if p_sex:
            s = str(p_sex).strip().lower()
            if s in ("male", "female"):
                norm_sex = s

        # 1) paged rows
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT *
                FROM view_all_resident(%s,%s,%s,%s,%s,%s,%s);
                """,
                [p_query, norm_sex, p_status_id, p_min_age, p_max_age, limit, offset],
            )
            rows = ResidentList._rows_to_dicts(cursor)

        # 2) total count (simple approach)
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*)::int
                FROM view_all_resident(%s,%s,%s,%s,%s,%s,%s);
                """,
                [p_query, norm_sex, p_status_id, p_min_age, p_max_age, 2147483647, 0],
            )
            total = cursor.fetchone()[0] if cursor.rowcount != 0 else 0

        pages = max(1, ceil(total / limit)) if limit else 1

        # Build modal payloads (aligned with the template)
        for r in rows:
            payload = {
                "resident_id": r.get("resident_id"),
                "resident_code": r.get("resident_code"),
                # Use full_name directly from SQL (don’t split)
                "full_name": r.get("full_name") or "",         # <— send full_name directly
                "sex": r.get("sex"),
                "dob": str(r.get("dob")) if r.get("dob") else "",
                "age": r.get("age"),
                "religion": r.get("religion"),
                "educ_attainment": r.get("educational_attainment"),
                "religion": r.get("religion"), 
                "civil_status": r.get("civil_status"),
                "resident_status": r.get("status_name"),
                # New: bind to full_address from SQL
                "full_address": r.get("full_address"),
                # Table fields you still show:
                "household_number": r.get("household_number"),
                "family_code": r.get("family_code"),
            }
            r["payload_json"] = json.dumps(payload, ensure_ascii=False)


        return {
            "rows": rows,
            "total": total,
            "page": page,
            "pages": pages,
            "limit": limit,
            "offset": offset,
        }






class ChildHealthListRow(models.Model):
    """
    Unmanaged model backed by the SQL set-returning function view_all_child_health_record().
    We only use the static fetch()/count() helpers; Django never touches db_table.
    """
    child_health_id = models.IntegerField(primary_key=True)
    child_id = models.IntegerField()
    child_full_name = models.TextField()
    sex = models.TextField()
    dob = models.DateField(null=True)
    age = models.TextField(null=True)
    family_code = models.TextField(null=True)
    # 🔹 NEW FIELDS to match the revised function
    sitio_id = models.IntegerField(null=True)
    sitio_name = models.TextField(null=True)
    feeding_method_name = models.TextField(null=True)
    tt_status_name = models.TextField(null=True)
    tt_status_date = models.DateField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "view_all_child_health_record_row"  # label only

    @staticmethod
    def fetch(
        query: Optional[str] = None,
        sitio_id: Optional[int] = None,
        sex: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        SELECT * FROM view_all_child_health_record(%s, %s, %s, %s, %s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      child_health_id,
                      child_id,
                      child_full_name,
                      sex,
                      dob,
                      age,
                      family_code,
                      sitio_id,
                      sitio_name,
                      feeding_method_name,
                      tt_status_name,
                      tt_status_date,
                      created_at
                    FROM view_all_child_health_record(
                      %s::TEXT,      -- p_query
                      %s::INT,       -- p_sitio_id
                      %s::TEXT,      -- p_sex
                      %s::INT,       -- p_limit
                      %s::INT        -- p_offset
                    )
                    """,
                    [query, sitio_id, sex, limit, offset],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            # If function not found / still creating, just return empty list
            return []
        
    @staticmethod
    def count(
        query: Optional[str] = None,
        sitio_id: Optional[int] = None,
        sex: Optional[str] = None,
    ) -> int:
        """
        Approximate total using a large limit. Replace with a dedicated count func if you add one.
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM (
                      SELECT 1
                      FROM view_all_child_health_record(
                        %s::TEXT,      -- p_query
                        %s::INT,       -- p_sitio_id
                        %s::TEXT,      -- p_sex
                        500000::INT,   -- p_limit
                        0::INT         -- p_offset
                      )
                    ) t
                    """,
                    [query, sitio_id, sex],
                )
                return cur.fetchone()[0]
        except (ProgrammingError, PGUndefinedFunction):
            return 0
        


class ChildHealthDetailRow(models.Model):
    """
    Unmanaged DTO for view_specific_child_health_record(child_health_id INT).
    We only use fetch_one(); Django doesn't manage a physical table.
    """
    # Not strictly required to declare all fields here since we return dicts,
    # but leaving a label helps in admin/debug.
    class Meta:
        managed = False
        db_table = "view_specific_child_health_record_row"

    @staticmethod
    def fetch_one(child_health_id: int) -> Optional[Dict[str, Any]]:
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT * FROM view_specific_child_health_record(%s::INT)", [child_health_id])
                row = cur.fetchone()
                if not row:
                    return None
                cols = [c[0] for c in cur.description]
                return dict(zip(cols, row))
        except ProgrammingError as e:
            # TEMP: bubble up so you see the real error in your console/logs
            raise


class GrowthMonitoringRow(models.Model):
    """
    Unmanaged helper to read rows from:
      view_specific_child_all_growth_monitoring(p_child_health_id INT)
    """
    class Meta:
        managed = False
        db_table = "view_specific_child_all_growth_monitoring_row"  # label only

    @staticmethod
    def fetch(child_health_id: int) -> List[Dict[str, Any]]:
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM view_specific_child_all_growth_monitoring(%s::INT)
                    """,
                    [child_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except ProgrammingError as e:
            # log if you want; return empty so UI shows "no data"
            return []
        

class ImmunizationRow(models.Model):
    """Reads rows from view_specific_child_immunization_record(p_child_health_id INT)."""
    class Meta:
        managed = False
        db_table = "view_specific_child_immunization_record_row"  # label only

    @staticmethod
    def fetch(child_health_id: int) -> List[Dict[str, Any]]:
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT *
                    FROM view_specific_child_immunization_record(%s::INT)
                    """,
                    [child_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except ProgrammingError:
            return []
        

class MedicalConditionRow(models.Model):
    """Rows from view_specific_child_all_medical_condition(p_child_health_id INT)."""
    class Meta:
        managed = False
        db_table = "view_specific_child_all_medical_condition_row"  # label only

    @staticmethod
    def fetch(child_health_id: int) -> List[Dict[str, Any]]:
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT * FROM view_specific_child_all_medical_condition(%s::INT)",
                    [child_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except ProgrammingError:
            return []


class SurgicalHistoryRow(models.Model):
    """Rows from view_specific_child_all_surgical_history(p_child_health_id INT)."""
    class Meta:
        managed = False
        db_table = "view_specific_child_all_surgical_history_row"  # label only

    @staticmethod
    def fetch(child_health_id: int) -> List[Dict[str, Any]]:
        try:
            with connection.cursor() as cur:
                cur.execute(
                    "SELECT * FROM view_specific_child_all_surgical_history(%s::INT)",
                    [child_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except ProgrammingError:
            return []
        


class MaternalHealthListRow(models.Model):
    """
    Unmanaged model backed by the SQL set-returning function View_all_maternal_record().
    We only use the static fetch()/count() helpers; Django never touches db_table.
    """
    maternal_health_id = models.IntegerField(primary_key=True)
    maternal_id = models.IntegerField()
    maternal_full_name = models.TextField()
    dob = models.DateField(null=True)
    record_status = models.TextField()
    date_created = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "view_all_maternal_record_row"  # label only – not an actual table

    @staticmethod
    def fetch(
        name_query: Optional[str] = None,
        family_code: Optional[str] = None,
        record_status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        SELECT ... FROM View_all_maternal_record(%s, %s, %s, %s, %s)
        with ORDER BY + LIMIT/OFFSET for pagination.
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      maternal_health_id,
                      maternal_id,
                      maternal_full_name,
                      dob,
                      record_status,
                      date_created
                    FROM View_all_maternal_record(%s, %s, %s, %s, %s)
                    ORDER BY date_created DESC
                    LIMIT %s OFFSET %s
                    """,
                    [name_query, family_code, record_status, date_from, date_to, limit, offset],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            # Function not found or still being created
            return []

    @staticmethod
    def count(
        name_query: Optional[str] = None,
        family_code: Optional[str] = None,
        record_status: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> int:
        """
        Exact total using the same View_all_maternal_record() function.
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM View_all_maternal_record(%s, %s, %s, %s, %s) AS t
                    """,
                    [name_query, family_code, record_status, date_from, date_to],
                )
                return cur.fetchone()[0]
        except (ProgrammingError, PGUndefinedFunction):
            return 0
        

class MaternalHealthDetailRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_health_record(p_maternal_health_id INT).

    We only use the static get_by_id() helper; Django never touches db_table.
    """
    maternal_health_id = models.IntegerField(primary_key=True)
    maternal_id = models.IntegerField()
    registration_date = models.DateTimeField()
    family_code = models.TextField()
    nhts_status = models.BooleanField()
    full_name = models.TextField()
    dob = models.DateField()
    age_years = models.IntegerField()
    full_address = models.TextField()
    address_landmark = models.TextField(null=True)
    phone_number = models.TextField(null=True)

    class Meta:
        managed = False
        # Just a label – there is no physical table with this name
        db_table = "view_specific_maternal_health_record_row"

    @staticmethod
    def get_by_id(maternal_health_id: int) -> Optional[Dict[str, Any]]:
        """
        Call: SELECT * FROM view_specific_maternal_health_record(%s)
        Returns a dict or None if not found / function missing.
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      maternal_health_id,
                      maternal_id,
                      registration_date,
                      family_code,
                      nhts_status,
                      full_name,
                      dob,
                      age_years,
                      full_address,
                      address_landmark,
                      phone_number
                    FROM view_specific_maternal_health_record(%s)
                    """,
                    [maternal_health_id],
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [c[0] for c in cur.description]
                return dict(zip(cols, row))
        except (ProgrammingError, PGUndefinedFunction, DatabaseError):
            # Function missing or custom P4B01 error etc.
            return None


class ObstetricalHistoryRow(models.Model):
    """
    Unmanaged model backed by view_obstetrical_history(p_maternal_health_id).
    Used for the Obstetrical History modal.
    """
    obs_id = models.IntegerField(primary_key=True)
    gravida = models.IntegerField(null=True)
    para = models.IntegerField(null=True)
    abortion = models.IntegerField(null=True)
    last_menstrual_period = models.DateField(null=True)
    expected_date_of_delivery = models.DateField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "view_obstetrical_history_row"  # label only

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> List[Dict[str, Any]]:
        """
        SELECT * FROM view_obstetrical_history(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      obs_id,
                      gravida,
                      para,
                      abortion,
                      last_menstrual_period,
                      expected_date_of_delivery,
                      created_at
                    FROM view_obstetrical_history(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []
        

class MaternalMedicalConditionRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_all_medical_condition(p_maternal_health_id).
    Used for the Medical Conditions table in the Medical/Surgical modal.
    """
    mmh_id = models.IntegerField(primary_key=True)
    m_medical_history_name = models.TextField()
    date_added = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "view_specific_maternal_all_medical_condition_row"  # label only

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> List[Dict[str, Any]]:
        """
        SELECT * FROM view_specific_maternal_all_medical_condition(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      mmh_id,
                      m_medical_history_name,
                      date_added
                    FROM view_specific_maternal_all_medical_condition(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []


class MaternalSurgicalHistoryRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_all_surgical_history(p_maternal_health_id).
    Used for the Surgical History table in the Medical/Surgical modal.
    """
    msh_id = models.IntegerField(primary_key=True)
    m_surgical_history_name = models.TextField()
    date_of_surgery = models.DateField(null=True)
    date_added = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "view_specific_maternal_all_surgical_history_row"  # label only

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> List[Dict[str, Any]]:
        """
        SELECT * FROM view_specific_maternal_all_surgical_history(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      msh_id,
                      m_surgical_history_name,
                      date_of_surgery,
                      date_added
                    FROM view_specific_maternal_all_surgical_history(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []
        

class MaternalImmunizationStatusTrackRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_immunization_status_track(p_maternal_health_id).
    Used for the Maternal Immunization modal.
    """
    immu_status_track_id = models.IntegerField(primary_key=True)

    # Adjust field types/names if your view returns different columns
    first_dose = models.BooleanField(null=True)
    first_dose_date = models.DateField(null=True)

    second_dose = models.BooleanField(null=True)
    second_dose_date = models.DateField(null=True)

    third_dose = models.BooleanField(null=True)
    third_dose_date = models.DateField(null=True)

    fourth_dose = models.BooleanField(null=True)
    fourth_dose_date = models.DateField(null=True)

    fifth_dose = models.BooleanField(null=True)
    fifth_dose_date = models.DateField(null=True)

    fim_status = models.BooleanField(null=True)
    updated_at = models.DateTimeField(null=True)

    class Meta:
        managed = False
        # just a label so Django stops trying to create a real table
        db_table = "view_specific_maternal_immunization_status_track_row"

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> Optional[Dict[str, Any]]:
        """
        SELECT * FROM view_specific_maternal_immunization_status_track(%s)
        Returns a single dict (or None if no row).
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      immu_status_track_id,
                      first_dose,
                      first_dose_date,
                      second_dose,
                      second_dose_date,
                      third_dose,
                      third_dose_date,
                      fourth_dose,
                      fourth_dose_date,
                      fifth_dose,
                      fifth_dose_date,
                      fim_status,
                      updated_at
                    FROM view_specific_maternal_immunization_status_track(%s)
                    """,
                    [maternal_health_id],
                )
                row = cur.fetchone()
                if not row:
                    return None
                cols = [c[0] for c in cur.description]
                return dict(zip(cols, row))
        except (ProgrammingError, PGUndefinedFunction):
            return None
        

class MaternalDiseaseSurveillanceRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_all_disease_surveillance(p_maternal_health_id).
    Used for the Infectious Disease Screening modal.
    """
    ids_id = models.IntegerField(primary_key=True)
    disease_type_id = models.IntegerField()
    disease_name = models.TextField()
    screening_date = models.DateField(null=True)
    result = models.TextField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        # Just a label; Django will not actually query this table name because
        # we're using a raw SQL function in fetch_for_mhr.
        db_table = "view_specific_maternal_all_disease_surveillance_row"

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> list[dict]:
        """
        SELECT * FROM view_specific_maternal_all_disease_surveillance(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      ids_id,
                      disease_type_id,
                      disease_name,
                      screening_date,
                      result,
                      created_at
                    FROM view_specific_maternal_all_disease_surveillance(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []
        

class MaternalLaboratoryScreeningRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_all_laboratory_screening(p_maternal_health_id).
    Used for the nested Lab Screening Result modal inside the Lab Screening + Iron modal.
    """
    lab_screening_id = models.IntegerField(primary_key=True)
    test_type_id = models.IntegerField()
    test_name = models.TextField()
    test_date = models.DateField(null=True)
    result = models.TextField(null=True)
    iron_tablet_given_date = models.DateField(null=True)
    iron_tablet_quantity = models.IntegerField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        # Label only – we never query this table name directly.
        db_table = "view_specific_maternal_all_laboratory_screening_row"

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> list[dict]:
        """
        SELECT * FROM view_specific_maternal_all_laboratory_screening(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      lab_screening_id,
                      test_type_id,
                      test_name,
                      test_date,
                      result,
                      iron_tablet_given_date,
                      iron_tablet_quantity,
                      created_at
                    FROM view_specific_maternal_all_laboratory_screening(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []


class MaternalCheckupRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_all_checkup_record(p_maternal_health_id).
    Used for the Check Ups modal.
    """
    checkup_id = models.IntegerField(primary_key=True)
    trimester_name = models.TextField()
    date_of_checkup = models.DateField(null=True)
    aog_weeks = models.IntegerField(null=True)
    weight_kg = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    height_cm = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    bmi = models.DecimalField(max_digits=6, decimal_places=2, null=True)
    blood_pressure = models.CharField(max_length=50, null=True)
    fetal_heart_rate = models.IntegerField(null=True)
    laboratory_results = models.TextField(null=True)
    notes = models.TextField(null=True)
    date_of_visit = models.DateTimeField(null=True)

    class Meta:
        managed = False
        db_table = "view_specific_maternal_all_checkup_record_row"  # label only

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> list[dict]:
        """
        SELECT * FROM view_specific_maternal_all_checkup_record(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      checkup_id,
                      trimester_name,
                      date_of_checkup,
                      aog_weeks,
                      weight_kg,
                      height_cm,
                      bmi,
                      blood_pressure,
                      fetal_heart_rate,
                      laboratory_results,
                      notes,
                      date_of_visit
                    FROM view_specific_maternal_all_checkup_record(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []



class MaternalSupplementRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_all_supplements_record(p_maternal_health_id).
    Used for the Supplements modal.
    """
    maternal_supplement_id = models.IntegerField(primary_key=True)
    supplement_type_id = models.IntegerField()
    supplement_name = models.TextField()
    date_given = models.DateField(null=True)
    number_of_tablets = models.IntegerField(null=True)
    trimester_name = models.TextField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        # Label only – we never query this table name directly.
        db_table = "view_specific_maternal_all_supplements_record_row"

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> List[Dict[str, Any]]:
        """
        SELECT * FROM view_specific_maternal_all_supplements_record(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      maternal_supplement_id,
                      supplement_type_id,
                      supplement_name,
                      date_given,
                      number_of_tablets,
                      trimester_name,
                      created_at
                    FROM view_specific_maternal_all_supplements_record(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []

class MaternalDeliveryOutcomeRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_delivery_outcome(p_maternal_health_id).
    Used for the Delivery Outcome modal.
    """
    outcome_id = models.IntegerField(primary_key=True)
    outcome_type = models.TextField()
    delivery_type = models.TextField()
    place_delivery_type = models.TextField()
    ownership_type = models.TextField(null=True)
    others_description = models.TextField(null=True)
    birth_attendant = models.TextField()
    other_attendant = models.TextField(null=True)
    time_of_delivery = models.TimeField(null=True)
    date_terminated = models.DateField(null=True)
    recorded_by = models.IntegerField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        # Label only – we never query this name directly.
        db_table = "view_specific_maternal_delivery_outcome_row"

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> list[dict]:
        """
        SELECT * FROM view_specific_maternal_delivery_outcome(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      outcome_id,
                      outcome_type,
                      delivery_type,
                      place_delivery_type,
                      ownership_type,
                      others_description,
                      birth_attendant,
                      other_attendant,
                      time_of_delivery,
                      date_terminated,
                      recorded_by,
                      created_at
                    FROM view_specific_maternal_delivery_outcome(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []


class MaternalPostpartumVisitRow(models.Model):
    """
    Unmanaged model backed by view_specific_maternal_all_postpartum_visit(p_maternal_health_id).
    Used for the Postpartum Visit modal.
    """
    postpartum_id = models.IntegerField(primary_key=True)
    date_of_visit = models.DateField(null=True)
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    blood_pressure = models.TextField(null=True)
    notes = models.TextField(null=True)
    laboratory_notes = models.TextField(null=True)
    recorded_by = models.IntegerField(null=True)
    created_at = models.DateTimeField()

    class Meta:
        managed = False
        db_table = "view_specific_maternal_all_postpartum_visit_row"  # label only

    @staticmethod
    def fetch_for_mhr(maternal_health_id: int) -> List[Dict[str, Any]]:
        """
        SELECT * FROM view_specific_maternal_all_postpartum_visit(%s)
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                      postpartum_id,
                      date_of_visit,
                      weight_kg,
                      height_cm,
                      blood_pressure,
                      notes,
                      laboratory_notes,
                      recorded_by,
                      created_at
                    FROM view_specific_maternal_all_postpartum_visit(%s)
                    """,
                    [maternal_health_id],
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except (ProgrammingError, PGUndefinedFunction):
            return []
        

class DiseaseType(models.Model):
    """
    Simple unmanaged model for Disease_Type table, used to populate the
    Infectious Disease Screening add-form dropdown.
    """
    disease_type_id = models.IntegerField(primary_key=True)
    disease_name = models.CharField(max_length=100)
    is_active = models.BooleanField()

    class Meta:
        managed = False
        db_table = "disease_type"

    @staticmethod
    def fetch_active() -> List[Dict[str, Any]]:
        """
        SELECT active disease types ordered by name.
        """
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT disease_type_id, disease_name, is_active
                    FROM disease_type
                    WHERE is_active IS TRUE
                    ORDER BY disease_name ASC
                    """
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except ProgrammingError:
            return []
        

class DiseaseTypeRow(models.Model):
    """
    Simple unmanaged model to read from Disease_Type reference table.
    Used for the Add Infectious Disease Screening modal.
    """
    disease_type_id = models.IntegerField(primary_key=True)
    disease_name = models.TextField()

    class Meta:
        managed = False
        db_table = "disease_type"  # exact table name in SQL: Disease_Type

    @staticmethod
    def fetch_all() -> list[dict]:
        from django.db import connection, ProgrammingError
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT disease_type_id, disease_name
                    FROM Disease_Type
                    ORDER BY disease_name
                    """
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except ProgrammingError:
            return []


class TestTypeRow(models.Model):
    """
    Simple unmanaged model to read from Test_Type reference table.
    Used for the Add Lab Screening form.
    """
    test_type_id = models.IntegerField(primary_key=True)
    test_name = models.TextField()

    class Meta:
        managed = False
        db_table = "Test_Type"  # exact SQL table name

    @staticmethod
    def fetch_all() -> list[dict]:
        from django.db import connection, ProgrammingError
        try:
            with connection.cursor() as cur:
                cur.execute(
                    """
                    SELECT test_type_id, test_name
                    FROM Test_Type
                    ORDER BY test_name
                    """
                )
                cols = [c[0] for c in cur.description]
                return [dict(zip(cols, row)) for row in cur.fetchall()]
        except ProgrammingError:
            return []
