from rest_framework import serializers
from resident_profiling_module.models import Resident, Religion, CivilStatus, EducationalAttainment, Sitio, ResidentStatus, ReligionCategory, Address, IdentityDocType
from django.db import connection
from .supabase_storage import upload_file_to_supabase
import hashlib
import base64

class ReligionSerializer(serializers.ModelSerializer):
    religion_name = serializers.SerializerMethodField()

    class Meta:
        model = Religion
        fields = ['religion_id', 'religion_name']

    def get_religion_name(self, obj):
        # Customize as needed; this is a common pattern:
        if obj.other_religion:
            return obj.other_religion
        return obj.religion_cat.religion_name


class SitioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sitio
        fields = ['sitio_id', 'sitio_name']

class AddressSerializer(serializers.ModelSerializer):
    sitio = SitioSerializer(read_only=True)

    class Meta:
        model = Address
        fields = [
            'address_id',
            'house_number',
            'street',
            'barangay',
            'sitio',
            'city_municipality',
            'country',
        ]


class CivilStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = CivilStatus
        fields = ['civil_stat_id', 'civil_name']

class EducationalAttainmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = EducationalAttainment
        fields = ['educational_attain_id', 'educational_attain_name']


class ResidentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResidentStatus
        fields = ['status_id', 'status_name']

class IdentityDocTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = IdentityDocType
        fields = ['identity_doc_type_id', 'name']

class ResidentRegistrationSerializer(serializers.ModelSerializer):
    religion_cat_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    status_id = serializers.IntegerField(write_only=True, required=True)

    identity_doc_type_id = serializers.IntegerField(write_only=True, required=True)
    verification_type = serializers.CharField(write_only=True, default='ID')

    # Address fields
    house_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    street = serializers.CharField(write_only=True, required=False, allow_blank=True)
    barangay = serializers.CharField(write_only=True, required=False, allow_blank=True)
    sitio_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    city_municipality = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)

    # Document fields
    id_image = serializers.ImageField(write_only=True, required=True) 
    document_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    expires_at = serializers.DateField(write_only=True, required=False, allow_null=True)

    #Credentials
    password = serializers.CharField(write_only=True, required=True)  
    username = serializers.CharField(write_only=True, required=True)

    #Status fields
    civil_status_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    educational_attainment_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    # Optional fields
    other_religion = serializers.CharField(write_only=True, required=False, allow_blank=True)
    profile_image_path = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Nested serializers for response
    religion = ReligionSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    civil_status = CivilStatusSerializer(read_only=True)
    educational_attainment = EducationalAttainmentSerializer(read_only=True)
    status = ResidentStatusSerializer(read_only=True)

    # User handling
    user_type = serializers.CharField(write_only=True, default='resident')
    registration_function = serializers.CharField(write_only=True, default='register_verified_resident')

    # registration response
    is_verified = serializers.BooleanField(read_only=True)
    verification_status = serializers.SerializerMethodField()

    guardian_username = serializers.CharField(write_only=True, required=False, allow_blank=True)
    guardian_type = serializers.CharField(write_only=True, required=False, allow_blank=True)
    

    class Meta:
        model = Resident
        fields = [
            'last_name', 'first_name', 'middle_name', 'suffix', 'dob', 'sex', 'gender',
            'is_voter', 'email', 'phone_number', 'date_recorded',
            'civil_status', 'educational_attainment', 'status', 'address', 'religion',
            'religion_cat_id', 'house_number', 'street', 'barangay', 'sitio_id', 'city_municipality', 'country',
            'status_id', 'id_image', 'password', 'username', 'civil_status_id', 'educational_attainment_id',
            'identity_doc_type_id', 'verification_type', 'document_number', 'expires_at',
            'other_religion', 'profile_image_path', 'user_type', 'registration_function', 'is_verified', 'verification_status', 'guardian_username', 'guardian_type'
        ]

    def validate(self, data):
        #Custom validation
        user_type = data.get('user_type', 'resident')
        verification_type = data.get('verification_type', 'ID')

        # For resident, required demographic fields
        if user_type == 'resident':
            required_fields = ['religion_cat_id', 'civil_status_id', 'educational_attainment_id']
            for field in required_fields:
                if not data.get(field):
                    raise serializers.ValidationError({field: 'This field is required for residents.'})
        
         # For guardian verification, guardian username is required
        if verification_type == 'GUARDIAN':
            guardian_username = data.get('guardian_username', '').strip()
            guardian_type = data.get('guardian_type', '').strip()
            
            if not guardian_username:
                raise serializers.ValidationError({'guardian_username': 'Guardian username is required for guardian verification.'})
            
            if not guardian_type or guardian_type not in ['GUARDIAN_ID', 'GUARDIAN_SUPPORTING']:
                raise serializers.ValidationError({'guardian_type': 'Valid guardian type is required (GUARDIAN_ID or GUARDIAN_SUPPORTING).'})

        return data
    
    def get_verification_status(self, obj):
        if obj.is_verified:
            return {
                'status': 'verified',
                'message': 'Your account has been successfully verified.',
                'needs_wait': False
            }
        else:
            return {
                'status': 'Pending',
                'message': 'Your account is pending verification. Please wait for approval.',
                'needs_wait': True
            }

    def create(self, validated_data):
        try:
            # User type and registration function
            user_type = validated_data.pop('user_type', 'resident')
            registration_function = validated_data.pop('registration_function', 'register_verified_resident')

            verification_type = validated_data.get('verification_type')
            guardian_username = validated_data.get('guardian_username')

            print(f"Processing {user_type} registration using {registration_function}")

            # Upload file to Supabase and get file path
            id_image_file = validated_data.pop('id_image')
            # file_path = upload_file_to_supabase(id_image_file)

            # storage folder base on user type
            if verification_type == 'GUARDIAN':
                file_path = upload_file_to_supabase(id_image_file, folder='guardian-docs')
            elif user_type == 'non_resident':
                file_path = upload_file_to_supabase(id_image_file, folder='non-residents-docs')
            else:
                file_path = upload_file_to_supabase(id_image_file, folder='id-documents')

            # Debug logging
            print(f"File name: {id_image_file.name}")
            print(f"File content type: {id_image_file.content_type}")
            print(f"File size: {id_image_file.size}")

            print(f"File uploaded to: {file_path}")
            print(f"User type: {user_type}")
            print(f"Using function: {registration_function}")

            # Verification Log
            
            # Check if this is guardian registration
            verification_type = validated_data.get('verification_type')
            guardian_username = validated_data.get('guardian_username')
           
            # Prepare parameters based on user type
            if verification_type == 'GUARDIAN' and guardian_username:
                # Guardian registration flow
                guardian_type = validated_data.get('guardian_type')

                if guardian_type == 'GUARDIAN_ID':  # ← Fix: was 'ID', should be 'GUARDIAN_ID'
                    params = self._prepare_guardian_id_params(validated_data, file_path)
                    registration_function = 'register_verified_via_guardian_id'
                    print(f"Using Guardian ID registration: {registration_function}")
                else:  # guardian_type == 'GUARDIAN_SUPPORTING'
                    params = self._prepare_guardian_doc_params(validated_data, file_path)
                    registration_function = 'register_verified_via_guardian_doc'
                    print(f"Using Guardian Document registration: {registration_function}")
            else:
                # Existing resident/non-resident logic
                if user_type == 'non_resident':
                    params = self._prepare_non_resident_params(validated_data, file_path)
                else:
                    params = self._prepare_resident_params(validated_data, file_path)

            print("PARAMS SENT TO DB:", params)

            # Call appropriate database function
            with connection.cursor() as cursor:
                placeholders = ', '.join(['%s'] * len(params))
                cursor.execute(f"SELECT {registration_function}({placeholders})", params)
                resident_id = cursor.fetchone()[0]

            resident = Resident.objects.get(resident_id=resident_id)

            print(f" Registration complete!")
            print(f" Document type: {validated_data.get('verification_type')}")
            print(f" Auto-verified: {resident.is_verified}")

            return resident
        

        except Exception as e:
            print(f"Registration failed: {str(e)}")
            raise serializers.ValidationError(f"Registration failed: {str(e)}")
        
    def _prepare_non_resident_params(self, validated_data, file_path):
        """Parameters for register_verified_business_owner function."""
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
            None,                                      # p_profile_image_path (optional)
            validated_data.get('identity_doc_type_id'), 
            validated_data.get('document_number'),     
            validated_data.get('expires_at'),          
        ]

    def _prepare_resident_params(self, validated_data, file_path):
        """Parameters for register_verified_resident function"""
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
        ]
    
    def _prepare_guardian_id_params(self, validated_data, file_path):
        """Parameters for register_verified_via_guardian_id function."""
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
            validated_data.get('email'),
            validated_data.get('phone_number'),
            validated_data.get('house_number'),
            validated_data.get('street'),
            validated_data.get('sitio_id'),
            validated_data.get('country', 'Philippines'),
            validated_data.get('profile_image_path'),
        ]

    def _prepare_guardian_doc_params(self, validated_data, file_path):
        """Parameters for register_verified_via_guardian_doc function."""
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
            validated_data.get('email'),
            validated_data.get('phone_number'),
            validated_data.get('house_number'),
            validated_data.get('street'),
            validated_data.get('sitio_id'),
            validated_data.get('country', 'Philippines'),
            validated_data.get('profile_image_path'),
        ]
    


class ReligionCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ReligionCategory
        fields = ['religion_cat_id', 'religion_name']




class ResidentSerializer(serializers.ModelSerializer):

    religion = ReligionSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    civil_status = CivilStatusSerializer(read_only=True)
    educational_attainment = EducationalAttainmentSerializer(read_only=True)
    status = ResidentStatusSerializer(read_only=True)
    
    class Meta:
        model = Resident
        fields = '__all__'