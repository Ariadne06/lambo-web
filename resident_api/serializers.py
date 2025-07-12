from rest_framework import serializers
from resident_profiling_module.models import Resident, Religion, CivilStatus, EducationalAttainment, Sitio, ResidentStatus, ReligionCategory, Address
from django.db import connection
import hashlib

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

class ResidentRegistrationSerializer(serializers.ModelSerializer):
    religion_cat_id = serializers.IntegerField(write_only=True)
    # Address fields
    house_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    street = serializers.CharField(write_only=True, required=False, allow_blank=True)
    barangay = serializers.CharField(write_only=True, required=False, allow_blank=True)
    sitio_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    city_municipality = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    
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
        ]

    def create(self, validated_data):
        
        data = self.context['request'].data
         
        plain_password = data.get('password', '')
        password_hashed = hashlib.sha256(plain_password.encode()).hexdigest()
        
        params = [
            data.get('last_name'),
            data.get('first_name'),
            data.get('dob'),
            data.get('sex'),
            data.get('barangay'),
            data.get('city_municipality'),
            data.get('status'),  
            data.get('username'),
            password_hashed,  
            data.get('doc_type', 'ID'),  
            data.get('image_base64', ''),  
            data.get('middle_name', ''),  
            data.get('suffix', ''),  
            data.get('gender', ''),  
            data.get('is_voter', False),
            data.get('email', ''), 
            data.get('phone_number', ''),  
            data.get('religion_cat_id'),
            data.get('other_religion', ''), 
            data.get('civil_status'),  
            data.get('educational_attainment'), 
            data.get('house_number', ''),  
            data.get('street', ''),  
            data.get('sitio_id'),
            data.get('country', 'Philippines'),
            data.get('req_pass_change', False),
            data.get('document_type', ''),  
            data.get('document_number', ''),  
            data.get('uploaded_by', 1),  
        ]

    
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT register_verified_resident(
                    %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
            """, params)
            resident_id = cursor.fetchone()[0]

        
        resident = Resident.objects.get(resident_id=resident_id)
        return resident


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