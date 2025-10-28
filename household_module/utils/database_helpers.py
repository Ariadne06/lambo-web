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