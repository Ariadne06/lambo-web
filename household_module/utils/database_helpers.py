from django.db import connection



def get_all_households():
    """
    Get all households using SQL function
    Returns: list of dicts
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM get_all_households(
                    NULL, NULL, NULL, 'all', NULL, 10000, 0
                )
            """)
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()

            households = []
            for row in rows:
                household_dict = dict(zip(columns, row))
                if household_dict.get('date_visited'):
                    household_dict['date_visited'] = household_dict['date_visited'].isoformat()
                households.append(household_dict)

            return households

    except Exception as e:
        print(f"Failed to get households: {str(e)}")
        raise Exception(f"Failed to get households: {str(e)}")
    

def insert_family_member(family_id, resident_id, rth_id, rtf_id, philhealthid_number, 
                        membership_type, philhealth_category_id, nutrition_status_id, 
                        personnel_id):
    """Insert family member using SQL function"""
    try:
        with connection.cursor() as cursor:
            cursor.callproc('insert_family_member', [
                resident_id,
                family_id,
                rth_id,
                rtf_id,
                philhealthid_number or '',
                membership_type or 'M',
                philhealth_category_id,
                nutrition_status_id,
                personnel_id,
                'personnel'
            ])
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"Failed to insert family member: {str(e)}")
        raise Exception(f"Failed to insert family member: {str(e)}")


def save_general_health_for_member(family_member_id, class_id, medical_history_ids, 
                                   wra_lmp, fp_method_yn, fp_method_id, 
                                   fp_status_id, personnel_id,smoker=None, alcohol_drinker=None, 
                                   sexually_active=None, age_of_menarche=None):
    """
    Save general health profile for a family member
    """
    try:
        with connection.cursor() as cursor:
            #  FIX: Convert empty list to None for PostgreSQL
            if medical_history_ids is not None and len(medical_history_ids) == 0:
                medical_history_ids = None
            
            cursor.execute("""
                SELECT save_general_health_for_member(
                     %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                family_member_id,
                class_id,
                medical_history_ids,  
                wra_lmp,             
                fp_method_yn,       
                fp_method_id,        
                fp_status_id,
                age_of_menarche,
                smoker, 
                alcohol_drinker,
                sexually_active,         
                personnel_id,
                'personnel'           
            ])
            
            result = cursor.fetchone()
            gh_id = result[0] if result else None
            
            if gh_id is None:
                raise Exception("SQL function returned NULL - check database logs")
            
            return gh_id
            
    except Exception as e:
        print(f" Failed to save general health: {str(e)}")
        raise Exception(f"Failed to save general health: {str(e)}")


def update_general_health_for_member(
    family_member_id, 
    class_id=None,
    apply_med_hist=False, 
    medical_history_ids=None,
    apply_fp=False,
    wra_lmp=None,
    fp_method_yn=None,
    fp_method_id=None,
    fp_status_id=None,
    apply_lifestyle=False,
    smoker=None,
    alcohol_drinker=None,
    sexually_active=None,
    age_of_menarche=None,
    personnel_id=None
):
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT update_general_health_for_member(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                family_member_id,
                class_id,
                apply_med_hist,
                medical_history_ids,  # Will be converted to PostgreSQL array
                apply_fp,
                wra_lmp,
                fp_method_yn,
                fp_method_id,
                fp_status_id,
                age_of_menarche,       
                apply_lifestyle,       
                smoker,               
                alcohol_drinker,       
                sexually_active, 
                personnel_id,
                'personnel'
            ])
            
            result = cursor.fetchone()
            gh_id = result[0] if result else None
            
            if gh_id is None:
                raise Exception("SQL function returned NULL - check database logs")
            
            return gh_id
            
    except Exception as e:
        print(f" Failed to update general health: {str(e)}")
        raise Exception(f"Failed to update general health: {str(e)}")
    

# child health helpers

def search_child(query):
    """
    Search for children by name, family code, or resident ID
    
    Args:
        query (str): Search term (required - at least 2 characters)
    
    Returns:
        list: List of matching children with parent/family information
    """
    try:
        # Validate query
        if not query or len(query.strip()) < 2:
            return []
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM search_child(%s)
            """, [query.strip()])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                
                # Convert date to ISO format if present
                if record.get('dob'):
                    record['dob'] = record['dob'].isoformat()
                
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"Failed to search children: {str(e)}")
        raise Exception(f"Failed to search children: {str(e)}")


def view_all_child_health_records(query=None, limit=50, offset=0):
    """
    View all child health records with optional search and pagination
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_all_child_health_record(
                    p_query := %s,
                    p_limit := %s,
                    p_offset := %s
                )
            """, [
                query.strip() if query and query.strip() else None,
                limit,
                offset
            ])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                
                # Convert dates to ISO format
                if record.get('dob'):
                    record['dob'] = record['dob'].isoformat()
                if record.get('tt_status_date'):
                    record['tt_status_date'] = record['tt_status_date'].isoformat()
                if record.get('created_at'):
                    record['created_at'] = record['created_at'].isoformat()
                
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"Failed to view child health records: {str(e)}")
        raise Exception(f"Failed to view child health records: {str(e)}")



def insert_child_health_record(data):
    """Insert child health record using SQL function"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT insert_child_health_record(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                data['child_id'],
                data.get('time_of_birth'),
                data.get('birth_weight_kg'),
                data.get('birth_length_cm'),
                data.get('place_of_delivery'),
                data.get('address_landmark'),
                data.get('tt_status_of_mother'),
                data.get('tt_status_date'),
                data.get('newborn_screening_status'),
                data.get('newborn_screening_status_date'),
                data.get('feeding_method_id'),
                data['personnel_id']
            ])
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"❌ Failed to insert child health record: {str(e)}")
        raise Exception(f"Failed to insert child health record: {str(e)}")


def update_child_health_record(child_health_id, data):
    """Update child health record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT update_child_health_record(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                child_health_id,
                data.get('place_of_delivery'),
                data.get('address_landmark'),
                data.get('tt_status_of_mother'),
                data.get('tt_status_date'),
                data.get('newborn_screening_status'),
                data.get('newborn_screening_status_date'),
                data.get('feeding_method_id'),
                data['personnel_id']
            ])
    except Exception as e:
        print(f"❌ Failed to update child health record: {str(e)}")
        raise Exception(f"Failed to update child health record: {str(e)}")


def view_specific_child_health_record(child_health_id):
    """
    View specific child health record with all details
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_child_health_record(%s)
            """, [child_health_id])
            
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            
            if not row:
                return None
                
            record = dict(zip(columns, row))
            
            # Convert dates/times to ISO format
            if record.get('dob'):
                record['dob'] = record['dob'].isoformat()
            if record.get('time_of_birth'):
                record['time_of_birth'] = record['time_of_birth'].isoformat()
            if record.get('tt_status_date'):
                record['tt_status_date'] = record['tt_status_date'].isoformat()
            if record.get('newborn_screening_status_date'):
                record['newborn_screening_status_date'] = record['newborn_screening_status_date'].isoformat()
            if record.get('created_at'):
                record['created_at'] = record['created_at'].isoformat()
            if record.get('updated_at'):
                record['updated_at'] = record['updated_at'].isoformat()
            
            return record
            
    except Exception as e:
        print(f"Failed to view child health record: {str(e)}")
        raise Exception(f"Failed to view child health record: {str(e)}")


def add_exclusive_breastfeed_backfill(child_health_id, month_id, personnel_id):
    """Add exclusive breastfeed assessment with backfill"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM add_exclusive_breastfeed_backfill(%s, %s, %s)
            """, [child_health_id, month_id, personnel_id])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Failed to add breastfeed assessment: {str(e)}")
        raise Exception(f"Failed to add breastfeed assessment: {str(e)}")


def view_specific_child_exclusive_breastfeed_track(child_health_id):
    """View child's exclusive breastfeed tracking"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM view_specific_child_exclusive_breastfeed_track(%s)", [child_health_id])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Failed to view breastfeed track: {str(e)}")
        raise Exception(f"Failed to view breastfeed track: {str(e)}")


def add_child_immunization(child_health_id, vaccine_type_id, dose_type_id, personnel_id):
    """Add immunization record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_immunization(%s, %s, %s, %s)
            """, [child_health_id, vaccine_type_id, dose_type_id, personnel_id])
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"❌ Failed to add immunization: {str(e)}")
        raise Exception(f"Failed to add immunization: {str(e)}")


def view_specific_child_immunization_record(child_health_id):
    """View child's immunization records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM view_specific_child_immunization_record(%s)", [child_health_id])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Failed to view immunization records: {str(e)}")
        raise Exception(f"Failed to view immunization records: {str(e)}")


def add_child_supplement(child_health_id, supplement_id, age_in_months, personnel_id):
    """Add supplement record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_child_supplement(%s, %s, %s, %s)
            """, [child_health_id, supplement_id, age_in_months, personnel_id])
    except Exception as e:
        print(f"❌ Failed to add supplement: {str(e)}")
        raise Exception(f"Failed to add supplement: {str(e)}")


def view_all_child_supplements(child_health_id):
    """View all supplements given to child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM view_all_child_supplements(%s)", [child_health_id])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Failed to view supplements: {str(e)}")
        raise Exception(f"Failed to view supplements: {str(e)}")


def add_child_medical_condition(child_health_id, medical_condition, personnel_id):
    """Add medical condition for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_child_medical_condition(%s, %s, %s)
            """, [child_health_id, medical_condition, personnel_id])
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"❌ Failed to add medical condition: {str(e)}")
        raise Exception(f"Failed to add medical condition: {str(e)}")


def view_specific_child_all_medical_condition(child_health_id):
    """View all medical conditions for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM view_specific_child_all_medical_condition(%s)", [child_health_id])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Failed to view medical conditions: {str(e)}")
        raise Exception(f"Failed to view medical conditions: {str(e)}")


def add_child_surgical_history(child_health_id, surgical_history_name, date_of_surgery, personnel_id):
    """Add surgical history for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_child_surgical_history(%s, %s, %s, %s)
            """, [child_health_id, surgical_history_name, date_of_surgery, personnel_id])
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"❌ Failed to add surgical history: {str(e)}")
        raise Exception(f"Failed to add surgical history: {str(e)}")


def view_specific_child_all_surgical_history(child_health_id):
    """View all surgical history for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM view_specific_child_all_surgical_history(%s)", [child_health_id])
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        print(f"❌ Failed to view surgical history: {str(e)}")
        raise Exception(f"Failed to view surgical history: {str(e)}")


def add_child_growth_monitoring(child_health_id, weight_kg, height_cm, temp_c, resp_rate, pulse_rate, notes, personnel_id):
    """Add growth monitoring record - SQL function calculates age automatically"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_child_growth_monitoring(
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                child_health_id,
                weight_kg,
                height_cm,
                temp_c,
                resp_rate,
                pulse_rate,
                notes,
                personnel_id
            ])
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"❌ Failed to add growth monitoring: {str(e)}")
        raise Exception(f"Failed to add growth monitoring: {str(e)}")


def view_specific_child_all_growth_monitoring(child_health_id):
    """View all growth monitoring records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_child_all_growth_monitoring(%s)
            """, [child_health_id])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                
                # Format date properly
                if record.get('date_of_visit'):
                    record['date_of_visit'] = record['date_of_visit'].isoformat()
                
                # Calculate total months for display
                age_years = record.get('age_years', 0) or 0
                age_months = record.get('age_months', 0) or 0
                record['age_in_months'] = (age_years * 12) + age_months
                
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"❌ Failed to view growth monitoring: {str(e)}")
        raise Exception(f"Failed to view growth monitoring: {str(e)}")


def view_specific_child_all_growth_monitoring(child_health_id):
    """View all growth monitoring records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_child_all_growth_monitoring(%s)
            """, [child_health_id])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                
                # Format date properly
                if record.get('date_of_visit'):
                    record['date_of_visit'] = record['date_of_visit'].isoformat()
                
                # ✅ Calculate total months for display
                age_years = record.get('age_years', 0) or 0
                age_months = record.get('age_months', 0) or 0
                record['age_in_months'] = (age_years * 12) + age_months
                
                # ✅ Format numeric values properly
                if record.get('weight_kg'):
                    record['weight_kg'] = float(record['weight_kg'])
                if record.get('height_cm'):
                    record['height_cm'] = float(record['height_cm'])
                if record.get('temp_c'):
                    record['temp_c'] = float(record['temp_c'])
                if record.get('resp_rate'):
                    record['resp_rate'] = int(record['resp_rate'])
                if record.get('pulse_rate'):
                    record['pulse_rate'] = int(record['pulse_rate'])
                
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"❌ Failed to view growth monitoring: {str(e)}")
        raise Exception(f"Failed to view growth monitoring: {str(e)}")

def update_child_health_record(child_health_id, data):
    """Update child health record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT update_child_health_record(
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                child_health_id,
                data.get('place_of_delivery'),
                data.get('address_landmark'),
                data.get('tt_status_of_mother'),
                data.get('tt_status_date'),
                data.get('newborn_screening_status'),
                data.get('newborn_screening_status_date'),
                data.get('feeding_method_id'),
                data['personnel_id']
            ])
            
            print(f"✅ Updated child health record {child_health_id}")
            
    except Exception as e:
        print(f"❌ Failed to update child health record: {str(e)}")
        raise Exception(f"Failed to update child health record: {str(e)}")