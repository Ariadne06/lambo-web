import os
from django.db import connection
from ..supabase_storage import upload_file_to_supabase

class ProfileService:
    """Service to handle resident profile updates."""
    
    @staticmethod
    def update_resident_profile(resident_id, form_data, profile_image_file=None):
        """
        Update resident profile with proper business logic.
        Returns: dict with success status and data
        """
        try:
            # 1. Get resident status to determine which function to use
            resident_status = ProfileService._get_resident_status(resident_id)
            if not resident_status:
                return {
                    'success': False,
                    'message': 'Resident not found',
                    'status_code': 404
                }
            
            # 2. Handle profile image upload if provided
            profile_image_path = None
            if profile_image_file:
                profile_image_path = ProfileService._upload_profile_image(profile_image_file, resident_id)
            
            # 3. Get current resident data for required fields
            current_data = ProfileService._get_current_resident_data(resident_id)
            if not current_data:
                return {
                    'success': False,
                    'message': 'Resident data not found',
                    'status_code': 404
                }
            
            # 4. Update based on resident type
            if resident_status.lower() == 'non-resident':
                ProfileService._update_non_resident(resident_id, form_data, current_data, profile_image_path)
            else:
                ProfileService._update_regular_resident(resident_id, form_data, current_data, profile_image_path)
            
            return {
                'success': True,
                'message': 'Profile updated successfully',
                'profile_image_url': profile_image_path,
                'status_code': 200
            }
            
        except Exception as e:
            print(f"Profile update error: {str(e)}")
            return {
                'success': False,
                'message': f'Failed to update profile: {str(e)}',
                'status_code': 500
            }
    
    @staticmethod
    def _get_resident_status(resident_id):
        """Get resident status name."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT rs.status_name 
                    FROM Resident r 
                    JOIN Resident_Status rs ON r.status_id = rs.status_id 
                    WHERE r.resident_id = %s
                """, [resident_id])
                
                result = cursor.fetchone()
                return result[0] if result else None
        except Exception:
            return None
    
    @staticmethod
    def _get_current_resident_data(resident_id):
        """Get current resident data for required fields."""
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT r.first_name, r.last_name, r.dob, r.sex, a.barangay, a.city_municipality
                    FROM Resident r 
                    LEFT JOIN Address a ON r.address_id = a.address_id
                    WHERE r.resident_id = %s
                """, [resident_id])
                
                result = cursor.fetchone()
                if result:
                    return {
                        'first_name': result[0],
                        'last_name': result[1],
                        'dob': result[2],
                        'sex': result[3],
                        'barangay': result[4],
                        'city_municipality': result[5]
                    }
                return None
        except Exception:
            return None
    
    @staticmethod
    def _upload_profile_image(image_file, resident_id):
        """Upload profile image to Supabase Storage."""
        try:
            supabase_path = upload_file_to_supabase(
                file=image_file,
                bucket_name='profile-images',  
                folder='profile_images'       
            )
            
            if supabase_path:
                # Check if it's already a full URL or just a path
                if supabase_path.startswith('http'):
                    return supabase_path
                else:
                    # Construct the public URL
                    base_url = os.getenv('SUPABASE_URL')
                    return f"{base_url}/storage/v1/object/public/profile-images/{supabase_path}"
            else:
                raise Exception("Upload failed - no path returned from Supabase")
                
        except Exception as e:
            raise Exception(f"Failed to upload profile image: {str(e)}")
    
    @staticmethod
    def _update_non_resident(resident_id, form_data, current_data, profile_image_path):
        """Update non-resident using update_business_owner function."""
        request_by = resident_id  # User updates their own profile
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT update_business_owner(
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                resident_id,                                           # p_resident_id
                request_by,                                            # p_request_by
                current_data['last_name'],                            # p_last_name (unchanged)
                current_data['first_name'],                           # p_first_name (unchanged)
                current_data['dob'],                                  # p_dob (unchanged)
                current_data['sex'],                                  # p_sex (unchanged)
                form_data.get('barangay', current_data['barangay']),  # p_barangay
                form_data.get('city_municipality', current_data['city_municipality']), # p_city_municipality
                None,                                                 # p_middle_name (unchanged for non-residents)
                None,                                                 # p_suffix (unchanged for non-residents)
                form_data.get('email'),                               # p_email
                form_data.get('phone_number'),                        # p_phone_number
                form_data.get('house_number'),                        # p_house_number
                form_data.get('street'),                              # p_street
                form_data.get('country', 'Philippines'),              # p_country
                profile_image_path                                    # p_profile_image_path
            ])
    
    @staticmethod
    def _update_regular_resident(resident_id, form_data, current_data, profile_image_path):
        """Update regular resident using update_resident function."""
        request_by = resident_id  # User updates their own profile
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT update_resident(
                    %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, [
                resident_id,                                          # p_resident_id
                request_by,                                           # p_request_by
                current_data['last_name'],                           # p_last_name (unchanged)
                current_data['first_name'],                          # p_first_name (unchanged)
                current_data['dob'],                                 # p_dob (unchanged)
                current_data['sex'],                                 # p_sex (unchanged)
                current_data['barangay'],                            # p_barangay (unchanged for residents)
                current_data['city_municipality'],                   # p_city_municipality (unchanged for residents)
                None,                                                # p_middle_name (unchanged)
                None,                                                # p_suffix (unchanged)
                form_data.get('gender'),                             # p_gender
                False,                                               # p_is_voter (HIDDEN: default to False)
                form_data.get('email'),                              # p_email
                form_data.get('phone_number'),                       # p_phone_number
                form_data.get('religion_cat_id'),                    # p_religion_cat_id
                form_data.get('other_religion'),                     # p_other_religion
                form_data.get('civil_stat_id'),                      # p_civil_stat_id
                form_data.get('educational_attain_id'),              # p_educational_attain_id
                form_data.get('house_number'),                       # p_house_number
                form_data.get('street'),                             # p_street
                None,                                                # p_sitio_id (unchanged)
                'Philippines',                                       # p_country (unchanged)
                profile_image_path                                   # p_profile_image_path
            ])