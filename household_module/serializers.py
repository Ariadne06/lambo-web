from rest_framework import serializers
from .models import Relationship, MedicalHistoryType, Class, FPMethod, FPStatus, HouseOwnershipType, HouseType, HouseholdType, NutritionStatus, PhilhealthCategory, RelationshipToHouseholdHead, WaterSourceType, ToiletFacilityType, WasteManagementType, Household, Family, FeedingMethod, Month, TTStatus, VaccineType, DoseType, Supplements, ChildHealthRecord, DiseaseType, Trimester, TestType, SupplementType, DewormingType, OutcomeType, DeliveryType, PlaceDeliveryType, OwnershipType, BirthAttendant, RecordStatus 
from resident_profiling_module.models import Resident, Address, Quarter
from .services.household_service import HouseholdService
from .utils.database_helpers import insert_family_member, save_general_health_for_member, insert_child_health_record, update_child_health_record, add_child_immunization, add_child_supplement, add_child_medical_condition, add_child_surgical_history, add_child_growth_monitoring, add_exclusive_breastfeed_backfill, add_obstetrical_history, add_maternal_medical_condition, add_maternal_surgical_history
from django.db import connection

class HouseOwnershipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseOwnershipType
        fields = ['house_ownership_id', 'description']

class HouseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseType
        fields = ['house_type_id', 'description']

class HouseholdTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseholdType
        fields = ['household_type_id', 'description']

class WaterSourceTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WaterSourceType
        fields = ['water_source_type_id', 'level', 'description']

class ToiletFacilityTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ToiletFacilityType
        fields = ['toilet_facility_type_id', 'code', 'description']

class WasteManagementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WasteManagementType
        fields = ['waste_management_type_id', 'code', 'description']

class RelationshipToHouseholdHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelationshipToHouseholdHead
        fields = ['rth_id', 'description']

class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ['house_number', 'street', 'barangay', 'sitio', 'city_municipality', 'country']

class PhilhealthCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = PhilhealthCategory
        fields = ['philhealth_category_id', 'code', 'description']

class NutritionStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = NutritionStatus
        fields = ['nutrition_status_id', 'description']


class MedicalHistoryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicalHistoryType
        fields = ['medical_history_type_id', 'description']

class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = ['class_id', 'class_description']

class FPMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FPMethod
        fields = ['fp_method_id', 'code', 'description']

class FPStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = FPStatus
        fields = ['fp_status_id', 'code', 'description']

class QuarterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quarter
        fields = ['quarter_id', 'quarter_number', 'quarter_name', 'year', 'start_date', 'end_date']

class RelationshipSerializer(serializers.ModelSerializer):
    class Meta:
        model = Relationship
        fields = ['relationship_id', 'relationship_name']

class FeedingMethodSerializer(serializers.ModelSerializer):
    class Meta:
        model = FeedingMethod
        fields = ['feeding_method_id', 'method_name', 'is_active']


class MonthSerializer(serializers.ModelSerializer):
    class Meta:
        model = Month
        fields = ['month_id', 'month_sequence_name', 'month_number']


class TTStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TTStatus
        fields = ['tt_status_id', 'tt_code', 'tt_name']


class VaccineTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = VaccineType
        fields = [
            'vaccine_type_id', 'vaccine_name', 'at_birth', 
            'first_dose', 'second_dose', 'third_dose',
            'interval_between_doses', 'date_added', 'updated_at'
        ]


class DoseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DoseType
        fields = ['dose_type_id', 'dose_name']


class SupplementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Supplements
        fields = ['supplement_id', 'supplement_name', 'is_active']

class DiseaseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DiseaseType
        fields = '__all__'


class TrimesterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trimester
        fields = '__all__'


class TestTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = TestType
        fields = '__all__'


class SupplementTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupplementType
        fields = '__all__'


class DewormingTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DewormingType
        fields = '__all__'


class OutcomeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutcomeType
        fields = '__all__'


class DeliveryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeliveryType
        fields = '__all__'


class PlaceDeliveryTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceDeliveryType
        fields = '__all__'


class OwnershipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OwnershipType
        fields = '__all__'


class BirthAttendantSerializer(serializers.ModelSerializer):
    class Meta:
        model = BirthAttendant
        fields = '__all__'


class RecordStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = RecordStatus
        fields = '__all__'



class FamilyCreateSerializer(serializers.ModelSerializer):

    household_type_id = serializers.IntegerField(write_only=True, required=True)
    family_head_id = serializers.IntegerField(write_only=True, required=True) 
    respondent_id = serializers.IntegerField(write_only=True, required=True)
    respondent_relationship_to_fh_id = serializers.IntegerField(write_only=True, required=False, default=1)
    head_rth_id = serializers.IntegerField(write_only=True, required=True)
    respondent_rth_id = serializers.IntegerField(write_only=True, required=True) 
    ip_status = serializers.BooleanField(write_only=True, required=False, default=False)
    ip_tribe = serializers.CharField(write_only=True, required=False, allow_blank=True)
    nhts_status = serializers.BooleanField(write_only=True, required=False, default=False)
    water_source_type_id = serializers.IntegerField(write_only=True, required=True)
    toilet_facility_type_id = serializers.IntegerField(write_only=True, required=True)
    waste_management_type_id = serializers.IntegerField(write_only=True, required=True)

    
    class Meta:
        model = Family
        fields = [
            'family_code', 'is_visited', 'quarter', 'year', 'created_at',
            'household_type_id', 'family_head_id', 'respondent_id', 
            'respondent_relationship_to_fh_id', 'head_rth_id', 'respondent_rth_id', 'ip_status', 'ip_tribe', 'nhts_status',
            'water_source_type_id', 'toilet_facility_type_id', 'waste_management_type_id',
        ]
        read_only_fields = ['family_code', 'is_visited', 'quarter', 'year', 'created_at']
    
    def validate(self, data):
        """Validation - following your pattern"""
        # Ensure family_head_id is provided
        if not data.get('family_head_id'):
            raise serializers.ValidationError({'family_head_id': 'Family head is required.'})
        
        if not data.get('head_rth_id'):
            raise serializers.ValidationError({'head_rth_id': 'Family head relationship to household head is required.'})

        if data.get('family_head_id') == data.get('respondent_id'):
            # Same person - relationships must match
            head_rth = data.get('head_rth_id')
            respondent_rth = data.get('respondent_rth_id')
            
            if respondent_rth and head_rth != respondent_rth:
                raise serializers.ValidationError({
                    'respondent_rth_id': f'When family head and respondent are the same person, they must have the same relationship to household head. Expected: {head_rth}, Got: {respondent_rth}'
                })
            
            #  respondent_rth_id to match head_rth_id
            if not respondent_rth:
                data['respondent_rth_id'] = head_rth
        
        #  Validate respondent_rth_id when respondent ≠ family head
        elif data.get('respondent_id') and data.get('respondent_id') != data.get('family_head_id'):
            if not data.get('respondent_rth_id'):
                raise serializers.ValidationError({
                    'respondent_rth_id': 'Respondent relationship to household head is required when respondent is different from family head.'
                })
        
        
        return data
    
    def create(self, validated_data):
        """Create family using service"""
        try:
            request = self.context.get('request')
            household_id = self.context.get('household_id')
            
            if not household_id:
                raise serializers.ValidationError("Household ID is required")
            
            personnel_id = request.data.get('personnel_id')
            
            if not personnel_id:
                raise serializers.ValidationError("Personnel ID is required")
            
            print(f"Creating family for household: {household_id} by personnel: {personnel_id}")
            
            family_id = HouseholdService.create_new_family(household_id, validated_data, personnel_id)
            
            if not family_id:
                raise serializers.ValidationError("Failed to create family")
            
            # Return a mock family object for response
            family = Family()
            family.family_id = family_id
            family.household_id = household_id
            
            print(f"Family created successfully with ID: {family_id}")
            return family
            
        except Exception as e:
            print(f"Family creation failed: {str(e)}")
            raise serializers.ValidationError(f"Family creation failed: {str(e)}")


# class RelationshipListSerializer(serializers.Serializer):
#     # This wraps the list returned by your static method
#     results = RelationshipToHouseholdHeadSerializer(many=True, read_only=True)

#     @staticmethod
#     def get_results():
#         return Household.sp_get_relationship_to_household_head()

#     def to_representation(self, instance):
#         # instance is ignored; we pull directly from the DB
#         return {"results": self.get_results()}
    
class HouseholdInsertSerializer(serializers.Serializer):
    house_ownership_id = serializers.IntegerField(required=True)
    house_type_id = serializers.IntegerField(required=True)
    barangay = serializers.CharField(required=True)
    city_municipality = serializers.CharField(required=True)
    sitio_id = serializers.IntegerField(required=True)
    personnel_id = serializers.IntegerField(required=True)
    house_number = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    street = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    country = serializers.CharField(required=False, default='Philippines')
    household_head_id = serializers.IntegerField(required=False, allow_null=True)
    respondent_id = serializers.IntegerField(required=False, allow_null=True)
    respondent_rth_id = serializers.IntegerField(required=False, allow_null=True)
    performed_by_id = serializers.IntegerField(required=False, allow_null=True)
    performed_by_type = serializers.CharField(required=False, default='personnel')
    enforce_bhw_assignment = serializers.BooleanField(required=False, default=False)

    def create(self, validated_data):
        # Call the service to execute the SQL function
        household_id = HouseholdService.insert_household(validated_data)
        return {'household_id': household_id}
    
class FamilyMemberCreateSerializer(serializers.Serializer):
    resident_id = serializers.IntegerField(required=True)
    rth_id = serializers.IntegerField(required=True)
    rtf_id = serializers.IntegerField(required=True)
    philhealthid_number = serializers.CharField(required=False, allow_blank=True, default='')
    membership_type = serializers.CharField(required=False, allow_blank=True, default='M')
    philhealth_category_id = serializers.IntegerField(required=False, allow_null=True)
    nutrition_status_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, data):
        if not data.get('resident_id'):
            raise serializers.ValidationError({'resident_id': 'Resident is required'})
        if not data.get('rth_id'):
            raise serializers.ValidationError({'rth_id': 'Relationship to household head is required'})
        if not data.get('rtf_id'):
            raise serializers.ValidationError({'rtf_id': 'Relationship to family head is required'})
        return data
    
    def create(self, validated_data):
        try:
            family_id = self.context.get('family_id')
            personnel_id = self.context.get('personnel_id')
            
            if not family_id or not personnel_id:
                raise serializers.ValidationError("Missing family_id or personnel_id")
            
           
            member_id = insert_family_member(
                family_id=family_id,
                resident_id=validated_data['resident_id'],
                rth_id=validated_data['rth_id'],
                rtf_id=validated_data['rtf_id'],
                philhealthid_number=validated_data.get('philhealthid_number', ''),
                membership_type=validated_data.get('membership_type', 'M'),
                philhealth_category_id=validated_data.get('philhealth_category_id'),
                nutrition_status_id=validated_data.get('nutrition_status_id'),
                personnel_id=personnel_id
            )
            
            return {'family_member_id': member_id}
                
        except Exception as e:
            raise serializers.ValidationError(f"Failed to add family member: {str(e)}")
        

class GeneralHealthCreateSerializer(serializers.Serializer):
    """Serializer for creating General Health records"""
    
    # Common fields
    class_id = serializers.IntegerField(required=True)
    medical_history_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False, 
        allow_empty=True,  
        allow_null=True 
    )
    
    # Female-only fields
    wra_lmp = serializers.DateField(required=False, allow_null=True)
    fp_method_yn = serializers.BooleanField(required=False, allow_null=True)
    fp_method_id = serializers.IntegerField(required=False, allow_null=True)
    fp_status_id = serializers.IntegerField(required=False, allow_null=True)
    age_of_menarche = serializers.IntegerField(required=False, allow_null=True)  

    smoker = serializers.BooleanField(required=True)
    alcohol_drinker = serializers.BooleanField(required=True)
    sexually_active = serializers.BooleanField(required=True)
    
    def validate(self, data):
        """Validate create data"""
        if not data.get('class_id'):
            raise serializers.ValidationError({'class_id': 'Class/Population Group is required'})
        
        if data.get('smoker') is None:
            raise serializers.ValidationError({'smoker': 'Smoker status is required'})
        if data.get('alcohol_drinker') is None:
            raise serializers.ValidationError({'alcohol_drinker': 'Alcohol drinker status is required'})
        if data.get('sexually_active') is None:
            raise serializers.ValidationError({'sexually_active': 'Sexually active status is required'})
            
        if data.get('medical_history_ids') is None:
            data['medical_history_ids'] = [] 
        
        # FP validation (only if fp_method_yn is True)
        if data.get('fp_method_yn') is True:
            if not data.get('fp_method_id'):
                raise serializers.ValidationError({'fp_method_id': 'FP Method is required when using family planning'})
            if not data.get('fp_status_id'):
                raise serializers.ValidationError({'fp_status_id': 'FP Status is required when using family planning'})
        
        if data.get('age_of_menarche') is not None:
            age_val = data.get('age_of_menarche')
            if age_val < 8 or age_val > 25:
                raise serializers.ValidationError({'age_of_menarche': 'Age of menarche must be between 8 and 25 years'})

        return data
    
    def create(self, validated_data):
        """Create general health record"""
        try:
            family_member_id = self.context.get('family_member_id')
            personnel_id = self.context.get('personnel_id')
            
            if not family_member_id:
                raise serializers.ValidationError("Missing family_member_id")
            if not personnel_id:
                raise serializers.ValidationError("Missing personnel_id")
            
            #  FIX: Handle empty medical history
            medical_history_ids = validated_data.get('medical_history_ids')
            if not medical_history_ids or len(medical_history_ids) == 0:
                medical_history_ids = None  
            
            gh_id = save_general_health_for_member(
                family_member_id=family_member_id,
                class_id=validated_data['class_id'],
                medical_history_ids=medical_history_ids,  
                wra_lmp=validated_data.get('wra_lmp'),
                fp_method_yn=validated_data.get('fp_method_yn'),
                fp_method_id=validated_data.get('fp_method_id'),
                fp_status_id=validated_data.get('fp_status_id'),
                smoker=validated_data.get('smoker'),
                alcohol_drinker=validated_data.get('alcohol_drinker'),
                sexually_active=validated_data.get('sexually_active'),
                age_of_menarche=validated_data.get('age_of_menarche'),  
                personnel_id=personnel_id
            )
            
            return {'gh_id': gh_id}
                
        except Exception as e:
            raise serializers.ValidationError(f"Failed to save general health: {str(e)}")
        

class GeneralHealthUpdateSerializer(serializers.Serializer):
    """Serializer for updating General Health records"""
    
    # Class (optional - only update if provided)
    class_id = serializers.IntegerField(required=False, allow_null=True)
    
    # Medical History (optional - only update if apply_med_hist=True)
    apply_med_hist = serializers.BooleanField(default=False)
    medical_history_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_null=True,
        allow_empty=True
    )
    
    # Family Planning (optional - only update if apply_fp=True)
    apply_fp = serializers.BooleanField(default=False)
    wra_lmp = serializers.DateField(required=False, allow_null=True)
    fp_method_yn = serializers.BooleanField(required=False, allow_null=True)
    fp_method_id = serializers.IntegerField(required=False, allow_null=True)
    fp_status_id = serializers.IntegerField(required=False, allow_null=True)
    apply_lifestyle = serializers.BooleanField(default=False)
    smoker = serializers.BooleanField(required=False, allow_null=True)
    alcohol_drinker = serializers.BooleanField(required=False, allow_null=True)
    sexually_active = serializers.BooleanField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validate update data"""
        
        # If updating medical history, validate it's applied
        if data.get('medical_history_ids') is not None and not data.get('apply_med_hist'):
            raise serializers.ValidationError({
                'apply_med_hist': 'Must be True when updating medical history'
            })
        
        # If updating FP, validate required fields
        if data.get('apply_fp'):
            if data.get('fp_method_yn') is True:
                if not data.get('fp_method_id') or not data.get('fp_status_id'):
                    raise serializers.ValidationError({
                        'fp_method_id': 'Required when fp_method_yn is True',
                        'fp_status_id': 'Required when fp_method_yn is True'
                    })
        
        if data.get('apply_lifestyle'):
            lifestyle_fields = ['smoker', 'alcohol_drinker', 'sexually_active']
            if not any(data.get(field) is not None for field in lifestyle_fields):
                raise serializers.ValidationError({
                    'apply_lifestyle': 'At least one lifestyle field must be provided when apply_lifestyle is True'
                })
        
        
        if data.get('age_of_menarche') is not None:
            age_val = data.get('age_of_menarche')
            if age_val < 8 or age_val > 25:
                raise serializers.ValidationError({'age_of_menarche': 'Age of menarche must be between 8 and 25 years'})
        
        return data
    
    def update(self, instance, validated_data):
        """Update General Health record"""
        try:
            family_member_id = self.context.get('family_member_id')
            personnel_id = self.context.get('personnel_id')
            
            if not family_member_id:
                raise serializers.ValidationError("Missing family_member_id")
            if not personnel_id:
                raise serializers.ValidationError("Missing personnel_id")
            
            from .utils.database_helpers import update_general_health_for_member
            
            gh_id = update_general_health_for_member(
                family_member_id=family_member_id,
                class_id=validated_data.get('class_id'),
                apply_med_hist=validated_data.get('apply_med_hist', False),
                medical_history_ids=validated_data.get('medical_history_ids'),
                apply_fp=validated_data.get('apply_fp', False),
                wra_lmp=validated_data.get('wra_lmp'),
                fp_method_yn=validated_data.get('fp_method_yn'),
                fp_method_id=validated_data.get('fp_method_id'),
                fp_status_id=validated_data.get('fp_status_id'),
                apply_lifestyle=validated_data.get('apply_lifestyle', False),
                smoker=validated_data.get('smoker'),
                alcohol_drinker=validated_data.get('alcohol_drinker'),
                sexually_active=validated_data.get('sexually_active'),
                age_of_menarche=validated_data.get('age_of_menarche'),  
                personnel_id=personnel_id
            )
            
            return {'gh_id': gh_id}
                
        except Exception as e:
            raise serializers.ValidationError(f"Failed to update general health: {str(e)}")
    
class HouseholdUpdateSerializer(serializers.Serializer):
    """Serializer for updating household information"""
    
    # Required fields
    house_ownership_id = serializers.IntegerField(required=True)
    house_type_id = serializers.IntegerField(required=True)
    barangay = serializers.CharField(required=True, max_length=200)
    city_municipality = serializers.CharField(required=True, max_length=100)
    sitio_id = serializers.IntegerField(required=True)
    personnel_id = serializers.IntegerField(required=True)
    
    # Optional fields
    house_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    street = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=200)
    country = serializers.CharField(required=False, default='Philippines', max_length=100)
    household_head_id = serializers.IntegerField(required=False, allow_null=True)
    respondent_id = serializers.IntegerField(required=False, allow_null=True)
    respondent_rth_id = serializers.IntegerField(required=False, allow_null=True)
    performed_by_id = serializers.IntegerField(required=False, allow_null=True)
    performed_by_type = serializers.CharField(required=False, default='personnel', max_length=20)
    enforce_bhw_assignment = serializers.BooleanField(required=False, default=False)
    
    def validate(self, data):
        """Validate the update data"""
        
        # Basic required field validation
        if not data.get('house_ownership_id'):
            raise serializers.ValidationError({'house_ownership_id': 'House ownership type is required.'})
        
        if not data.get('house_type_id'):
            raise serializers.ValidationError({'house_type_id': 'House type is required.'})
        
        if not data.get('sitio_id'):
            raise serializers.ValidationError({'sitio_id': 'Sitio/Purok is required.'})
        
        if not data.get('personnel_id'):
            raise serializers.ValidationError({'personnel_id': 'Personnel ID is required.'})
        
        # Barangay and city validation
        barangay = data.get('barangay', '').strip()
        if not barangay:
            raise serializers.ValidationError({'barangay': 'Barangay is required.'})
        
        city = data.get('city_municipality', '').strip()
        if not city:
            raise serializers.ValidationError({'city_municipality': 'City/Municipality is required.'})
        
        # Respondent validation
        respondent_id = data.get('respondent_id')
        respondent_rth_id = data.get('respondent_rth_id')
        
        if respondent_id and not respondent_rth_id:
            raise serializers.ValidationError({
                'respondent_rth_id': 'Respondent relationship to household head is required when respondent is provided.'
            })
        
        return data
    

class ChildHealthRecordCreateSerializer(serializers.Serializer):
    """Create child health record"""
    child_id = serializers.IntegerField(required=True)
    time_of_birth = serializers.TimeField(required=False, allow_null=True)
    birth_weight_kg = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    birth_length_cm = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    place_of_delivery = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    address_landmark = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    tt_status_of_mother = serializers.IntegerField(required=False, allow_null=True)
    tt_status_date = serializers.DateField(required=False, allow_null=True)
    newborn_screening_status = serializers.BooleanField(required=False, allow_null=True)
    newborn_screening_status_date = serializers.DateField(required=False, allow_null=True)
    feeding_method_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, data):
        if not data.get('child_id'):
            raise serializers.ValidationError({'child_id': 'Child ID is required'})
        
        if data.get('newborn_screening_status') is True and not data.get('newborn_screening_status_date'):
            raise serializers.ValidationError({
                'newborn_screening_status_date': 'Date required when screening status is TRUE'
            })
        
        return data
    
    def create(self, validated_data):
        try:
            personnel_id = self.context.get('personnel_id')
            if not personnel_id:
                raise serializers.ValidationError({'personnel_id': 'Personnel ID is required'})
            
            validated_data['personnel_id'] = personnel_id
            child_health_id = insert_child_health_record(validated_data)
            
            if not child_health_id:
                raise serializers.ValidationError('Failed to create child health record')
            
            return {'child_health_id': child_health_id}
        except Exception as e:
            raise serializers.ValidationError(f"Failed to create record: {str(e)}")


class ChildHealthRecordUpdateSerializer(serializers.Serializer):
    """Update child health record - only non-sensitive fields"""
    place_of_delivery = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    address_landmark = serializers.CharField(max_length=200, required=False, allow_blank=True, allow_null=True)
    tt_status_of_mother = serializers.IntegerField(required=False, allow_null=True)
    tt_status_date = serializers.DateField(required=False, allow_null=True)
    newborn_screening_status = serializers.BooleanField(required=False, allow_null=True)
    newborn_screening_status_date = serializers.DateField(required=False, allow_null=True)
    feeding_method_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, data):
        # Validate screening date if status is True
        if data.get('newborn_screening_status') is True:
            if not data.get('newborn_screening_status_date'):
                raise serializers.ValidationError(
                    "Newborn screening date is required when status is True"
                )
        
        return data
    
    def update(self, instance, validated_data):
        """Update child health record"""
        try:
            # Get personnel_id from context
            personnel_id = self.context.get('personnel_id')
            if not personnel_id:
                raise serializers.ValidationError("Personnel ID is required")
            
            # Call database helper
            from .utils.database_helpers import update_child_health_record
            
            update_child_health_record(
                child_health_id=instance,  # instance is the child_health_id
                data={**validated_data, 'personnel_id': personnel_id}
            )
            
            return instance
            
        except Exception as e:
            raise serializers.ValidationError(str(e))


class ChildGrowthMonitoringCreateSerializer(serializers.Serializer):
    """Serializer for creating child growth monitoring records"""
    
    # Required fields
    weight_kg = serializers.DecimalField(max_digits=5, decimal_places=2, required=True)
    height_cm = serializers.DecimalField(max_digits=5, decimal_places=2, required=True)
    
    # ✅ CHANGED: These are now REQUIRED (per your SQL function)
    temp_c = serializers.DecimalField(max_digits=4, decimal_places=1, required=True)
    resp_rate = serializers.IntegerField(required=True)
    pulse_rate = serializers.IntegerField(required=True)
    
    # Optional notes
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    
    def validate_weight_kg(self, value):
        """Validate weight is reasonable"""
        if value <= 0:
            raise serializers.ValidationError("Weight must be greater than 0")
        if value > 150:
            raise serializers.ValidationError("Weight seems unusually high. Please verify.")
        return value
    
    def validate_height_cm(self, value):
        """Validate height is reasonable"""
        if value <= 0:
            raise serializers.ValidationError("Height must be greater than 0")
        if value > 220:
            raise serializers.ValidationError("Height seems unusually high. Please verify.")
        return value
    
    def validate_temp_c(self, value):
        """Validate temperature"""
        if value < 30 or value > 45:
            raise serializers.ValidationError("Temperature must be between 30°C and 45°C")
        return value
    
    def validate_resp_rate(self, value):
        """Validate respiratory rate"""
        if value < 10 or value > 100:
            raise serializers.ValidationError("Respiratory rate must be between 10 and 100 bpm")
        return value
    
    def validate_pulse_rate(self, value):
        """Validate pulse rate"""
        if value < 40 or value > 200:
            raise serializers.ValidationError("Pulse rate must be between 40 and 200 bpm")
        return value
    
    def create(self, validated_data):
        """Create growth monitoring record"""
        try:
            child_health_id = self.context.get('child_health_id')
            personnel_id = self.context.get('personnel_id')
            
            if not child_health_id:
                raise serializers.ValidationError("Missing child_health_id")
            if not personnel_id:
                raise serializers.ValidationError("Missing personnel_id")
            
            # ✅ Call database helper WITHOUT age_in_months
            cgm_id = add_child_growth_monitoring(
                child_health_id=child_health_id,
                personnel_id=personnel_id,
                weight_kg=validated_data['weight_kg'],
                height_cm=validated_data['height_cm'],
                temp_c=validated_data['temp_c'],
                resp_rate=validated_data['resp_rate'],
                pulse_rate=validated_data['pulse_rate'],
                notes=validated_data.get('notes')
            )
            
            if not cgm_id:
                raise serializers.ValidationError("Failed to create growth monitoring record")
            
            return {'cgm_id': cgm_id}
            
        except Exception as e:
            raise serializers.ValidationError(f"Failed to add growth record: {str(e)}")
        
class ChildImmunizationCreateSerializer(serializers.Serializer):
    vaccine_type_id = serializers.IntegerField(required=True)
    dose_type_id = serializers.IntegerField(required=True)
    date_given = serializers.DateField(required=True)   # <-- ADD THIS

    def create(self, validated_data):
        child_health_id = self.context.get("child_health_id")
        personnel_id = self.context.get("personnel_id")

        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT add_immunization(%s, %s, %s, %s, %s);",
                [
                    child_health_id,
                    validated_data["vaccine_type_id"],
                    validated_data["dose_type_id"],
                    validated_data["date_given"],
                    personnel_id,
                ],
            )
            row = cursor.fetchone()

        return row[0] if row else None



class ChildSupplementCreateSerializer(serializers.Serializer):
    """Add supplement record"""
    personnel_id = serializers.IntegerField(required=True)
    supplement_id = serializers.IntegerField(required=True)
    age_in_months = serializers.IntegerField(required=True, min_value=0)
    
    def validate_age_in_months(self, value):
        """Ensure age is valid"""
        if value < 0:
            raise serializers.ValidationError("Age in months cannot be negative")
        if value > 60:  # 5 years
            raise serializers.ValidationError("Age exceeds program limits (>60 months)")
        return value
    
    def create(self, validated_data):
        """Call database helper to add supplement"""
        child_health_id = self.context.get('child_health_id')
        
        child_health_id_returned = add_child_supplement(
            child_health_id=child_health_id,
            supplement_id=validated_data['supplement_id'],
            age_in_months=validated_data['age_in_months'],
            personnel_id=validated_data['personnel_id']
        )
        
        return child_health_id_returned




class ChildBreastfeedTrackingCreateSerializer(serializers.Serializer):
    """Serializer for creating/updating breastfeed tracking records"""
    
    month_id = serializers.IntegerField(required=True)
    feeding_method_id = serializers.IntegerField(required=True)
    date_assessed = serializers.DateField(required=True)
    notes = serializers.CharField(max_length=500, required=False, allow_blank=True, allow_null=True)
    
    def validate_month_id(self, value):
        """Validate month_id is 1-6 (for exclusive breastfeeding tracking)"""
        if value < 1 or value > 6:
            raise serializers.ValidationError("Month must be between 1 and 6")
        return value
    
    def validate_date_assessed(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Date cannot be in the future")
        return value
    
    def create(self, validated_data):
        try:
            child_health_id = self.context.get('child_health_id')
            personnel_id = self.context.get('personnel_id')
            
            if not child_health_id or not personnel_id:
                raise serializers.ValidationError("Missing child_health_id or personnel_id")
            
            tracking_id = add_exclusive_breastfeed_backfill(
                child_health_id=child_health_id,
                month_id=validated_data['month_id'],
                feeding_method_id=validated_data['feeding_method_id'],
                date_assessed=validated_data['date_assessed'],
                notes=validated_data.get('notes'),
                personnel_id=personnel_id
            )
            
            return {'tracking_id': tracking_id}
            
        except Exception as e:
            raise serializers.ValidationError(f"Failed to add breastfeed tracking: {str(e)}")


class ChildMedicalConditionCreateSerializer(serializers.Serializer):
    """Add medical condition for child"""
    personnel_id = serializers.IntegerField(required=True)
    medical_condition = serializers.CharField(max_length=200, required=True)
    
    def validate_medical_condition(self, value):
        """Validate and normalize medical condition name"""
        trimmed = value.strip()
        if len(trimmed) < 2:
            raise serializers.ValidationError("Medical condition must be at least 2 characters")
        return trimmed
    
    def create(self, validated_data):
        """Call database helper to add medical condition"""
        child_health_id = self.context.get('child_health_id')
        
        rmh_id = add_child_medical_condition(
            child_health_id=child_health_id,
            medical_condition=validated_data['medical_condition'],
            personnel_id=validated_data['personnel_id']
        )
        
        return rmh_id


class ChildSurgicalHistoryCreateSerializer(serializers.Serializer):
    """Add surgical history for child"""
    personnel_id = serializers.IntegerField(required=True)
    surgical_history_name = serializers.CharField(max_length=200, required=True)
    date_of_surgery = serializers.DateField(required=True)
    
    def validate_surgical_history_name(self, value):
        """Validate and normalize surgical procedure name"""
        trimmed = value.strip()
        if len(trimmed) < 2:
            raise serializers.ValidationError("Surgical procedure name must be at least 2 characters")
        return trimmed
    
    def validate_date_of_surgery(self, value):
        """Ensure surgery date is not in the future"""
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Surgery date cannot be in the future")
        return value
    
    def create(self, validated_data):
        """Call database helper to add surgical history"""
        child_health_id = self.context.get('child_health_id')
        
        rsh_id = add_child_surgical_history(
            child_health_id=child_health_id,
            surgical_history_name=validated_data['surgical_history_name'],
            date_of_surgery=validated_data['date_of_surgery'],
            personnel_id=validated_data['personnel_id']
        )
        
        return rsh_id


class ExclusiveBreastfeedCreateSerializer(serializers.Serializer):
    """Add exclusive breastfeed assessment"""
    personnel_id = serializers.IntegerField(required=True)
    month_id = serializers.IntegerField(required=True)
    
    def validate_month_id(self, value):
        """Ensure month_id is valid (1-6)"""
        if value < 1 or value > 6:
            raise serializers.ValidationError("Month must be between 1 and 6")
        return value
    
    def create(self, validated_data):
        """Call database helper to add exclusive breastfeed assessment"""
        child_health_id = self.context.get('child_health_id')
        
        results = add_exclusive_breastfeed_backfill(
            child_health_id=child_health_id,
            month_id=validated_data['month_id'],
            personnel_id=validated_data['personnel_id']
        )
        
        return results
    
# ========================================
#  MATERNAL ACTION SERIALIZERS (for creating records)
# ========================================

class MaternalHealthCreateSerializer(serializers.Serializer):
    maternal_id = serializers.IntegerField(required=True)
    address_landmark = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    personnel_id = serializers.IntegerField(required=True)
    
    def create(self, validated_data):
        from .utils.database_helpers import insert_maternal
        
        maternal_id = validated_data['maternal_id']
        address_landmark = validated_data.get('address_landmark')
        personnel_id = validated_data['personnel_id']
        
        result = insert_maternal(maternal_id, address_landmark, personnel_id)
        return result

class MaternalHealthUpdateSerializer(serializers.Serializer):
    address_landmark = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=500)
    personnel_id = serializers.IntegerField(required=True)
    
    def validate_address_landmark(self, value):
        """Validate address landmark length"""
        if value and len(value) > 500:
            raise serializers.ValidationError("Address landmark must be less than 500 characters")
        return value


class MaternalHealthStatusUpdateSerializer(serializers.Serializer):
    record_status_id = serializers.IntegerField(required=True)
    personnel_id = serializers.IntegerField(required=True)
    
    def validate_record_status_id(self, value):
        """Validate that status ID exists and is 'Completed'"""
        from .models import RecordStatus
        
        try:
            status = RecordStatus.objects.get(record_status_id=value)
            if status.record_name.lower() != 'completed':
                raise serializers.ValidationError("Only 'Completed' status is allowed")
            return value
        except RecordStatus.DoesNotExist:
            raise serializers.ValidationError("Invalid record status ID")

class ObstetricalHistoryCreateSerializer(serializers.Serializer):
    gravida = serializers.IntegerField(required=True, min_value=0)
    para = serializers.IntegerField(required=True, min_value=0)
    abortion = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    last_menstrual_period = serializers.DateField(required=True)
    expected_date_of_delivery = serializers.DateField(required=False, allow_null=True)
    personnel_id = serializers.IntegerField(required=True)
    
    def validate(self, data):
        # Ensure abortion is at least 0 if provided
        if data.get('abortion') is not None and data['abortion'] < 0:
            raise serializers.ValidationError({'abortion': 'Must be 0 or greater'})
        
        # Validate gravida >= para + abortion
        gravida = data.get('gravida', 0)
        para = data.get('para', 0)
        abortion = data.get('abortion', 0) or 0
        
        if gravida < (para + abortion):
            raise serializers.ValidationError({
                'gravida': f'Gravida ({gravida}) must be >= Para ({para}) + Abortion ({abortion})'
            })
        
        return data
    
    def create(self, validated_data):
        maternal_health_id = self.context.get('maternal_health_id')
        
        try:
            obs_id = add_obstetrical_history(maternal_health_id, validated_data)
            return {'obs_id': obs_id, **validated_data}
        except Exception as e:
            raise serializers.ValidationError(str(e))


class MaternalMedicalConditionCreateSerializer(serializers.Serializer):
    medical_condition = serializers.CharField(required=True, max_length=500)
    personnel_id = serializers.IntegerField(required=True)
    
    def validate_medical_condition(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Medical condition cannot be empty")
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Medical condition must be at least 3 characters")
        return value.strip()
    
    def create(self, validated_data):
        maternal_health_id = self.context.get('maternal_health_id')
        
        try:
            mmh_id = add_maternal_medical_condition(
                maternal_health_id,
                validated_data['medical_condition'],
                validated_data['personnel_id']
            )
            return {'mmh_id': mmh_id, **validated_data}
        except Exception as e:
            raise serializers.ValidationError(str(e))


class MaternalSurgicalHistoryCreateSerializer(serializers.Serializer):
    surgical_history_name = serializers.CharField(required=True, max_length=500)
    date_of_surgery = serializers.DateField(required=True)
    personnel_id = serializers.IntegerField(required=True)
    
    def validate_surgical_history_name(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("Surgical history name cannot be empty")
        if len(value.strip()) < 3:
            raise serializers.ValidationError("Surgical history name must be at least 3 characters")
        return value.strip()
    
    def validate_date_of_surgery(self, value):
        from datetime import date
        if value > date.today():
            raise serializers.ValidationError("Date of surgery cannot be in the future")
        return value
    
    def create(self, validated_data):
        maternal_health_id = self.context.get('maternal_health_id')
        
        try:
            data = {
                'surgical_history_name': validated_data['surgical_history_name'],
                'date_of_surgery': validated_data['date_of_surgery']
            }
            msh_id = add_maternal_surgical_history(
                maternal_health_id,
                data,
                validated_data['personnel_id']
            )
            return {'msh_id': msh_id, **validated_data}
        except Exception as e:
            raise serializers.ValidationError(str(e))


class MaternalImmunizationCreateSerializer(serializers.Serializer):
    dose_number = serializers.IntegerField(required=True, min_value=1, max_value=5)
    date_given = serializers.DateField(required=True)
    personnel_id = serializers.IntegerField(required=True)
    
    def validate_dose_number(self, value):
        if value not in [1, 2, 3, 4, 5]:
            raise serializers.ValidationError("Dose number must be between 1 and 5")
        return value
    
    def save(self, maternal_health_id):
        from .utils.database_helpers import add_maternal_immunization
        
        return add_maternal_immunization(
            maternal_health_id=maternal_health_id,
            dose_number=self.validated_data['dose_number'],
            date_given=self.validated_data['date_given'],
            personnel_id=self.validated_data['personnel_id']
        )


class DiseaseScreenCreateSerializer(serializers.Serializer):
    disease_type_id = serializers.IntegerField(required=True)
    screening_date = serializers.DateField(required=True)
    result = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    personnel_id = serializers.IntegerField(required=True)


class LabScreeningCreateSerializer(serializers.Serializer):
    test_type_id = serializers.IntegerField(required=True)
    test_date = serializers.DateField(required=True)
    result = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    iron_tablet_given_date = serializers.DateField(required=False, allow_null=True)
    iron_tablet_quantity = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    personnel_id = serializers.IntegerField(required=True)


class CheckupRecordCreateSerializer(serializers.Serializer):
    aog_weeks = serializers.IntegerField(required=True, min_value=0)
    weight_kg = serializers.DecimalField(required=True, max_digits=5, decimal_places=2, min_value=0)
    height_cm = serializers.DecimalField(required=True, max_digits=5, decimal_places=2, min_value=0)
    bmi = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    blood_pressure = serializers.CharField(required=False, allow_blank=True, max_length=20)
    fetal_heart_rate = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    laboratory_results = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    personnel_id = serializers.IntegerField(required=True)


class MaternalSupplementCreateSerializer(serializers.Serializer):
    supplement_type_id = serializers.IntegerField(required=True)
    date_given = serializers.DateField(required=True)
    number_of_tablets = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    personnel_id = serializers.IntegerField(required=True)


class DewormingCreateSerializer(serializers.Serializer):
    deworming_type_id = serializers.IntegerField(required=True)
    number_of_tablets = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    date_given = serializers.DateField(required=True)
    personnel_id = serializers.IntegerField(required=True)


class DeliveryOutcomeCreateSerializer(serializers.Serializer):
    outcome_type_id = serializers.IntegerField(required=True)
    delivery_type_id = serializers.IntegerField(required=True)
    place_delivery_type_id = serializers.IntegerField(required=True)
    ownership_type_id = serializers.IntegerField(required=False, allow_null=True)
    others_description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    birth_attendant_id = serializers.IntegerField(required=True)
    other_attendant = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    time_of_delivery = serializers.TimeField(required=False, allow_null=True)
    date_terminated = serializers.DateField(required=True)
    personnel_id = serializers.IntegerField(required=True)


class PostpartumVisitCreateSerializer(serializers.Serializer):
    date_of_visit = serializers.DateField(required=False, allow_null=True)
    weight_kg = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    height_cm = serializers.DecimalField(required=False, allow_null=True, max_digits=5, decimal_places=2)
    blood_pressure = serializers.CharField(required=False, allow_blank=True, max_length=20)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    laboratory_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    personnel_id = serializers.IntegerField(required=True)


# Child Vaccine Management
class VaccineTypeCreateSerializer(serializers.Serializer):
    vaccine_name = serializers.CharField(max_length=200, required=True)
    at_birth = serializers.BooleanField(default=False)
    first_dose = serializers.BooleanField(default=False)
    second_dose = serializers.BooleanField(default=False)
    third_dose = serializers.BooleanField(default=False)
    interval_between_doses = serializers.CharField(
        required=False, 
        allow_null=True,
        help_text="e.g., '4 weeks', '1 month'"
    )
    
    def validate(self, data):
        # At least one dose must be enabled
        if not any([
            data.get('at_birth'),
            data.get('first_dose'),
            data.get('second_dose'),
            data.get('third_dose')
        ]):
            raise serializers.ValidationError(
                "At least one dose type must be enabled"
            )
        
        # If multiple doses, interval is recommended
        dose_count = sum([
            data.get('first_dose', False),
            data.get('second_dose', False),
            data.get('third_dose', False)
        ])
        
        if dose_count >= 1 and not data.get('interval_between_doses'):
            raise serializers.ValidationError(
                "Interval between doses is recommended when multiple doses are enabled"
            )
        
        return data
    
    def save(self, personnel_id):
        from .utils.database_helpers import insert_vaccine
        return insert_vaccine(self.validated_data, personnel_id)


class VaccineTypeUpdateSerializer(serializers.Serializer):
    vaccine_name = serializers.CharField(max_length=200, required=False)
    at_birth = serializers.BooleanField(required=False)
    first_dose = serializers.BooleanField(required=False)
    second_dose = serializers.BooleanField(required=False)
    third_dose = serializers.BooleanField(required=False)
    interval_between_doses = serializers.CharField(
        required=False,
        allow_null=True
    )
    
    def save(self, vaccine_type_id, personnel_id):
        from .utils.database_helpers import update_vaccine
        return update_vaccine(vaccine_type_id, self.validated_data, personnel_id)