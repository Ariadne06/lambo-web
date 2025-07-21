from rest_framework import serializers
from resident_profiling_module.models import Resident, Religion, CivilStatus, EducationalAttainment, Sitio, ResidentStatus, ReligionCategory, Address
from django.db import connection
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

class ResidentRegistrationSerializer(serializers.ModelSerializer):
    religion_cat_id = serializers.IntegerField(write_only=True)
    status_id = serializers.IntegerField(write_only=True, required=True)
    # Address fields
    house_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    street = serializers.CharField(write_only=True, required=False, allow_blank=True)
    barangay = serializers.CharField(write_only=True, required=False, allow_blank=True)
    sitio_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    city_municipality = serializers.CharField(write_only=True)
    country = serializers.CharField(write_only=True)
    id_image = serializers.ImageField(write_only=True, required=True) 
    password = serializers.CharField(write_only=True, required=True)  
    username = serializers.CharField(write_only=True, required=True)
    civil_status_id = serializers.IntegerField(write_only=True, required=True)
    educational_attainment_id = serializers.IntegerField(write_only=True, required=True)

    
    
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
            'status_id', 'id_image', 'password', 'username', 'civil_status_id', 'educational_attainment_id'
        ]

    def create(self, validated_data):
        
        data = self.context['request'].data
         
        plain_password = validated_data.get('password', '')
        password_hashed = hashlib.sha256(plain_password.encode()).hexdigest()
        
        id_image_file = validated_data.get('id_image')
        if id_image_file:
            image_base64 = base64.b64encode(id_image_file.read()).decode('utf-8')
        else:
            image_base64 = None

        params = [
            validated_data.get('last_name'),
            validated_data.get('first_name'),
            validated_data.get('dob'),
            validated_data.get('sex'),
            validated_data.get('barangay'),
            validated_data.get('city_municipality'),
            validated_data.get('status_id'),
            validated_data.get('username'),
            password_hashed,  # This is fine, as you compute it above
            validated_data.get('doc_type', 'ID'),  # If this is not in validated_data, get from data/context
            image_base64,  # <-- This is the base64 string of the image
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
            validated_data.get('req_pass_change', False),
            data.get('document_type', None),  # If this is not in validated_data, get from data/context
            validated_data.get('document_number'),
            validated_data.get('uploaded_by', None),
        ]

        print("Username:", validated_data.get('username'))
        print("Password (plain):", validated_data.get('password'))
        print("Password (hashed):", password_hashed)
        print("PARAMS SENT TO DB:", params)
    
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


# class ResidentIdDocumentSerializer(serializers.ModelSerializer):
#     document_image = serializers.ImageField(write_only=True)
#     resident = serializers.PrimaryKeyRelatedField(queryset=Resident.objects.all())  # required by default

#     class Meta:
#         model = ResidentIdDocument
#         fields = [
#             'id_doc_id', 'resident', 'document_type', 'document_number',
#             'document_image', 'date_uploaded', 'uploaded_by', 'verified', 'verification_date'
#         ]

#     def create(self, validated_data):
#         image = validated_data.pop('document_image')
#         image_bytes = image.read()
#         instance = ResidentIdDocument.objects.create(image_data=image_bytes, **validated_data)
#         return instance

class ResidentSerializer(serializers.ModelSerializer):

    religion = ReligionSerializer(read_only=True)
    address = AddressSerializer(read_only=True)
    civil_status = CivilStatusSerializer(read_only=True)
    educational_attainment = EducationalAttainmentSerializer(read_only=True)
    status = ResidentStatusSerializer(read_only=True)
    
    class Meta:
        model = Resident
        fields = '__all__'