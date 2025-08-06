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
    religion_cat_id = serializers.IntegerField(write_only=True)
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
    civil_status_id = serializers.IntegerField(write_only=True, required=True)
    educational_attainment_id = serializers.IntegerField(write_only=True, required=True)

    # Optional fields
    other_religion = serializers.CharField(write_only=True, required=False, allow_blank=True)
    profile_image_path = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    # Nested serializers for response
    religion = ReligionSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    civil_status = CivilStatusSerializer(read_only=True)
    educational_attainment = EducationalAttainmentSerializer(read_only=True)
    status = ResidentStatusSerializer(read_only=True)

    class Meta:
        model = Resident
        fields = [
            'last_name', 'first_name', 'middle_name', 'suffix', 'dob', 'sex', 'gender',
            'is_voter', 'email', 'phone_number', 'date_recorded',
            'civil_status', 'educational_attainment', 'status', 'address', 'religion',
            'religion_cat_id', 'house_number', 'street', 'barangay', 'sitio_id', 'city_municipality', 'country',
            'status_id', 'id_image', 'password', 'username', 'civil_status_id', 'educational_attainment_id',
            'identity_doc_type_id', 'verification_type', 'document_number', 'expires_at',
            'other_religion', 'profile_image_path'
        ]

    def create(self, validated_data):
        try:
            # Upload file to Supabase and get file path
            id_image_file = validated_data.pop('id_image')
            file_path = upload_file_to_supabase(id_image_file)

            # Debug logging
            print(f"File name: {id_image_file.name}")
            print(f"File content type: {id_image_file.content_type}")
            print(f"File size: {id_image_file.size}")
            
            # Prepare parameters for the new database function
            params = [
                validated_data.get('last_name'),
                validated_data.get('first_name'),
                validated_data.get('dob'),
                validated_data.get('sex'),
                validated_data.get('barangay'),
                validated_data.get('city_municipality'),
                validated_data.get('username'),
                validated_data.get('password'),  # Function will handle hashing
                validated_data.get('verification_type', 'ID'),
                file_path,  # Supabase file path instead of base64
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

            print("PARAMS SENT TO DB:", params)
        
            with connection.cursor() as cursor:
                cursor.execute("""
                    SELECT register_verified_resident(
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, params)
                resident_id = cursor.fetchone()[0]

            resident = Resident.objects.get(resident_id=resident_id)
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