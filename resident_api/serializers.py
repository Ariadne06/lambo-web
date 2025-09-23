from rest_framework import serializers
from resident_profiling_module.models import EmploymentStatus, Nationality, Occupation, Resident, Religion, CivilStatus, EducationalAttainment, Sitio, ResidentStatus, ReligionCategory, Address, IdentityDocType
from django.db import connection
from .supabase_storage import upload_file_to_supabase
from .services.registration_service import RegistrationService
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

class OccupationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Occupation
        fields = ['occupation_id', 'occupation_name']

class NationalitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Nationality
        fields = ['nationality_id', 'nationality', 'country_name']

class EmploymentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmploymentStatus
        fields = ['employment_status_id', 'employment_status_name']

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

    # added fields

    occupation_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    nationality_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    employment_status_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    is_pwd = serializers.BooleanField(write_only=True, required=False, default=False)
    

    class Meta:
        model = Resident
        fields = [
            'last_name', 'first_name', 'middle_name', 'suffix', 'dob', 'sex', 'gender',
            'is_voter', 'email', 'phone_number', 'date_recorded',
            'civil_status', 'educational_attainment', 'status', 'address', 'religion',
            'religion_cat_id', 'house_number', 'street', 'barangay', 'sitio_id', 'city_municipality', 'country',
            'status_id', 'id_image', 'password', 'username', 'civil_status_id', 'educational_attainment_id',
            'identity_doc_type_id', 'verification_type', 'document_number', 'expires_at',
            'other_religion', 'profile_image_path', 'user_type', 'registration_function', 'is_verified', 'verification_status', 'guardian_username', 'guardian_type',
            'occupation_id', 'nationality_id', 'employment_status_id', 'is_pwd',
        ]

    def validate(self, data):
        """Custom validation logic."""
        user_type = data.get('user_type', 'resident')
        verification_type = data.get('verification_type', 'ID')

        # For resident, required demographic fields
        if user_type == 'resident':
            required_fields = ['religion_cat_id', 'civil_status_id', 'educational_attainment_id', 'occupation_id', 'nationality_id', 'employment_status_id']
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
        """Get verification status for response."""
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
        """Create resident using appropriate registration method."""
        try:
            user_type = validated_data.get('user_type', 'resident')
            verification_type = validated_data.get('verification_type', 'ID')
            guardian_username = validated_data.get('guardian_username')

            print(f"Processing {user_type} registration with verification: {verification_type}")

             # Route to appropriate registration service
            if user_type == 'non_resident' and verification_type == 'GUARDIAN' and guardian_username:
                # Non-resident via guardian
                resident = RegistrationService.register_non_resident_via_guardian(validated_data)
            elif verification_type == 'GUARDIAN' and guardian_username:
                # Resident via guardian
                resident = RegistrationService.register_via_guardian(validated_data)
            elif user_type == 'non_resident':
                resident = RegistrationService.register_non_resident(validated_data)
            else:
                resident = RegistrationService.register_resident(validated_data)

            print(f"Registration complete! Auto-verified: {resident.is_verified}")
            return resident

        except Exception as e:
            print(f"Registration failed: {str(e)}")
            raise serializers.ValidationError(f"Registration failed: {str(e)}")

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