from django.db import connection

def execute_registration_function(function_name, params):
    """Execute a registration database function with given parameters."""
    try:
        with connection.cursor() as cursor:
            placeholders = ', '.join(['%s'] * len(params))
            cursor.execute(f"SELECT {function_name}({placeholders})", params)
            result = cursor.fetchone()[0]
            return result
    except Exception as e:
        raise Exception(f"Database operation failed: {str(e)}")

def get_guardian_info(username):
    """Get guardian information by username."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT guardian_resident_id, last_name, first_name, middle_name, suffix, dob
                FROM get_guardian_identity_by_username(%s)
            """, [username])
            return cursor.fetchone()
    except Exception as e:
        return None

def get_resident_profile(resident_id):
    """Get resident profile by ID."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT get_resident_profile(%s)", [resident_id])
            result = cursor.fetchone()[0]
            return result
    except Exception as e:
        raise Exception(f"Failed to fetch profile: {str(e)}")

def mobile_login(username, password):
    """Handle mobile login through database function."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT login_user_mobile(%s, %s)", [username, password])
            result = cursor.fetchone()[0]
            return result
    except Exception as e:
        raise Exception(f"Login failed: {str(e)}")
    
def update_resident_profile(resident_id, update_data):
    """Update resident profile through database function."""
    try:
        with connection.cursor() as cursor:
            # Your existing update profile logic
            cursor.execute("SELECT update_resident_profile(%s, %s)", [resident_id, update_data])
            result = cursor.fetchone()[0]
            return result
    except Exception as e:
        raise Exception(f"Profile update failed: {str(e)}")
    
def change_personnel_password(personnel_id, old_password, new_password):
    """Change personnel password through database function."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT change_personnel_password(%s, %s, %s)", [personnel_id, old_password, new_password])
            result = cursor.fetchone()[0]
            return result
    except Exception as e:
        raise Exception(f"Password change failed: {str(e)}")
    
def resubmit_supporting_certificate(resident_id, identity_doc_type_id, new_file_path, note='resubmit photo'):
    """Call the SQL function for resubmission."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT resubmit_resident_supporting_certificate(%s, %s, %s, %s)",
                [resident_id, identity_doc_type_id, new_file_path, note]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        raise Exception(f"Resubmission failed: {str(e)}")

def re_register_resident(resident_id, performed_by=None, performed_by_type='resident', reason='details_mismatch'):
    """Call the SQL function for re-register."""
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT re_register_resident(%s, %s, %s, %s)",
                [resident_id, performed_by or resident_id, performed_by_type, reason]
            )
            return cursor.fetchone()[0]
    except Exception as e:
        raise Exception(f"Re-registration failed: {str(e)}")
