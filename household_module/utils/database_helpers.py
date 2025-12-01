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
    

# ========================================
# MATERNAL HEALTH DATABASE HELPERS
# ========================================

def search_mother(query):
    """Search for mothers by name or resident ID"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM Search_mother(%s)", [query])
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Failed to search mothers: {str(e)}")
        raise Exception(f"Failed to search mothers: {str(e)}")


def view_all_maternal_record(
    name_query=None,
    family_code=None,
    record_status=None,
    date_from=None,
    date_to=None
):
    """View all maternal health records with filters"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM View_all_maternal_record(%s, %s, %s, %s, %s)",
                [name_query, family_code, record_status, date_from, date_to]
            )
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Failed to view maternal records: {str(e)}")
        raise Exception(f"Failed to view maternal records: {str(e)}")


def view_specific_maternal_health_record(maternal_health_id):
    """View detailed maternal health record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM view_specific_maternal_health_record(%s)",
                [maternal_health_id]
            )
            columns = [col[0] for col in cursor.description]
            result = cursor.fetchone()
            return dict(zip(columns, result)) if result else None
    except Exception as e:
        print(f"Failed to view maternal health record: {str(e)}")
        raise Exception(f"Failed to view maternal health record: {str(e)}")


def insert_maternal(maternal_id, address_landmark, personnel_id):
    """Create new maternal health record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT Insert_maternal(%s, %s, %s)",
                [maternal_id, address_landmark, personnel_id]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to create maternal record: {str(e)}")
        raise Exception(f"Failed to create maternal record: {str(e)}")

def update_maternal_record(maternal_health_id, address_landmark, personnel_id):
    """Update maternal health record (only address_landmark)"""
    try:
        with connection.cursor() as cursor:
            cursor.callproc('update_maternal_health_record', [
                maternal_health_id,
                address_landmark,
                personnel_id
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        print(f"❌ Failed to update maternal record: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def update_maternal_record_status(maternal_health_id, record_status_id, personnel_id):
    """Update maternal health record status to Completed"""
    try:
        with connection.cursor() as cursor:
            cursor.callproc('update_maternal_health_record_status', [
                maternal_health_id,
                record_status_id,
                personnel_id
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        print(f"❌ Failed to update maternal record status: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


# Obstetrical History
def add_obstetrical_history(maternal_health_id, data):
    """Add obstetrical history"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_obstetrical_history(
                    p_maternal_health_id        := %s,
                    p_gravida                   := %s,
                    p_para                      := %s,
                    p_abortion                  := %s,
                    p_last_menstrual_period     := %s,
                    p_expected_date_of_delivery := %s,
                    p_personnel_id              := %s
                )
            """, [
                maternal_health_id,
                data.get('gravida'),
                data.get('para'),
                data.get('abortion'),
                data.get('last_menstrual_period'),
                data.get('expected_date_of_delivery'),
                data.get('personnel_id')
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        print(f"❌ Failed to add obstetrical history: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def view_obstetrical_history(maternal_health_id):
    """View obstetrical history for a maternal health record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_obstetrical_history(%s)
            """, [maternal_health_id])
            
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                
                # Convert dates to ISO format
                if 'last_menstrual_period' in record and record['last_menstrual_period']:
                    record['last_menstrual_period'] = record['last_menstrual_period'].isoformat()
                if 'expected_date_of_delivery' in record and record['expected_date_of_delivery']:
                    record['expected_date_of_delivery'] = record['expected_date_of_delivery'].isoformat()
                if 'created_at' in record and record['created_at']:
                    record['created_at'] = record['created_at'].isoformat()
                
                results.append(record)
            
            return results
            
    except Exception as e:
        print(f"❌ Failed to view obstetrical history: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")

# Medical/Surgical History
# Medical/Surgical History
def add_maternal_medical_condition(maternal_health_id, condition_name, personnel_id):
    """Add maternal medical condition"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_maternal_medical_condition(
                    p_maternal_health_id := %s,
                    p_m_medical_history_name := %s,
                    p_personnel_id := %s
                )
            """, [maternal_health_id, condition_name, personnel_id])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        print(f"❌ Failed to add maternal medical condition: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def view_maternal_all_medical_conditions(maternal_health_id):
    """View all medical conditions"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_maternal_all_medical_condition(%s)
            """, [maternal_health_id])
            
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in results]
            
    except Exception as e:
        print(f"❌ Failed to view maternal medical conditions: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def add_maternal_surgical_history(maternal_health_id, data, personnel_id):
    """Add surgical history"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_maternal_surgical_history(
                    p_maternal_health_id := %s,
                    p_m_surgical_history_name := %s,
                    p_date_of_surgery := %s,
                    p_personnel_id := %s
                )
            """, [
                maternal_health_id,
                data.get('surgical_history_name'),
                data.get('date_of_surgery'),
                personnel_id
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        print(f"❌ Failed to add maternal surgical history: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def view_maternal_all_surgical_history(maternal_health_id):
    """View all surgical history"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_maternal_all_surgical_history(%s)
            """, [maternal_health_id])
            
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            
            return [dict(zip(columns, row)) for row in results]
            
    except Exception as e:
        print(f"❌ Failed to view maternal surgical history: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


# Immunization
def add_maternal_immunization(maternal_health_id, dose_number, date_given, personnel_id):
    """Add TT immunization dose"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT add_maternal_immunization(%s, %s, %s, %s)
            """, [maternal_health_id, dose_number, date_given, personnel_id])
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        print(f"❌ Failed to add immunization: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def view_maternal_immunization_track(maternal_health_id):
    """View TT immunization tracking"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_maternal_immunization_status_track(%s)
            """, [maternal_health_id])
            
            columns = [col[0] for col in cursor.description]
            result = cursor.fetchone()
            
            if not result:
                return None
            
            record = dict(zip(columns, result))
            
            # Convert dates to ISO format for JSON
            date_fields = [
                'first_dose_date', 'second_dose_date', 'third_dose_date',
                'fourth_dose_date', 'fifth_dose_date', 'updated_at'
            ]
            
            for field in date_fields:
                if field in record and record[field]:
                    record[field] = record[field].isoformat()
            
            return record
            
    except Exception as e:
        print(f"❌ Failed to view immunization track: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


# Disease Surveillance
def add_disease_screen_record(maternal_health_id, data, personnel_id):
    """Add disease screening record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_disease_screen_record(%s, %s, %s, %s, %s)",
                [
                    maternal_health_id,
                    data['disease_type_id'],
                    data['screening_date'],
                    data.get('result'),
                    personnel_id
                ]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to add disease screen: {str(e)}")
        raise Exception(f"Failed to add disease screen: {str(e)}")


def view_maternal_all_disease_surveillance(maternal_health_id):
    """View all disease surveillance records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_maternal_all_disease_surveillance(%s)
            """, [maternal_health_id])
            
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            
            records = []
            for row in results:
                record = dict(zip(columns, row))
                
                # Convert dates to ISO format
                if 'screening_date' in record and record['screening_date']:
                    record['screening_date'] = record['screening_date'].isoformat()
                if 'created_at' in record and record['created_at']:
                    record['created_at'] = record['created_at'].isoformat()
                
                records.append(record)
            
            return records
            
    except Exception as e:
        print(f"❌ Failed to view disease surveillance: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


# Laboratory Screening
def add_lab_screening_record(maternal_health_id, data, personnel_id):
    """Add laboratory screening record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_lab_screening_record(%s, %s, %s, %s, %s, %s, %s)",
                [
                    maternal_health_id,
                    data['test_type_id'],
                    data['test_date'],
                    data.get('result'),
                    data.get('iron_tablet_given_date'),
                    data.get('iron_tablet_quantity'),
                    personnel_id
                ]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to add lab screening: {str(e)}")
        raise Exception(f"Failed to add lab screening: {str(e)}")


def view_maternal_all_lab_screening(maternal_health_id):
    """View all lab screening records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM view_specific_maternal_all_laboratory_screening(%s)
            """, [maternal_health_id])
            
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            
            records = []
            for row in results:
                record = dict(zip(columns, row))
                
                # Convert dates to ISO format
                if 'test_date' in record and record['test_date']:
                    record['test_date'] = record['test_date'].isoformat()
                if 'iron_tablet_given_date' in record and record['iron_tablet_given_date']:
                    record['iron_tablet_given_date'] = record['iron_tablet_given_date'].isoformat()
                if 'created_at' in record and record['created_at']:
                    record['created_at'] = record['created_at'].isoformat()
                
                records.append(record)
            
            return records
            
    except Exception as e:
        print(f"❌ Failed to view lab screening: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


# Checkup Records
def add_checkup_record(maternal_health_id, data, personnel_id):
    """Add trimester checkup record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_checkup_record(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    maternal_health_id,
                    data['aog_weeks'],
                    data['weight_kg'],
                    data['height_cm'],
                    data.get('bmi'),
                    data.get('blood_pressure'),
                    data.get('fetal_heart_rate'),
                    data.get('laboratory_results'),
                    data.get('notes'),
                    personnel_id
                ]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to add checkup record: {str(e)}")
        raise Exception(f"Failed to add checkup record: {str(e)}")


def view_maternal_all_checkups(maternal_health_id):
    """View all checkup records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM view_specific_maternal_all_checkup_record(%s)",
                [maternal_health_id]
            )
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                
                # Convert dates to ISO format
                if 'date_of_checkup' in record and record['date_of_checkup']:
                    record['date_of_checkup'] = record['date_of_checkup'].isoformat()
                if 'date_of_visit' in record and record['date_of_visit']:
                    record['date_of_visit'] = record['date_of_visit'].isoformat()
                
                results.append(record)
            
            return results
    except Exception as e:
        print(f"Failed to view checkups: {str(e)}")
        raise Exception(f"Failed to view checkups: {str(e)}")


def view_checkup_record_track(maternal_health_id):
    """View checkup tracking (counts by trimester)"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM checkup_record_track(%s)",
                [maternal_health_id]
            )
            columns = [col[0] for col in cursor.description]
            result = cursor.fetchone()
            return dict(zip(columns, result)) if result else None
    except Exception as e:
        print(f"Failed to view checkup track: {str(e)}")
        raise Exception(f"Failed to view checkup track: {str(e)}")


# Supplements
def add_maternal_supplement_record(maternal_health_id, data, personnel_id):
    """Add micronutrient supplement record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_maternal_supplement_record(%s, %s, %s, %s, %s)",
                [
                    maternal_health_id,
                    data['supplement_type_id'],
                    data['date_given'],
                    data.get('number_of_tablets'),
                    personnel_id
                ]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to add supplement: {str(e)}")
        raise Exception(f"Failed to add supplement: {str(e)}")


def view_maternal_all_supplements(maternal_health_id):
    """View all supplement records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM view_specific_maternal_all_supplements_record(%s)",
                [maternal_health_id]
            )
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Failed to view supplements: {str(e)}")
        raise Exception(f"Failed to view supplements: {str(e)}")


# Deworming
def add_deworming_record(maternal_health_id, data, personnel_id):
    """Add deworming record"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_deworming_record(%s, %s, %s, %s, %s)",
                [
                    maternal_health_id,
                    data['deworming_type_id'],
                    data.get('number_of_tablets'),
                    data['date_given'],
                    personnel_id
                ]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to add deworming: {str(e)}")
        raise Exception(f"Failed to add deworming: {str(e)}")


def view_maternal_all_deworming(maternal_health_id):
    """View all deworming records"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM view_specific_maternal_all_deworming_record(%s)",
                [maternal_health_id]
            )
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Failed to view deworming: {str(e)}")
        raise Exception(f"Failed to view deworming: {str(e)}")


# Pregnancy Outcome
def add_delivery_outcome(maternal_health_id, data, personnel_id):
    """Add delivery outcome (marks record as Completed)"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_delivery_outcome(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    maternal_health_id,
                    data['outcome_type_id'],
                    data['delivery_type_id'],
                    data['place_delivery_type_id'],
                    data.get('ownership_type_id'),
                    data.get('others_description'),
                    data['birth_attendant_id'],
                    data.get('other_attendant'),
                    data.get('time_of_delivery'),
                    data['date_terminated'],
                    personnel_id
                ]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to add delivery outcome: {str(e)}")
        raise Exception(f"Failed to add delivery outcome: {str(e)}")


def view_maternal_delivery_outcome(maternal_health_id):
    """View delivery outcome"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM view_specific_maternal_delivery_outcome(%s)",
                [maternal_health_id]
            )
            columns = [col[0] for col in cursor.description]
            result = cursor.fetchone()
            return dict(zip(columns, result)) if result else None
    except Exception as e:
        print(f"Failed to view delivery outcome: {str(e)}")
        raise Exception(f"Failed to view delivery outcome: {str(e)}")


# Postpartum
def add_postpartum_visit(maternal_health_id, data, personnel_id):
    """Add postpartum visit"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_postpartum_visit(%s, %s, %s, %s, %s, %s, %s, %s)",
                [
                    maternal_health_id,
                    data.get('date_of_visit'),
                    data.get('weight_kg'),
                    data.get('height_cm'),
                    data.get('blood_pressure'),
                    data.get('notes'),
                    data.get('laboratory_notes'),
                    personnel_id
                ]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        print(f"Failed to add postpartum visit: {str(e)}")
        raise Exception(f"Failed to add postpartum visit: {str(e)}")


def view_maternal_all_postpartum_visits(maternal_health_id):
    """View all postpartum visits"""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM view_specific_maternal_all_postpartum_visit(%s)",
                [maternal_health_id]
            )
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Failed to view postpartum visits: {str(e)}")
        raise Exception(f"Failed to view postpartum visits: {str(e)}")

# ========================================
# VACCINE TYPE MANAGEMENT HELPERS
# ========================================

def view_all_vaccines():
    """View all vaccine types"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM view_all_vaccine()")
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                record = dict(zip(columns, row))
                
                # Convert interval to string for JSON
                if 'interval_between_doses' in record and record['interval_between_doses']:
                    record['interval_between_doses'] = str(record['interval_between_doses'])
                if 'date_added' in record and record['date_added']:
                    record['date_added'] = record['date_added'].isoformat()
                if 'updated_at' in record and record['updated_at']:
                    record['updated_at'] = record['updated_at'].isoformat()
                
                results.append(record)
            
            return results
    except Exception as e:
        print(f"❌ Failed to view vaccines: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def view_specific_vaccine(vaccine_type_id):
    """View specific vaccine type details"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM view_specific_vaccine(%s)", [vaccine_type_id])
            columns = [col[0] for col in cursor.description]
            row = cursor.fetchone()
            
            if not row:
                return None
            
            record = dict(zip(columns, row))
            
            # Convert interval to string
            if 'interval_between_doses' in record and record['interval_between_doses']:
                record['interval_between_doses'] = str(record['interval_between_doses'])
            if 'date_added' in record and record['date_added']:
                record['date_added'] = record['date_added'].isoformat()
            if 'updated_at' in record and record['updated_at']:
                record['updated_at'] = record['updated_at'].isoformat()
            
            return record
    except Exception as e:
        print(f"❌ Failed to view vaccine: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def insert_vaccine(data, personnel_id):
    """Insert new vaccine type"""
    try:
        with connection.cursor() as cursor:
            # Convert interval string to PostgreSQL interval
            interval_str = data.get('interval_between_doses')
            
            cursor.execute("""
                SELECT insert_vaccine(
                    %s, %s, %s, %s, %s, %s::interval, %s
                )
            """, [
                data['vaccine_name'],
                data.get('at_birth', False),
                data.get('first_dose', False),
                data.get('second_dose', False),
                data.get('third_dose', False),
                interval_str,  # e.g., '4 weeks'
                personnel_id
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"❌ Failed to insert vaccine: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def update_vaccine(vaccine_type_id, data, personnel_id):
    """Update vaccine type"""
    try:
        with connection.cursor() as cursor:
            interval_str = data.get('interval_between_doses')
            
            cursor.execute("""
                SELECT update_vaccine(
                    %s, %s, %s, %s, %s, %s, %s::interval, %s
                )
            """, [
                vaccine_type_id,
                data.get('vaccine_name'),
                data.get('at_birth'),
                data.get('first_dose'),
                data.get('second_dose'),
                data.get('third_dose'),
                interval_str,
                personnel_id
            ])
            
            result = cursor.fetchone()
            return result[0] if result else None
    except Exception as e:
        print(f"❌ Failed to update vaccine: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")


def get_next_allowed_dose(child_health_id, vaccine_type_id):
    """Get the next allowed dose for a child's vaccine"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT * FROM get_dose_type_latest(%s, %s)
            """, [child_health_id, vaccine_type_id])
            
            result = cursor.fetchone()
            if result:
                return {
                    'dose_type_id': result[0],
                    'dose_name': result[1]
                }
            return None
    except Exception as e:
        print(f"❌ Failed to get next dose: {str(e)}")
        raise Exception(f"Database operation failed: {str(e)}")