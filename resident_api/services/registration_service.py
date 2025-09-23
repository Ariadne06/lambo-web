from ..utils.database_helpers import execute_registration_function
from ..supabase_storage import upload_file_to_supabase
from resident_profiling_module.models import Resident

class RegistrationService:
    """Service to handle different types of resident registration."""
    
    @staticmethod
    def register_resident(validated_data):
        """Register a regular resident."""
        # Upload file
        id_image_file = validated_data.pop('id_image')
        file_path = upload_file_to_supabase(id_image_file, folder='id-documents')
        
        # Prepare parameters
        params = RegistrationService._prepare_resident_params(validated_data, file_path)
        
        # Execute registration
        resident_id = execute_registration_function('register_verified_resident', params)
        
        return Resident.objects.get(resident_id=resident_id)
    
    @staticmethod
    def register_non_resident(validated_data):
        """Register a non-resident business owner."""
        # Upload file
        id_image_file = validated_data.pop('id_image')
        file_path = upload_file_to_supabase(id_image_file, folder='non-residents-docs')
        
        # Prepare parameters
        params = RegistrationService._prepare_non_resident_params(validated_data, file_path)
        
        # Execute registration
        resident_id = execute_registration_function('register_verified_non_resident', params)
        
        return Resident.objects.get(resident_id=resident_id)
    
    @staticmethod
    def register_via_guardian(validated_data):
        """Register via guardian verification."""
        # Upload file
        id_image_file = validated_data.pop('id_image')
        file_path = upload_file_to_supabase(id_image_file, folder='guardian-docs')
        
        # Determine guardian type and function
        guardian_type = validated_data.get('guardian_type')
        if guardian_type == 'GUARDIAN_ID':
            params = RegistrationService._prepare_guardian_id_params(validated_data, file_path)
            function_name = 'register_verified_via_guardian_id'
        else:
            params = RegistrationService._prepare_guardian_doc_params(validated_data, file_path)
            function_name = 'register_verified_via_guardian_doc'
        
        # Execute registration
        resident_id = execute_registration_function(function_name, params)
        
        return Resident.objects.get(resident_id=resident_id)
    
    @staticmethod
    def register_non_resident_via_guardian(validated_data):
        """Register a non-resident via guardian verification."""
        id_image_file = validated_data.pop('id_image')
        file_path = upload_file_to_supabase(id_image_file, folder='guardian-docs')

        guardian_type = validated_data.get('guardian_type')
        if guardian_type == 'GUARDIAN_ID':
            params = RegistrationService._prepare_guardian_id_params_non_resident(validated_data, file_path)
            function_name = 'register_verified_via_guardian_id_non_resident'
        else:
            params = RegistrationService._prepare_guardian_doc_params_non_resident(validated_data, file_path)
            function_name = 'register_verified_via_guardian_doc_non_resident'

        resident_id = execute_registration_function(function_name, params)
        return Resident.objects.get(resident_id=resident_id)
    
    @staticmethod
    def _prepare_resident_params(validated_data, file_path):
        """Prepare parameters for resident registration."""
        return [
            validated_data.get('last_name'),
            validated_data.get('first_name'),
            validated_data.get('dob'),
            validated_data.get('sex'),
            validated_data.get('barangay'),
            validated_data.get('city_municipality'),
            validated_data.get('username'),
            validated_data.get('password'),
            validated_data.get('verification_type', 'ID'),
            file_path,
            validated_data.get('identity_doc_type_id'),
            validated_data.get('middle_name'),
            validated_data.get('suffix'),
            validated_data.get('gender'),
            validated_data.get('is_voter', False),
            validated_data.get('email'),
            validated_data.get('phone_number'),
            validated_data.get('religion_cat_id'),
            validated_data.get('other_religion'),
            validated_data.get('civil_status_id'),
            validated_data.get('educational_attainment_id'),
            validated_data.get('house_number'),
            validated_data.get('street'),
            validated_data.get('sitio_id'),
            validated_data.get('country', 'Philippines'),
            validated_data.get('profile_image_path'),
            validated_data.get('document_number'),
            validated_data.get('expires_at'),
            validated_data.get('is_pwd', False),
            validated_data.get('occupation_id'),
            validated_data.get('nationality_id'),
            validated_data.get('employment_status_id'),
            
        ]
    
    @staticmethod
    def _prepare_non_resident_params(validated_data, file_path):
        """Prepare parameters for non-resident registration."""
        return [
            validated_data.get('last_name'),
            validated_data.get('first_name'),
            validated_data.get('dob'),
            validated_data.get('sex'),
            validated_data.get('barangay'),
            validated_data.get('city_municipality'),
            validated_data.get('username'),
            validated_data.get('password'),
            validated_data.get('verification_type', 'SUPPORTING'),
            file_path,

            validated_data.get('middle_name'),
            validated_data.get('suffix'),
            validated_data.get('email'),
            validated_data.get('phone_number'),
            validated_data.get('house_number'),
            validated_data.get('street'),
            validated_data.get('country', 'Philippines'),
            validated_data.get('profile_image_path'),
            validated_data.get('identity_doc_type_id'),
            validated_data.get('document_number'),
            validated_data.get('expires_at'),
        ]
    
    @staticmethod
    def _prepare_guardian_id_params(validated_data, file_path):
        """Prepare parameters for guardian ID registration."""
        return [
            validated_data.get('last_name'),                
            validated_data.get('first_name'),             
            validated_data.get('dob'),                      
            validated_data.get('sex'),                      
            validated_data.get('barangay'),               
            validated_data.get('city_municipality'),        
            validated_data.get('username'),                 
            validated_data.get('password'),                
            validated_data.get('identity_doc_type_id'),     
            file_path,                                      
            validated_data.get('document_number'),          
            validated_data.get('expires_at'),              
            validated_data.get('guardian_username'),        
            validated_data.get('middle_name'),             
            validated_data.get('suffix'),                  
            validated_data.get('gender'),                  
            validated_data.get('is_voter', False),          
            validated_data.get('email'),                   
            validated_data.get('phone_number'),           
            validated_data.get('religion_cat_id'),          
            validated_data.get('other_religion'),           
            validated_data.get('civil_status_id'),          
            validated_data.get('educational_attainment_id'),
            validated_data.get('house_number'),             
            validated_data.get('street'),                   
            validated_data.get('sitio_id'),                
            validated_data.get('country', 'Philippines'),   
            validated_data.get('profile_image_path'),       
            validated_data.get('is_pwd', False),           
            validated_data.get('occupation_id'),            
            validated_data.get('nationality_id'),          
            validated_data.get('employment_status_id'),
        ]
    
    @staticmethod
    def _prepare_guardian_doc_params(validated_data, file_path):
        """Prepare parameters for guardian document registration."""
        return [
            validated_data.get('last_name'),
            validated_data.get('first_name'),
            validated_data.get('dob'),
            validated_data.get('sex'),
            validated_data.get('barangay'),
            validated_data.get('city_municipality'),
            validated_data.get('username'),
            validated_data.get('password'),
            validated_data.get('identity_doc_type_id'),
            file_path,
            validated_data.get('guardian_username'),
            validated_data.get('middle_name'),
            validated_data.get('suffix'),
            validated_data.get('gender'),
            validated_data.get('is_voter', False),
            validated_data.get('email'),
            validated_data.get('phone_number'),
            validated_data.get('religion_cat_id'),
            validated_data.get('other_religion'),
            validated_data.get('civil_status_id'),
            validated_data.get('educational_attainment_id'),
            validated_data.get('house_number'),
            validated_data.get('street'),
            validated_data.get('sitio_id'),
            validated_data.get('country', 'Philippines'),
            validated_data.get('profile_image_path'),
            validated_data.get('is_pwd', False),
            validated_data.get('occupation_id'),
            validated_data.get('nationality_id'),
            validated_data.get('employment_status_id'),
        ]
    
    @staticmethod
    def _prepare_guardian_id_params_non_resident(validated_data, file_path):
        """Prepare parameters for non-resident guardian ID registration."""
        return [
            validated_data.get('last_name'),
            validated_data.get('first_name'),
            validated_data.get('dob'),
            validated_data.get('sex'),
            validated_data.get('barangay'),
            validated_data.get('city_municipality'),
            validated_data.get('username'),
            validated_data.get('password'),
            validated_data.get('identity_doc_type_id'),
            file_path,
            validated_data.get('document_number'),
            validated_data.get('expires_at'),
            validated_data.get('guardian_username'),
            validated_data.get('middle_name'),
            validated_data.get('suffix'),
            validated_data.get('email'),
            validated_data.get('phone_number'),
            validated_data.get('house_number'),
            validated_data.get('street'),
            validated_data.get('country', 'Philippines'),
            validated_data.get('profile_image_path'),
        ]

    @staticmethod
    def _prepare_guardian_doc_params_non_resident(validated_data, file_path):
        """Prepare parameters for non-resident guardian supporting doc registration."""
        return [
            validated_data.get('last_name'),
            validated_data.get('first_name'),
            validated_data.get('dob'),
            validated_data.get('sex'),
            validated_data.get('barangay'),
            validated_data.get('city_municipality'),
            validated_data.get('username'),
            validated_data.get('password'),
            validated_data.get('identity_doc_type_id'),
            file_path,
            validated_data.get('guardian_username'),
            validated_data.get('middle_name'),
            validated_data.get('suffix'),
            validated_data.get('email'),
            validated_data.get('phone_number'),
            validated_data.get('house_number'),
            validated_data.get('street'),
            validated_data.get('country', 'Philippines'),
            validated_data.get('profile_image_path'),
        ]