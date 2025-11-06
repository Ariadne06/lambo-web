from django.db import models, connection
import json
from typing import Optional, List, Dict, Any
from decimal import Decimal, InvalidOperation
from datetime import datetime, date

class Secretary(models.Model):
    class Meta:
        managed = False

    @staticmethod
    def sp_get_pending_supporting_certificates(query, limit, offset, sort_by, sort_dir):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_pending_supporting_certificates', [query, limit, offset, sort_by, sort_dir])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e

    @staticmethod
    def sp_review_resident_supporting_certificate(rid, doc_type_id, review_status, pid, review_notes, review_action):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('review_resident_supporting_certificate', [rid, doc_type_id, review_status, pid, review_notes, review_action])
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e

    @staticmethod
    def sp_register_business(
        resident_id,
        business_name,
        business_type_id,
        nature_of_business,
        ownership_id,
        house_number,
        street,
        barangay,
        sitio_id,
        city_municipality,
        country,
        total_gross_income,
        dti_sec_cda_reg_number,   # optional
        clearance_category_id,    # required
        total_units,              # <-- NEW (optional; may be None)
        clearance_date_issued,    # optional
        created_by,
    ):
        """
        Calls register_business(...) which expects p_total_units
        BETWEEN p_clearance_category_id and p_clearance_date_issued.
        """
        with connection.cursor() as cursor:
            cursor.callproc(
                'register_business',
                [
                    resident_id,
                    business_name,
                    business_type_id,
                    nature_of_business,
                    ownership_id,
                    house_number,
                    street,
                    barangay,
                    sitio_id,
                    city_municipality,
                    country,
                    total_gross_income,
                    dti_sec_cda_reg_number,  # may be None
                    clearance_category_id,
                    total_units,              # <-- keep position in sync with SQL
                    clearance_date_issued,    # may be None
                    created_by,
                ],
            )
            result = cursor.fetchone()
            return result[0]
        

class Business(models.Model):
    class Meta:
        managed = False

    @staticmethod
    def sp_business_clearance_category():
            """
            Returns [(clearance_category_id, category_name), ...]
            from business_clearance_category().
            """
            try:
                with connection.cursor() as cursor:
                    cursor.callproc('business_clearance_category', [])
                    cols = [c[0] for c in cursor.description]
                    return [dict(zip(cols, row)) for row in cursor.fetchall()]
            except Exception as e:
                raise e
        
    @staticmethod
    def sp_get_business_clearance_categories_for_select():
        """
        Calls get_business_clearance_categories_for_select()
        and returns a list of dicts with clearance_category_id, category_name.
        """
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_business_clearance_categories_for_select', [])
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except Exception as e:
            raise e

    @staticmethod
    def sp_get_all_businesses(query=None, status=None, type_id=None, ownership_id=None, owner_id=None, limit=10, offset=0):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_all_businesses', [query, status, type_id, ownership_id, owner_id, limit, offset])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e

    @staticmethod
    def sp_get_business_detail(business_id: int):
        """Fetch full details of a business for the modal view."""
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_business_detail', [business_id])
                cols = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e

    @staticmethod
    def sp_search_business_owner(query, limit=10, offset=0):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('search_business_owner', [query, limit, offset])
                cols = [c[0] for c in cursor.description]
                return [dict(zip(cols, row)) for row in cursor.fetchall()]
        except Exception as e:
            raise e

    @staticmethod
    def sp_update_business(
        business_id: int,
        business_name=None,
        business_type_id=None,       # kept for server-side rule checks (not editable)
        nature_of_business=None,
        ownership_id=None,           # kept for server-side rule checks (not editable)
        resident_id=None,            # optional owner transfer (only if allowed)
        house_number=None,
        street=None,
        barangay=None,
        sitio_id=None,
        city_municipality=None,
        country=None,
        total_gross_income=None,
        clearance_category_id=None,  # may be None
        dti_sec_cda_reg_number=None, # not editable
        total_units=None,            # <-- NEW (may be None)
        updated_by: int = None,
    ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'update_business',
                    [
                        business_id,            # p_business_id
                        business_name,          # p_business_name
                        nature_of_business,     # p_nature_of_business
                        business_type_id,       # p_business_type_id (NOT editable by rule)
                        ownership_id,           # p_ownership_id     (NOT editable by rule)
                        dti_sec_cda_reg_number, # p_dti_sec_cda_reg_number (NOT editable)
                        resident_id,            # p_resident_id
                        house_number,           # p_house_number
                        street,                 # p_street
                        barangay,               # p_barangay
                        sitio_id,               # p_sitio_id
                        city_municipality,      # p_city_municipality
                        country,                # p_country
                        total_gross_income,     # p_total_gross_income
                        clearance_category_id,  # p_clearance_category_id
                        total_units,            # p_total_units  <-- keep position in sync
                        updated_by,             # p_updated_by
                    ],
                )
                row = cursor.fetchone()
                return row[0] if row else "OK"
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_set_closed_business(business_id: int, updated_by: int):
        """
        Calls set_closed_business(p_business_id, p_updated_by) in PostgreSQL.
        Returns the TEXT message from the function.
        """
        try:
            with connection.cursor() as cursor:
                cursor.callproc("set_closed_business", [business_id, updated_by])
                row = cursor.fetchone()
                # DB function returns TEXT message
                return str(row[0]) if row and len(row) > 0 else "Business marked as Closed"
        except Exception as e:
            # Bubble up so the view can format a clean error
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
    


class BusinessFee(models.Model):
    """
    Thin wrapper that fetches rows from get_all_business_clearance_cat().
    Returns a list[dict] so templates can access keys directly.
    """
    class Meta:
        managed = False  # no ORM migrations; we’re calling a function

    @staticmethod
    def sp_get_all_business_clearance_cat():
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_all_business_clearance_cat()")
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]

    @staticmethod
    def sp_get_specific_business_clearance_cat(clearance_category_id: int):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM get_specific_business_clearance_cat(%s)",
                [clearance_category_id],
            )
            cols = [c[0] for c in cursor.description]
            row = cursor.fetchone()
            return dict(zip(cols, row)) if row else None

    @staticmethod
    def sp_update_business_clearance_category(
        clearance_category_id: int,
        base_fee,
        additional_fee_per_unit,
        minimum_units,
        updated_by: int,
    ) -> str:
        """
        Calls update_business_clearance_category(...) which returns TEXT.
        Pass None for any field you don't want to change.
        """
        with connection.cursor() as cursor:
            cursor.callproc(
                "update_business_clearance_category",
                [clearance_category_id, base_fee, additional_fee_per_unit, minimum_units, updated_by],
            )
            msg = cursor.fetchone()[0]  # function returns TEXT
            return msg
        
class AmusementDeviceType(models.Model):
    """
    Thin wrapper around your Postgres functions.
    """
    class Meta:
        managed = False

    @staticmethod
    def sp_get_all_amusement_device_type():
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_all_amusement_device_type()")
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]

    @staticmethod
    def sp_get_specific_amusement_device_type(device_type_id: int):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM get_specific_amusement_device_type(%s)",
                [device_type_id],
            )
            cols = [c[0] for c in cursor.description]
            row = cursor.fetchone()
            return dict(zip(cols, row)) if row else None

    @staticmethod
    def sp_update_amusement_device_type(
        device_type_id: int,
        fee_per_unit,
        updated_by: int,
    ) -> str:
        """
        Calls update_amusement_device_type(...) which returns TEXT.
        Pass None for any field you don't want to change (only fee_per_unit here).
        """
        with connection.cursor() as cursor:
            cursor.callproc(
                "update_amusement_device_type",
                [device_type_id, fee_per_unit, updated_by],
            )
            msg = cursor.fetchone()[0]
            return msg
        
class OtherClearanceType(models.Model):
    """
    Wrapper over Postgres functions for 'other barangay clearances'.
    """
    class Meta:
        managed = False

    @staticmethod
    def sp_get_all_other_barangay_clearance_type():
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM get_all_other_barangay_clearance_type()")
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, r)) for r in cursor.fetchall()]

    @staticmethod
    def sp_get_specific_other_barangay_clearance_type(clearance_type_id: int):
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM get_specific_other_barangay_clearance_type(%s)",
                [clearance_type_id],
            )
            cols = [c[0] for c in cursor.description]
            row = cursor.fetchone()
            return dict(zip(cols, row)) if row else None

    @staticmethod
    def sp_update_other_barangay_clearance_type(
        clearance_type_id: int,
        fee,
        updated_by: int,
    ) -> str:
        with connection.cursor() as cursor:
            cursor.callproc(
                "update_other_barangay_clearance_type",
                [clearance_type_id, fee, updated_by],
            )
            return cursor.fetchone()[0]  # TEXT message
        
class BusinessTaxConfig(models.Model):
    class Meta:
        managed = False

    @staticmethod
    def sp_get_current_business_tax_config():
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_current_business_tax_config()")
            cols = [c[0] for c in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None

    @staticmethod
    def sp_update_business_tax_config(
        config_id,
        threshold_amount,
        rate_percent_at_or_below,
        rate_percent_above,
        window_month_start,  # int or None
        window_month_end,    # int or None
        monthly_interest_percent,
        updated_by
    ) -> str:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT update_business_tax_config(
                    %s::int,
                    %s::numeric,
                    %s::numeric,
                    %s::numeric,
                    %s::smallint,
                    %s::smallint,
                    %s::numeric,
                    %s::int
                )
                """,
                [
                    config_id,
                    threshold_amount,
                    rate_percent_at_or_below,
                    rate_percent_above,
                    window_month_start,   # cast to ::smallint in SQL
                    window_month_end,     # cast to ::smallint in SQL
                    monthly_interest_percent,
                    updated_by,
                ],
            )
            return cur.fetchone()[0]
        

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
    def _dictfetchall(cur) -> List[Dict]:
        cols = [c[0] for c in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def list_all(q: Optional[str] = None,
                 date_from: Optional[date] = None,
                 date_to: Optional[date] = None,
                 created_by: Optional[int] = None,
                 sort: str = 'date_desc',
                 limit: int = 100, offset: int = 0,
                 audience: Optional[str] = None) -> List[Dict]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_all_announcement(%s,%s,%s,%s,%s,%s,%s,%s)",
                [q, date_from, date_to, created_by, sort, limit, offset, audience]
            )
            return AnnouncementRepo._dictfetchall(cur)
        
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

    @staticmethod
    def get_one(announcement_id: int) -> Optional[Dict]:
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_specific_announcement(%s)", [announcement_id])
            rows = AnnouncementRepo._dictfetchall(cur)
            return rows[0] if rows else None

    @staticmethod
    def create(header_title: str, details: str,
               image_path: Optional[str],
               created_by: int,
               event_date: Optional[date] = None,
               audience: Optional[str] = None) -> int:
        """
        audience: 'resident' | 'personnel' | 'both'
        Insert uses CURRENT_DATE for `date`. If an event_date is provided,
        we set it right after insert via direct UPDATE.
        """
        with connection.cursor() as cur:
            cur.execute(
                "SELECT insert_announcement(%s,%s,%s,%s,%s)",
                [header_title, details, image_path, created_by, audience]
            )
            new_id = cur.fetchone()[0]
            if event_date:
                cur.execute("UPDATE Announcement SET date=%s WHERE announcement_id=%s", [event_date, new_id])
        return new_id

    @staticmethod
    def update(announcement_id: int, updated_by: int,
               header_title: Optional[str] = None,
               details: Optional[str] = None,
               image_path: Optional[str] = None,
               event_date: Optional[date] = None,
               audience: Optional[str] = None) -> bool:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT update_announcement(%s,%s,%s,%s,%s,%s)",
                [announcement_id, updated_by, header_title, details, image_path, audience]
            )
            changed = cur.fetchone()[0]
            if event_date is not None:   # allow clearing by sending empty
                cur.execute("UPDATE Announcement SET date=%s WHERE announcement_id=%s", [event_date, announcement_id])
        return changed

    @staticmethod
    def delete(announcement_id: int, deleted_by: int) -> bool:
        with connection.cursor() as cur:
            try:
                cur.execute("SELECT delete_announcement(%s,%s)", [announcement_id, deleted_by])
                row = cur.fetchone()
                return bool(row[0]) if row else True
            except Exception:
                try:
                    cur.execute("""
                        UPDATE Announcement
                           SET is_deleted = TRUE,
                               deleted_by = %s,
                               deleted_at = LOCALTIMESTAMP
                         WHERE announcement_id = %s
                    """, [deleted_by, announcement_id])
                    return True
                except Exception:
                    cur.execute("DELETE FROM Announcement WHERE announcement_id = %s", [announcement_id])
                    return True
    

# --- Backwards-compatible helper container ---
class SecretaryHelpers:
    """Container class placed at the end of this file that groups the
    thin DB helper wrappers. This keeps new helpers appended (to reduce
    merge conflicts) while grouping them in a single namespace as
    requested.

    Usage examples (prefer explicit class staticmethod calls from views):
        BusinessFee.sp_get_fee_types_dropdown()
        SecretaryHelpers.get_fee_types_dropdown()
    """

    @staticmethod
    def get_fee_types_dropdown() -> list[dict]:
        """Return fee_type_id / fee_type_name directly from SQL function.

        Uses: SELECT * FROM get_fee_types_dropdown()
        """
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_fee_types_dropdown()")
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def get_other_clearance_purposes_dropdown() -> list[dict]:
        """Return other_clearance_id / purpose_name using the DB helper.

        Delegates to OtherClearanceType.sp_get_other_clearance_purposes_dropdown().
        """
        return OtherClearanceType.sp_get_other_clearance_purposes_dropdown()

    @staticmethod
    def search_owner(p_query: Optional[str], p_limit: int = 25, p_offset: int = 0) -> list[dict]:
                """Call the DB function search_owner(p_query, p_limit, p_offset) and map rows.

                Returns: list of dicts with keys
                    business_id, business_name, business_status, owner_resident_id, owner_full_name
                """
                with connection.cursor() as cur:
                        cur.callproc('search_owner', [p_query, p_limit, p_offset])
                        cols = [c[0] for c in cur.description]
                        return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def search_resident(p_query: Optional[str], p_limit: int = 25, p_offset: int = 0) -> list[dict]:
        """Call search_resident(...) and return rows as list[dict].

        Delegates to Secretary.sp_search_resident().
        """
        return Secretary.sp_search_resident(p_query, p_limit, p_offset)

    @staticmethod
    def secretary_preview_business_clearance(
        p_business_id: int,
        p_purpose: Optional[str] = None,
        p_videoke_qty: Optional[int] = None,
        p_billiard_qty: Optional[int] = None,
        p_other_device_qty: Optional[int] = None,
    ) -> dict:
        """Call the DB function secretary_preview_business_clearance(...) and return a mapped dict."""
        with connection.cursor() as cur:
            cur.callproc('secretary_preview_business_clearance', [
                p_business_id, p_purpose, p_videoke_qty, p_billiard_qty, p_other_device_qty
            ])
            cols = [c[0] for c in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None

    @staticmethod
    def create_application_business(
        fee_type_id: int,
        business_id: int,
        business_clearance_category: int,
        videoke_qty: Optional[int] = None,
        billiard_qty: Optional[int] = None,
        other_device_qty: Optional[int] = None,
        purpose: Optional[str] = None,
        requested_by: Optional[str] = 'personnel',
        date_submitted: Optional[datetime] = None,
    ) -> Optional[int]:
        """Call Create_Application_Business and return the new application_id.

        SQL signature (defaults handled in DB):
          Create_Application_Business(
            p_fee_type_id INT,
            p_business_id INT,
            p_business_clearance_category INT,
            p_videoke_quantity INT DEFAULT NULL,
            p_billiard_quantity INT DEFAULT NULL,
            p_other_device_quantity INT DEFAULT NULL,
            p_purpose TEXT DEFAULT NULL,
            p_requested_by TEXT DEFAULT NULL,
            p_date_submitted TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
          ) RETURNS INT
        """
        with connection.cursor() as cur:
            if date_submitted is not None:
                cur.execute(
                    "SELECT Create_Application_Business(%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    [
                        fee_type_id,
                        business_id,
                        business_clearance_category,
                        videoke_qty,
                        billiard_qty,
                        other_device_qty,
                        purpose,
                        requested_by,
                        date_submitted,
                    ],
                )
            else:
                cur.execute(
                    "SELECT Create_Application_Business(%s,%s,%s,%s,%s,%s,%s,%s)",
                    [
                        fee_type_id,
                        business_id,
                        business_clearance_category,
                        videoke_qty,
                        billiard_qty,
                        other_device_qty,
                        purpose,
                        requested_by,
                    ],
                )
            row = cur.fetchone()
            return int(row[0]) if row and row[0] is not None else None

    # ---- Applications listing/detail/status helpers ----
    @staticmethod
    def list_all_applications(p_query: Optional[str] = None, p_limit: int = 50, p_offset: int = 0) -> list[dict]:
        """Wrapper for get_all_application(p_query, p_limit, p_offset)."""
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_all_application(%s,%s,%s)", [p_query, p_limit, p_offset])
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, row)) for row in cur.fetchall()]

    @staticmethod
    def count_all_applications(p_query: Optional[str] = None) -> int:
        """Count rows via SELECT COUNT(*) FROM get_all_application(...)."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM get_all_application(%s,%s,%s)",
                [p_query, 1_000_000_000, 0]
            )
            return int(cur.fetchone()[0])

    @staticmethod
    def get_specific_application(application_id: int) -> Optional[dict]:
        """Wrapper for get_specific_application(application_id)."""
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM get_specific_application(%s)", [application_id])
            cols = [c[0] for c in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None

    @staticmethod
    def set_application_to_for_payment(application_id: int) -> None:
        """Wrapper for set_application_to_for_payment(application_id). Returns None; raises on error."""
        with connection.cursor() as cur:
            cur.execute("SELECT set_application_to_for_payment(%s)", [application_id])

    @staticmethod
    def get_clearance_details_for_printing(application_id: int) -> Optional[dict]:
        """Call get_clearance_details_for_printing and return a single dict row."""
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_clearance_details_for_printing(%s)",
                [application_id]
            )
            cols = [c[0] for c in cur.description]
            row = cur.fetchone()
            return dict(zip(cols, row)) if row else None

    
