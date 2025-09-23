from django.db import connection
import logging

logger = logging.getLogger(__name__)


def get_document_types():
    """Get all document types - using SQL function fn_list_document_types()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM fn_list_document_types()")
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching document types: {e}")
        raise e


def get_clearance_purposes():
    """Get all clearance purposes with fees - using SQL function fn_list_clearance_purposes()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM fn_list_clearance_purposes()")
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching clearance purposes: {e}")
        raise e


def calculate_certificate_fee(resident_id, document_type_id, business_id=None, clearance_purpose_id=None):
    """Calculate fee using SQL function resident_quote_fee()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT resident_quote_fee(%s, %s, %s, %s)
            """, [resident_id, document_type_id, business_id, clearance_purpose_id])
            
            result = cursor.fetchone()
            return result[0] if result else 0.00
    except Exception as e:
        logger.error(f"Error calculating certificate fee: {e}")
        raise e


def create_certificate_application(applicant_id, document_type_id, application_description, business_id=None, clearance_purpose_id=None):
    """Create certificate application using SQL function resident_create_application()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT resident_create_application(%s, %s, %s, %s, %s)
            """, [applicant_id, document_type_id, application_description, business_id, clearance_purpose_id])
            
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error creating certificate application: {e}")
        raise e


def get_resident_applications(resident_id):
    """Get applications for a resident - direct SQL query"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.application_id,
                    dt.document_type_name,
                    a.application_description,
                    cp.purpose_name,
                    ast.application_status_name,
                    COALESCE(pt.amount, 0) as fee_amount,
                    a.application_date,
                    a.approval_date,
                    'N/A' as remarks
                FROM application a
                JOIN document_type dt ON a.document_type_id = dt.document_type_id
                LEFT JOIN clearance_purpose cp ON a.clearance_purpose_id = cp.clearance_purpose_id
                JOIN application_status ast ON a.application_status_id = ast.application_status_id
                LEFT JOIN payment_transactions pt ON a.application_id = pt.application_id
                WHERE a.applicant_id = %s
                ORDER BY a.application_date DESC
            """, [resident_id])
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching resident applications: {e}")
        raise e


def get_application_details(application_id):
    """Get detailed application information - direct SQL query"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.application_id,
                    a.applicant_id,
                    CONCAT(r.first_name, ' ', r.last_name) as applicant_name,
                    dt.document_type_name,
                    a.application_description,
                    cp.purpose_name,
                    ast.application_status_name,
                    COALESCE(pt.amount, 0) as fee_amount,
                    a.application_date,
                    a.approval_date,
                    CONCAT(p.first_name, ' ', p.last_name) as processed_by,
                    'N/A' as remarks,
                    di.document_id as certificate_number,
                    di.date_issued as issued_date,
                    di.validity_period as valid_until
                FROM application a
                JOIN resident r ON a.applicant_id = r.resident_id
                JOIN document_type dt ON a.document_type_id = dt.document_type_id
                LEFT JOIN clearance_purpose cp ON a.clearance_purpose_id = cp.clearance_purpose_id
                JOIN application_status ast ON a.application_status_id = ast.application_status_id
                LEFT JOIN personnel_credentials p ON a.reviewed_by = p.personnel_id
                LEFT JOIN payment_transactions pt ON a.application_id = pt.application_id
                LEFT JOIN document_issuance di ON a.application_id = di.application_id
                WHERE a.application_id = %s
            """, [application_id])
            
            columns = [col[0] for col in cursor.description]
            result = cursor.fetchone()
            return dict(zip(columns, result)) if result else None
    except Exception as e:
        logger.error(f"Error fetching application details: {e}")
        raise e


def get_pending_applications():
    """Get all pending applications for processing - direct SQL query"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    a.application_id,
                    a.applicant_id,
                    CONCAT(r.first_name, ' ', r.last_name) as applicant_name,
                    dt.document_type_name,
                    a.application_description,
                    cp.purpose_name,
                    COALESCE(dpr.base_fee, cp.fee, 0) as fee_amount,
                    a.application_date,
                    CONCAT(COALESCE(addr.street, ''), ', ', addr.barangay) as address
                FROM application a
                JOIN resident r ON a.applicant_id = r.resident_id
                JOIN document_type dt ON a.document_type_id = dt.document_type_id
                LEFT JOIN clearance_purpose cp ON a.clearance_purpose_id = cp.clearance_purpose_id
                LEFT JOIN address addr ON r.address_id = addr.address_id
                LEFT JOIN document_pricing_rules dpr ON a.document_type_id = dpr.document_type_id AND dpr.business_type_id IS NULL
                WHERE a.application_status_id = (SELECT application_status_id FROM application_status WHERE application_status_name = 'Pending')
                ORDER BY a.application_date ASC
            """)
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching pending applications: {e}")
        raise e


def secretary_review_application(application_id, personnel_id, decision, remarks=None):
    """Review application using SQL function secretary_review_application()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT secretary_review_application(%s, %s, %s, %s)
            """, [personnel_id, application_id, decision, remarks])
            
            # Function returns void, so just check if it executed successfully
            return True
    except Exception as e:
        logger.error(f"Error reviewing application: {e}")
        raise e


def treasurer_record_payment(application_id, personnel_id, document_type_id, amount, or_number, extra_amount=0):
    """Record payment using SQL function treasurer_record_payment_and_approve()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT treasurer_record_payment_and_approve(%s, %s, %s, %s, %s, %s)
            """, [personnel_id, application_id, document_type_id, amount, or_number, extra_amount])
            
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error recording payment: {e}")
        raise e


def secretary_mark_completed(application_id, personnel_id, remarks=None):
    """Mark application as completed using SQL function secretary_mark_completed()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT secretary_mark_completed(%s, %s, %s)
            """, [personnel_id, application_id, remarks])
            
            # Function returns void, so just check if it executed successfully
            return True
    except Exception as e:
        logger.error(f"Error marking application completed: {e}")
        raise e


def get_application_status_id(status_name):
    """Get application status ID by name using SQL function get_application_status_id()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT get_application_status_id(%s)", [status_name])
            
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting application status ID: {e}")
        raise e


def get_document_type_id(document_name):
    """Get document type ID by name using SQL function get_document_type_id()"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT get_document_type_id(%s)", [document_name])
            
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        logger.error(f"Error getting document type ID: {e}")
        raise e