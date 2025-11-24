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
    """
    Add exclusive breastfeed assessment (backfills all missing months up to target)
    Returns list of inserted months
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM add_exclusive_breastfeed_backfill(
                    %s::INT,
                    %s::INT,
                    %s::INT
                )
            """, [
                child_health_id,
                month_id,
                personnel_id
            ])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                results.append(record)
            
            if not results:
                raise Exception("No months were inserted")
            
            print(f"✅ Exclusive breastfeed backfill successful: {len(results)} month(s) inserted")
            return results
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to add exclusive breastfeed: {error_msg}")
        
        # Handle specific SQL errors
        if 'P4407' in error_msg or 'already assessed' in error_msg:
            if 'Next month:' in error_msg:
                # Example: "Next month: 5th Month" → Extract "5th Month"
                next_month_part = error_msg.split('Next month:')[-1].strip().rstrip('.')
                raise Exception(f"Assessment already recorded. Please select '{next_month_part}' to continue tracking.")
            else:
                raise Exception("This month has already been assessed. Please select the next available month.")
        elif 'P4403' in error_msg or 'not allowed for Bottle/Mixed' in error_msg:
            raise Exception("Exclusive breastfeeding tracking is only for breastfeeding infants")
        elif 'P4402' in error_msg or 'Feeding method missing' in error_msg:
            raise Exception("Child's feeding method is not set")
        elif 'P4401' in error_msg or 'not found' in error_msg:
            raise Exception("Child health record not found")
        elif 'P4406' in error_msg or 'months 1..6' in error_msg:
            raise Exception("Exclusive breastfeeding is tracked only for months 1 to 6")
        else:
            raise Exception(f"Failed to add exclusive breastfeed assessment: {error_msg}")


def view_specific_child_exclusive_breastfeed_track(child_health_id):
    """
    View exclusive breastfeed tracking for a child (months 1-6)
    Returns all 6 months with assessment status
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_child_exclusive_breastfeed_track(%s)
            """, [child_health_id])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                # Convert datetime to ISO string
                if 'date_assessed' in record and record['date_assessed']:
                    record['date_assessed'] = record['date_assessed'].isoformat()
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"❌ Failed to view exclusive breastfeed track: {str(e)}")
        raise Exception(f"Failed to view exclusive breastfeed track: {str(e)}")


def get_all_months():
    """Get all months for dropdown"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT month_id, month_number, month_sequence_name
                FROM Month
                WHERE month_number BETWEEN 1 AND 6
                ORDER BY month_number
            """)
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"❌ Failed to get months: {str(e)}")
        raise Exception(f"Failed to get months: {str(e)}")


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
    """Add supplement record for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_child_supplement(
                    %s::INT,
                    %s::INT,
                    %s::INT,
                    %s::INT
                )
            """, [
                child_health_id,
                supplement_id,
                age_in_months,
                personnel_id
            ])
            
            result = cursor.fetchone()
            child_health_id_returned = result[0] if result else None
            
            if child_health_id_returned is None:
                raise Exception("Failed to add supplement - no ID returned")
            
            print(f"✅ Supplement added for child_health_id={child_health_id_returned}")
            return child_health_id_returned
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to add supplement: {error_msg}")
        
        # Handle specific SQL errors
        if 'P4704' in error_msg or 'already recorded' in error_msg:
            raise Exception("This supplement has already been given at this age")
        elif 'P4701' in error_msg or 'not found' in error_msg:
            raise Exception("Child health record not found")
        elif 'P4702' in error_msg or 'Invalid age' in error_msg:
            raise Exception("Invalid age in months")
        elif 'P4703' in error_msg or 'Supplement not found' in error_msg:
            raise Exception("Supplement type not found")
        elif 'P4706' in error_msg or 'inactive' in error_msg:
            raise Exception("This supplement is no longer active")
        else:
            raise Exception(f"Failed to add supplement: {error_msg}")


def view_all_child_supplements(child_health_id):
    """View all supplements given to child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_all_child_supplements(%s)
            """, [child_health_id])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                # Convert datetime to ISO string
                if 'date_given' in record and record['date_given']:
                    record['date_given'] = record['date_given'].isoformat()
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"❌ Failed to view supplements: {str(e)}")
        raise Exception(f"Failed to view supplements: {str(e)}")


def add_child_medical_condition(child_health_id, medical_condition, personnel_id):
    """Add medical condition for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_child_medical_condition(
                    %s::INT,
                    %s::TEXT,
                    %s::INT
                )
            """, [
                child_health_id,
                medical_condition,
                personnel_id
            ])
            
            result = cursor.fetchone()
            rmh_id = result[0] if result else None
            
            if rmh_id is None:
                raise Exception("Failed to add medical condition - no ID returned")
            
            print(f"✅ Medical condition added: rmh_id={rmh_id}")
            return rmh_id
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to add medical condition: {error_msg}")
        
        # Handle specific SQL errors
        if 'P4803' in error_msg or 'Duplicate medical condition' in error_msg:
            raise Exception("This medical condition has already been recorded for this child")
        elif 'P4802' in error_msg or 'not found' in error_msg:
            raise Exception("Child health record not found")
        elif 'P4801' in error_msg or 'cannot be blank' in error_msg:
            raise Exception("Medical condition cannot be blank")
        else:
            raise Exception(f"Failed to add medical condition: {error_msg}")



def view_specific_child_all_medical_condition(child_health_id):
    """View all medical conditions for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_child_all_medical_condition(%s)
            """, [child_health_id])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                # Convert datetime to ISO string for JSON serialization
                if 'date_added' in record and record['date_added']:
                    record['date_added'] = record['date_added'].isoformat()
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"❌ Failed to view medical conditions: {str(e)}")
        raise Exception(f"Failed to view medical conditions: {str(e)}")


def add_child_surgical_history(child_health_id, surgical_history_name, date_of_surgery, personnel_id):
    """Add surgical history for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_child_surgical_history(
                    %s::INT,
                    %s::TEXT,
                    %s::DATE,
                    %s::INT
                )
            """, [
                child_health_id,
                surgical_history_name,
                date_of_surgery,
                personnel_id
            ])
            
            result = cursor.fetchone()
            rsh_id = result[0] if result else None
            
            if rsh_id is None:
                raise Exception("Failed to add surgical history - no ID returned")
            
            print(f"✅ Surgical history added: rsh_id={rsh_id}")
            return rsh_id
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to add surgical history: {error_msg}")
        
        # Handle specific SQL errors
        if 'P4904' in error_msg or 'Duplicate surgical history' in error_msg:
            raise Exception("This surgical procedure has already been recorded for this date")
        elif 'P4903' in error_msg or 'not found' in error_msg:
            raise Exception("Child health record not found")
        elif 'P4901' in error_msg or 'name required' in error_msg:
            raise Exception("Surgical history name is required")
        elif 'P4902' in error_msg or 'Date of surgery required' in error_msg:
            raise Exception("Date of surgery is required")
        else:
            raise Exception(f"Failed to add surgical history: {error_msg}")

def view_specific_child_all_surgical_history(child_health_id):
    """View all surgical history for child"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_child_all_surgical_history(%s)
            """, [child_health_id])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                # Convert dates to ISO strings
                if 'date_of_surgery' in record and record['date_of_surgery']:
                    record['date_of_surgery'] = record['date_of_surgery'].isoformat()
                if 'date_added' in record and record['date_added']:
                    record['date_added'] = record['date_added'].isoformat()
                results.append(record)
            
            return results
            
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


def view_all_general_health(query=None, quarter_id=None, sitio_id=None, sex=None, limit=50, offset=0):
    """
    View all general health records with filtering
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_all_general_health(
                    %s::TEXT,    -- query
                    %s::INT,     -- quarter_id 
                    %s::INT,     -- sitio_id 
                    %s::TEXT,    -- sex 
                    %s::INT,     -- limit
                    %s::INT      -- offset
                )
            """, [query, quarter_id, sitio_id, sex, limit, offset])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in rows]
            
    except Exception as e:
        raise Exception(f"Failed to fetch records: {e}")


def view_specific_resident_general_health(family_member_id, quarter_id=None):
    """
    View detailed general health record for a specific family member
    """
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_resident_general_health(
                    %s::INT,
                    %s::INT
                )
            """, [
                family_member_id,
                quarter_id
            ])
            
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            
            if not row:
                return None
            
            record = dict(zip(columns, row))
            
            # Convert arrays/jsonb to proper format
            if 'medical_history_names' in record and record['medical_history_names']:
                record['medical_history_names'] = list(record['medical_history_names'])
            else:
                record['medical_history_names'] = []
            
            # Convert dates to ISO strings
            if 'last_menstrual_period' in record and record['last_menstrual_period']:
                record['last_menstrual_period'] = record['last_menstrual_period'].isoformat()
            
            if 'created_at' in record and record['created_at']:
                record['created_at'] = record['created_at'].isoformat()
            
            if 'updated_at' in record and record['updated_at']:
                record['updated_at'] = record['updated_at'].isoformat()
            
            return record
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Failed to view general health detail: {error_msg}")
        raise Exception(f"Failed to view general health detail: {error_msg}")