from ..utils.database_helpers import get_households_for_bhw, create_household, create_family, get_lookup_data
import logging

logger = logging.getLogger(__name__)

class HouseholdService:
    """Service class following your ProfileService pattern"""
    
    @staticmethod
    def get_households_for_personnel(personnel_id):
        """Get households for BHW - simple wrapper like your ProfileService"""
        try:
            return get_households_for_bhw(personnel_id)
        except Exception as e:
            logger.error(f"Service error getting households: {e}")
            raise e
    
    @staticmethod
    def create_new_household(form_data, personnel_id):
        """Create household - simple wrapper like your ProfileService"""
        try:
            return create_household(form_data, personnel_id)
        except Exception as e:
            logger.error(f"Service error creating household: {e}")
            raise e
    
    @staticmethod
    def create_new_family(household_id, form_data, personnel_id):
        """Create family - simple wrapper like your ProfileService"""
        try:
            return create_family(household_id, form_data, personnel_id)
        except Exception as e:
            logger.error(f"Service error creating family: {e}")
            raise e
    
    @staticmethod
    def get_all_lookup_data():
        """Get lookup data - simple wrapper like your ProfileService"""
        try:
            return get_lookup_data()
        except Exception as e:
            logger.error(f"Service error getting lookup data: {e}")
            raise e