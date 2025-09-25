from ..utils.database_helpers import (
    get_document_types, get_clearance_purposes, calculate_certificate_fee,
    create_certificate_application, get_resident_applications, get_application_details,
    get_pending_applications, secretary_review_application, treasurer_record_payment,
    secretary_mark_completed, get_application_status_id, get_document_type_id
)
import logging

logger = logging.getLogger(__name__)


class CertificateService:
    """Certificate service class - following household_module HouseholdService pattern"""
    
    @staticmethod
    def get_all_document_types():
        """Get all document types - simple wrapper like HouseholdService"""
        try:
            return get_document_types()
        except Exception as e:
            logger.error(f"Service error getting document types: {e}")
            raise e
    
    @staticmethod
    def get_all_clearance_purposes():
        """Get all clearance purposes - simple wrapper like HouseholdService"""
        try:
            return get_clearance_purposes()
        except Exception as e:
            logger.error(f"Service error getting clearance purposes: {e}")
            raise e
    
    @staticmethod
    def calculate_fee(resident_id, document_type_id, business_id=None, clearance_purpose_id=None):
        """Calculate certificate fee - simple wrapper like HouseholdService"""
        try:
            return calculate_certificate_fee(resident_id, document_type_id, business_id, clearance_purpose_id)
        except Exception as e:
            logger.error(f"Service error calculating fee: {e}")
            raise e
    
    @staticmethod
    def submit_application(applicant_id, document_type_id, application_description, business_id=None, clearance_purpose_id=None):
        """Submit certificate application - simple wrapper like HouseholdService"""
        try:
            return create_certificate_application(
                applicant_id, document_type_id, application_description, business_id, clearance_purpose_id
            )
        except Exception as e:
            logger.error(f"Service error submitting application: {e}")
            raise e
    
    @staticmethod
    def get_applications_for_resident(resident_id):
        """Get applications for resident - simple wrapper like HouseholdService"""
        try:
            return get_resident_applications(resident_id)
        except Exception as e:
            logger.error(f"Service error getting resident applications: {e}")
            raise e
    
    @staticmethod
    def get_application_by_id(application_id):
        """Get application details - simple wrapper like HouseholdService"""
        try:
            return get_application_details(application_id)
        except Exception as e:
            logger.error(f"Service error getting application details: {e}")
            raise e
    
    @staticmethod
    def get_all_pending_applications():
        """Get all pending applications for personnel - simple wrapper like HouseholdService"""
        try:
            return get_pending_applications()
        except Exception as e:
            logger.error(f"Service error getting pending applications: {e}")
            raise e
    
    @staticmethod
    def review_application(application_id, personnel_id, decision, remarks=None):
        """Review application (for payment/reject) - simple wrapper like HouseholdService"""
        try:
            return secretary_review_application(application_id, personnel_id, decision, remarks)
        except Exception as e:
            logger.error(f"Service error reviewing application: {e}")
            raise e
    
    @staticmethod
    def record_payment_and_approve(application_id, personnel_id, document_type_id, amount, or_number, extra_amount=0):
        """Record payment and approve application - simple wrapper like HouseholdService"""
        try:
            return treasurer_record_payment(application_id, personnel_id, document_type_id, amount, or_number, extra_amount)
        except Exception as e:
            logger.error(f"Service error recording payment: {e}")
            raise e
    
    @staticmethod
    def mark_application_completed(application_id, personnel_id, remarks=None):
        """Mark application as completed - simple wrapper like HouseholdService"""
        try:
            return secretary_mark_completed(application_id, personnel_id, remarks)
        except Exception as e:
            logger.error(f"Service error marking application completed: {e}")
            raise e
    
    @staticmethod
    def get_status_id_by_name(status_name):
        """Get application status ID by name - simple wrapper like HouseholdService"""
        try:
            return get_application_status_id(status_name)
        except Exception as e:
            logger.error(f"Service error getting status ID: {e}")
            raise e
    
    @staticmethod
    def get_document_type_id_by_name(document_name):
        """Get document type ID by name - simple wrapper like HouseholdService"""
        try:
            return get_document_type_id(document_name)
        except Exception as e:
            logger.error(f"Service error getting document type ID: {e}")
            raise e