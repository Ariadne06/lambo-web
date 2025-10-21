from email.headerregistry import Address
from django.db import connection
from ..utils.database_helpers import get_all_households
from ..models import Household
import json

class HouseholdService:
    """Service to handle household operations """
    
    @staticmethod
    def insert_household(data):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_household', [
                    data['house_ownership_id'],
                    data['house_type_id'],
                    data['barangay'],
                    data['city_municipality'],
                    data['sitio_id'],
                    data['personnel_id'],
                    data.get('house_number'),
                    data.get('street'),
                    data.get('country', 'Philippines'),
                    data.get('household_head_id'),
                    data.get('respondent_id'),
                    data.get('respondent_rth_id'),
                    data.get('performed_by_id'),
                    data.get('performed_by_type', 'personnel'),
                    data.get('enforce_bhw_assignment', False),
                ])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            raise Exception(f"Database operation failed: {str(e)}")
    
    @staticmethod
    def get_all_households():
        """
        Get all households 
        """
        return get_all_households()
    
    @staticmethod
    def create_new_family(household_id, data, personnel_id):
        """
        Create a new family for a household using SQL function
        """
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_family', [
                     household_id,                                     
                    data['household_type_id'],                      
                    data['family_head_id'],                                                  
                    data['water_source_type_id'],                    
                    data['toilet_facility_type_id'],                  
                    data['waste_management_type_id'],                      
                    data['respondent_id'],                             
                    data.get('respondent_relationship_to_fh_id', 1),         
                    data.get('head_rth_id', 1),                       
                    data.get('ip_status', False),                      
                    data.get('ip_tribe', ''),                         
                    data.get('nhts_status', False),                   
                    None,                                                 
                    personnel_id,                                    
                    'personnel',                                       
                    False,                                                
                ])
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception as e:
            print(f"Database error creating family: {str(e)}")
            raise Exception(f"Database operation failed: {str(e)}")