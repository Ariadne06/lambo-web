from django.db import connection
import logging

logger = logging.getLogger(__name__)

def get_households_for_bhw(personnel_id):
    """Get households for BHW - following your database_helpers pattern"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    h.household_id,
                    h.household_code,
                    h.house_number,
                    CONCAT(hh.first_name, ' ', hh.last_name) as household_head_name,
                    CONCAT(resp.first_name, ' ', resp.last_name) as respondent_name,
                    CONCAT(COALESCE(a.street, ''), ', ', a.barangay, ', ', COALESCE(a.sitio, '')) as full_address,
                    h.is_visited,
                    COUNT(f.family_id) as family_count,
                    COUNT(CASE WHEN f.is_visited = TRUE THEN 1 END) as visited_families,
                    h.quarter,
                    h.year
                FROM household h
                LEFT JOIN resident hh ON h.household_head_id = hh.resident_id
                LEFT JOIN resident resp ON h.respondent_id = resp.resident_id
                LEFT JOIN address a ON h.address_id = a.address_id
                LEFT JOIN family f ON h.household_id = f.household_id 
                WHERE h.quarter = (SELECT EXTRACT(QUARTER FROM CURRENT_DATE))
                AND h.year = (SELECT EXTRACT(YEAR FROM CURRENT_DATE))
                GROUP BY h.household_id, h.household_code, h.house_number, 
                         hh.first_name, hh.last_name, resp.first_name, resp.last_name,
                         a.street, a.barangay, a.sitio, h.is_visited, h.quarter, h.year
                ORDER BY h.household_code
            """)
            
            return cursor.fetchall()
            
    except Exception as e:
        logger.error(f"Error fetching households: {e}")
        raise e

def create_household(form_data, personnel_id):
    """Create household using your database function pattern"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT insert_household(%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                form_data.get('house_ownership_type_id'),
                form_data.get('house_number', ''),
                form_data.get('address_id'),
                form_data.get('household_head_id'),
                form_data.get('respondent_id'),
                form_data.get('respondent_relationship_to_hh_id', 1),
                personnel_id,
                # Quarter and year will be handled by the database function
                None,  # quarter - let DB function handle
                None   # year - let DB function handle
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        logger.error(f"Error creating household: {e}")
        raise e

def create_family(household_id, form_data, personnel_id):
    """Create family using your database function pattern"""
    try:
        # Validate that family_head_id is provided - REQUIRED!
        if not form_data.get('family_head_id'):
            raise ValueError("Family head is required")
            
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT insert_family(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, [
                household_id,
                form_data.get('household_type_id'),
                form_data.get('family_head_id'),  # REQUIRED!
                form_data.get('respondent_id'),
                form_data.get('respondent_relationship_to_fh_id', 1),
                form_data.get('ip_status', False),
                form_data.get('ip_tribe', ''),
                form_data.get('nhts_status', False),
                form_data.get('water_source_type_id'),
                form_data.get('toilet_facility_type_id'),
                form_data.get('waste_management_type_id'),
                form_data.get('waste_other_text', ''),
                None,  # quarter - let DB function handle
                None   # year - let DB function handle
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        logger.error(f"Error creating family: {e}")
        raise e

def get_lookup_data():
    """Get all lookup data - following your pattern"""
    try:
        data = {}
        
        with connection.cursor() as cursor:
            # Get residents
            cursor.execute("""
                SELECT resident_id, first_name, last_name,
                       CONCAT(first_name, ' ', last_name) as full_name
                FROM resident 
                WHERE status_id IN (SELECT status_id FROM resident_status WHERE status_name = 'Active')
                ORDER BY last_name, first_name
            """)
            columns = [col[0] for col in cursor.description]
            data['residents'] = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Get addresses
            cursor.execute("""
                SELECT address_id, street, barangay, sitio, city_municipality,
                       CONCAT(COALESCE(street, ''), ', ', barangay, ', ', COALESCE(sitio, '')) as full_address
                FROM address
                ORDER BY barangay, sitio, street
            """)
            columns = [col[0] for col in cursor.description]
            data['addresses'] = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
        return data
        
    except Exception as e:
        logger.error(f"Error fetching lookup data: {e}")
        raise e