from django.db import models, connection
import json
from typing import Optional, List, Dict, Any

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
    def sp_review_resident_supporting_certificate(rid, doc_type_id, review_status, review_notes, pid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('review_resident_supporting_certificate', [rid, doc_type_id, review_status, review_notes, pid])
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
    def sp_register_business(resident_id,
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
                    dti_sec_cda_reg_number,
                    clearance_date_issued,
                    created_by,):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('register_business', [resident_id,
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
                    dti_sec_cda_reg_number,
                    clearance_date_issued,
                    created_by,])
                result = cursor.fetchone()
                return result[0]
        except Exception as e:
            raise e
        
class Business(models.Model):
    class Meta:
        managed = False

    @staticmethod
    def sp_get_all_businesses(query=None, status=None, type_id=None, ownership_id=None, owner_id=None, limit=10, offset=0):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'get_all_businesses',
                    [query, status, type_id, ownership_id, owner_id, limit, offset]
                )
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
        with connection.cursor() as cursor:
            cursor.callproc('search_business_owner', [query, limit, offset])
            cols = [c[0] for c in cursor.description]
            return [dict(zip(cols, row)) for row in cursor.fetchall()]

    from django.db import models, connection
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
    def sp_review_resident_supporting_certificate(rid, doc_type_id, review_status, review_notes, pid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('review_resident_supporting_certificate', [rid, doc_type_id, review_status, review_notes, pid])
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
        dti_sec_cda_reg_number,
        clearance_date_issued,
        created_by,
    ):
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
                        dti_sec_cda_reg_number,
                        clearance_date_issued,
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
        business_type_id=None,
        nature_of_business=None,
        ownership_id=None,
        resident_id=None,          # optional owner transfer
        house_number=None,
        street=None,
        barangay=None,
        sitio_id=None,
        city_municipality=None,
        country=None,
        total_gross_income=None,
        dti_sec_cda_reg_number=None,
        updated_by: int = None,
    ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    'update_business',
                    [
                        business_id,
                        business_name,
                        business_type_id,
                        nature_of_business,
                        ownership_id,
                        resident_id,
                        house_number,
                        street,
                        barangay,
                        sitio_id,
                        city_municipality,
                        country,
                        total_gross_income,
                        dti_sec_cda_reg_number,
                        updated_by,
                    ],
                )
                row = cursor.fetchone()
                return row[0] if row else "OK"
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_set_closed_business(business_id: int, updated_by: int):
        try:
            with connection.cursor() as cursor:
                cursor.callproc("set_closed_business", [business_id, updated_by])
                row = cursor.fetchone()
                if row and len(row) > 0:
                    return str(row[0])
                return "Business marked as Closed"
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