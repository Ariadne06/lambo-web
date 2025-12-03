from django.db import models, connection
import json
from typing import Optional, List, Dict, Any
from datetime import datetime, date

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
    
    @staticmethod
    def bhw_dashboard(personnel_id: int, quarter_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Wrapper for:

            SELECT * FROM bhw_dashboard(%s, %s);

        See BHW_DASHBOARD.sql for the full list of returned columns.
        """
        with connection.cursor() as cur:
            cur.execute("SELECT * FROM bhw_dashboard(%s, %s);", [personnel_id, quarter_id])
            row = cur.fetchone()
            if not row:
                return {}

            cols = [c[0] for c in cur.description]
            result = dict(zip(cols, row))

        # Normalize households_per_purok JSONB -> Python list[dict]
        val = result.get("households_per_purok")
        if val is None:
            result["households_per_purok"] = []
        elif isinstance(val, list):
            # already decoded
            pass
        elif isinstance(val, (bytes, bytearray)):
            result["households_per_purok"] = json.loads(val.decode("utf-8"))
        elif hasattr(val, "tobytes"):
            result["households_per_purok"] = json.loads(val.tobytes().decode("utf-8"))
        elif isinstance(val, str):
            result["households_per_purok"] = json.loads(val)
        else:
            result["households_per_purok"] = []

        return result
    
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
    
class Child(models.Model):

    class Meta:
        managed = False
    
    @staticmethod
    def sp_view_all_child_health_record(
            query,
            sitio_id,
            sex,
            limit,
            offset
        ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_all_child_health_record', [
                    query,
                    sitio_id,
                    sex,
                    limit,
                    offset
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_insert_child_health_record(
            child_id,
            time_of_birth,
            birth_weight,
            birth_height,
            place_of_delivery,
            address_landmark,
            tt_status_mother,
            tt_status_date,
            newborn_screening_status,
            newborn_screening_date,
            feeding_method,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_child_health_record', [
                    child_id,
                    time_of_birth,
                    birth_weight,
                    birth_height,
                    place_of_delivery,
                    address_landmark,
                    tt_status_mother,
                    tt_status_date,
                    newborn_screening_status,
                    newborn_screening_date,
                    feeding_method,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_specific_child_health_record(child_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_child_health_record', [child_health_id])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_specific_child_all_medical_condition(child_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_child_all_medical_condition', [
                    child_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_specific_child_all_surgical_history(child_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_child_all_surgical_history', [
                    child_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_add_child_medical_condition(
            child_health_id,
            medical_condition,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_child_medical_condition', [
                    child_health_id,
                    medical_condition,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_add_child_surgical_history(
            child_health_id,
            surgical_history_name,
            date_of_surgery,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_child_surgical_history', [
                    child_health_id,
                    surgical_history_name,
                    date_of_surgery,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_update_child_health_record(
            child_health_id,
            place_of_delivery,
            address_landmark,
            tt_status_of_mother,
            tt_status_date,
            newborn_screening_status,
            newborn_screening_status_date,
            feeding_method_id,
            updated_by
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('update_child_health_record', [
                    child_health_id,
                    place_of_delivery,
                    address_landmark,
                    tt_status_of_mother,
                    tt_status_date,
                    newborn_screening_status,
                    newborn_screening_status_date,
                    feeding_method_id,
                    updated_by
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_specific_child_immunization_record(child_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_child_immunization_record', [
                    child_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_all_child_supplements(child_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_all_child_supplements', [
                    child_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_child_supplement(
            child_health_id,
            supplement_id,
            age_in_months,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_child_supplement', [
                    child_health_id,
                    supplement_id,
                    age_in_months,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_supplements():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT supplement_id, supplement_name FROM Supplements")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_child_all_growth_monitoring(child_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_child_all_growth_monitoring', [
                    child_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_child_growth_monitoring(
            child_health_id,
            weight_kg,
            height_cm,
            temp_c,
            resp_rate,
            pulse_rate,
            notes,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_child_growth_monitoring', [
                    child_health_id,
                    weight_kg,
                    height_cm,
                    temp_c,
                    resp_rate,
                    pulse_rate,
                    notes,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_child_exclusive_breastfeed_track(child_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_child_exclusive_breastfeed_track', [
                    child_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_exclusive_breastfeed_backfill(
            child_health_id,
            month_id,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_exclusive_breastfeed_backfill', [
                    child_health_id,
                    month_id,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e

class Maternal:
    
    class Meta:
        managed = False
        
    @staticmethod
    def sp_view_all_maternal_record(
            name_query=None,
            record_status_id=None,
            limit=25,
            offset=0
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc(
                    "view_all_maternal_record", [
                        name_query, 
                        record_status_id, 
                        limit, 
                        offset
                    ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_specific_maternal_health_record(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_maternal_health_record', [maternal_health_id])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_insert_maternal(
            maternal_id,
            address_landmark,
            created_by
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_maternal', [
                    maternal_id,
                    address_landmark,
                    created_by
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_obstetrical_history(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_obstetrical_history', [maternal_health_id])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_add_obstetrical_history(
            maternal_health_id,
            gravida,
            para,
            aborption,
            last_menstrual_period,
            expected_date_of_delivery,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_obstetrical_history', [
                    maternal_health_id,
                    gravida,
                    para,
                    aborption,
                    last_menstrual_period,
                    expected_date_of_delivery,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_medical_condition(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_maternal_all_medical_condition', [
                    maternal_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_maternal_medical_condition(
            maternal_health_id,
            medical_condition_name,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_maternal_medical_condition', [
                    maternal_health_id,
                    medical_condition_name,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_surgical_history(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_maternal_all_surgical_history', [
                    maternal_health_id
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_maternal_surgical_history(
            maternal_health_id,
            surgical_history_name,
            date_of_surgery,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_maternal_surgical_history', [
                    maternal_health_id,
                    surgical_history_name,
                    date_of_surgery,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_last_completed_gravida(maternal_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT get_last_completed_gravida(%s)', [maternal_id])
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_disease_surveillance(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_maternal_all_disease_surveillance', [maternal_health_id])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_disease_screen_record(
            maternal_health_id,
            disease_type_id,
            screening_date,
            result,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_disease_screen_record', [
                    maternal_health_id,
                    disease_type_id,
                    screening_date,
                    result,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_last_completed_abortion(maternal_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT get_last_completed_abortion(%s)', [maternal_id])
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_immunization_status_track(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_maternal_immunization_status_track', [
                    maternal_health_id
                ])
                cols = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_maternal_immunization(
            maternal_health_id,
            dose_number,
            date_given,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_maternal_immunization', [
                    maternal_health_id,
                    dose_number,
                    date_given,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_disease_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT disease_type_id, disease_name FROM Disease_Type ORDER BY disease_name")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_laboratory_screening(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_maternal_all_laboratory_screening', [maternal_health_id])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_lab_screening_record(
            maternal_health_id,
            test_type_id,
            test_date,
            result,
            iron_tablet_given_date,
            iron_tablet_quantity,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_lab_screening_record', [
                    maternal_health_id,
                    test_type_id,
                    test_date,
                    result,
                    iron_tablet_given_date,
                    iron_tablet_quantity,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_test_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT test_type_id, test_name FROM Test_Type ORDER BY test_name")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_checkup_records(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM view_specific_maternal_all_checkup_record(%s)", [maternal_health_id])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_supplements_record(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM view_specific_maternal_all_supplements_record(%s)", [maternal_health_id])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_maternal_supplement_record(
            maternal_health_id,
            supplement_type_id,
            date_given,
            number_of_tablets,
            personnel_id
            ):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT add_maternal_supplement_record(%s, %s, %s, %s, %s)", 
                             [maternal_health_id, supplement_type_id, date_given, number_of_tablets, personnel_id])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_supplement_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT supplement_type_id, supplement_name FROM Supplement_Type ORDER BY supplement_name")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_checkup_record(
            maternal_health_id,
            aog_weeks,
            weight_kg,
            height_cm,
            bmi,
            blood_pressure,
            fetal_heart_rate,
            laboratory_results,
            notes,
            personnel_id
            ):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT add_checkup_record(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                             [maternal_health_id, aog_weeks, weight_kg, height_cm, bmi, blood_pressure, fetal_heart_rate, laboratory_results, notes, personnel_id])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_record_status():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM RECORD_STATUS
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_deworming_record(
            maternal_health_id,
            deworming_type_id,
            number_of_tablets,
            date_given,
            personnel_id
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('add_deworming_record', [
                    maternal_health_id,
                    deworming_type_id,
                    number_of_tablets,
                    date_given,
                    personnel_id
                ])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_deworming_record(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_specific_maternal_all_deworming_record', [maternal_health_id])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_deworming_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT deworming_type_id, deworming_name FROM Deworming_Type")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_delivery_outcome(
            maternal_health_id,
            outcome_type_id,
            delivery_type_id,
            place_delivery_type_id,
            ownership_type_id,
            others_description,
            birth_attendant_id,
            other_attendant,
            time_of_delivery,
            date_terminated,
            baby_birthweight_in_grams,
            baby_sex,
            personnel_id
            ):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT add_delivery_outcome(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)", 
                             [maternal_health_id, outcome_type_id, delivery_type_id, place_delivery_type_id, 
                              ownership_type_id, others_description, birth_attendant_id, other_attendant, 
                              time_of_delivery, date_terminated, baby_birthweight_in_grams, baby_sex, personnel_id])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_delivery_outcome(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM view_specific_maternal_delivery_outcome(%s)", [maternal_health_id])
                cols = [col[0] for col in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_outcome_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT outcome_type_id, outcome_type_description FROM Outcome_Type ORDER BY outcome_type_description")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_delivery_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT delivery_type_id, delivery_name FROM Delivery_Type ORDER BY delivery_name")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_place_delivery_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT place_delivery_type_id, place_delivery_name FROM Place_Delivery_Type ORDER BY place_delivery_name")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_ownership_types():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT ownership_type_id, ownership_name FROM Ownership_Type ORDER BY ownership_name")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_get_birth_attendants():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT birth_attendant_id, birth_attendant_name FROM Birth_Attendant ORDER BY birth_attendant_name")
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_add_postpartum_visit(
            maternal_health_id,
            date_of_visit,
            weight_kg,
            height_cm,
            blood_pressure,
            notes,
            laboratory_notes,
            personnel_id
            ):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT add_postpartum_visit(%s, %s, %s, %s, %s, %s, %s, %s)", 
                             [maternal_health_id, date_of_visit, weight_kg, height_cm, 
                              blood_pressure, notes, laboratory_notes, personnel_id])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            raise e
    
    @staticmethod
    def sp_view_specific_maternal_all_postpartum_visit(maternal_health_id):
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT * FROM view_specific_maternal_all_postpartum_visit(%s)", [maternal_health_id])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e

