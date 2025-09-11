from django.db import models, connection

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
