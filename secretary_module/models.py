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
    