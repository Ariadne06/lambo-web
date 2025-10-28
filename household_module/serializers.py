from rest_framework import serializers
from .models import MedicalHistoryType, Class, FPMethod, FPStatus, HouseOwnershipType, HouseType, HouseholdType, NutritionStatus, PhilhealthCategory, RelationshipToHouseholdHead, WaterSourceType, ToiletFacilityType, WasteManagementType, Household, Family
from resident_profiling_module.models import Resident, Address, Quarter
from .services.household_service import HouseholdService
from .utils.database_helpers import insert_family_member, save_general_health_for_member

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
