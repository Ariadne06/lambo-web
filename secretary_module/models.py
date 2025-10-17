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
    def sp_register_verified_via_guardian_doc(rid, doc_type_id, review_status, review_notes, pid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('register_verified_via_guardian_doc', [rid, doc_type_id, review_status, review_notes, pid])
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
        dti_sec_cda_reg_number,   # optional (can be None)
        clearance_category_id,    # NEW required param
        clearance_date_issued,    # optional
        created_by,
    ):
        """
        Calls register_business(...) which expects p_clearance_category_id
        immediately after p_dti_sec_cda_reg_number.
        """
        try:
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
                        clearance_category_id,   # <-- inserted here
                        clearance_date_issued,   # may be None
                        created_by,
                    ],
                )
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e
    

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
        clearance_category_id=None,  # <-- NEW param (can be None)
        dti_sec_cda_reg_number=None, # not editable; pass None
        updated_by: int = None,
    ):
        try:
            with connection.cursor() as cursor:
                # ORDER MUST MATCH THE SQL FUNCTION SIGNATURE
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
      - insert_announcement(title, details, image_path, created_by) -> INT
      - get_all_announcement(q, date_from, date_to, created_by, sort, limit, offset) -> rows
      - get_specific_announcement(id) -> single row (id, header_title, details, announcement_image_path, date, updated_at, created_by)
      - update_announcement(id, updated_by, title?, details?, image_path?) -> BOOLEAN
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
                 limit: int = 100, offset: int = 0) -> List[Dict]:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT * FROM get_all_announcement(%s,%s,%s,%s,%s,%s,%s)",
                [q, date_from, date_to, created_by, sort, limit, offset]
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
               event_date: Optional[date] = None) -> int:
        """
        Insert uses CURRENT_DATE for `date`. If an event_date is provided,
        we set it right after insert via direct UPDATE.
        """
        with connection.cursor() as cur:
            cur.execute(
                "SELECT insert_announcement(%s,%s,%s,%s)",
                [header_title, details, image_path, created_by]
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
               event_date: Optional[date] = None) -> bool:
        with connection.cursor() as cur:
            cur.execute(
                "SELECT update_announcement(%s,%s,%s,%s,%s)",
                [announcement_id, updated_by, header_title, details, image_path]
            )
            changed = cur.fetchone()[0]
            if event_date is not None:   # allow clearing by sending empty
                cur.execute("UPDATE Announcement SET date=%s WHERE announcement_id=%s", [event_date, announcement_id])
        return changed
    
    @staticmethod
    def delete(announcement_id: int, deleted_by: int) -> bool:
        """
        Tries to call stored function delete_announcement(id, deleted_by).
        If it doesn't exist, falls back to soft delete (if columns exist) or hard delete.
        """
        with connection.cursor() as cur:
            # 1) try stored function
            try:
                cur.execute("SELECT delete_announcement(%s,%s)", [announcement_id, deleted_by])
                row = cur.fetchone()
                return bool(row[0]) if row else True
            except Exception:
                # 2) try soft delete (if columns exist)
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
                    # 3) hard delete
                    cur.execute("DELETE FROM Announcement WHERE announcement_id = %s", [announcement_id])
                    return True



