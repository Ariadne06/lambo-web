from rest_framework import serializers
from .models import HouseOwnershipType, HouseholdType, WaterSourceType, ToiletFacilityType, WasteManagementType, Household, Family
from resident_profiling_module.models import Resident, Address
from .services.household_service import HouseholdService

class HouseOwnershipTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = HouseOwnershipType
        fields = ['house_ownership_id', 'description']

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


class HouseholdCreateSerializer(serializers.ModelSerializer):
    # Write-only fields for creation
    house_ownership_type_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    house_number = serializers.CharField(write_only=True, required=False, allow_blank=True)
    address_id = serializers.IntegerField(write_only=True, required=True)
    household_head_id = serializers.IntegerField(write_only=True, required=True)
    respondent_id = serializers.IntegerField(write_only=True, required=True)
    respondent_relationship_to_hh_id = serializers.IntegerField(write_only=True, required=False, default=1)
    
    class Meta:
        model = Household
        fields = [
            'household_code', 'house_number', 'is_visited', 'quarter', 'year', 'created_at',
            'house_ownership_type_id', 'address_id', 'household_head_id', 'respondent_id', 
            'respondent_relationship_to_hh_id'
        ]
        read_only_fields = ['household_code', 'is_visited', 'quarter', 'year', 'created_at']
    
    def create(self, validated_data):
        """Create household using service - following your pattern"""
        try:

            request = self.context.get('request')
            personnel_id = request.user.personnel.personnel_id
            
            print(f"Creating household for personnel: {personnel_id}")
            
            household_id = HouseholdService.create_new_household(validated_data, personnel_id)
            
            if not household_id:
                raise serializers.ValidationError("Failed to create household")
            
            # Return a mock household object for response
            household = Household()
            household.household_id = household_id
            household.house_number = validated_data.get('house_number', '')
            
            print(f"Household created successfully with ID: {household_id}")
            return household
            
        except Exception as e:
            print(f"Household creation failed: {str(e)}")
            raise serializers.ValidationError(f"Household creation failed: {str(e)}")

class FamilyCreateSerializer(serializers.ModelSerializer):

    household_type_id = serializers.IntegerField(write_only=True, required=True)
    family_head_id = serializers.IntegerField(write_only=True, required=True)  # REQUIRED!
    respondent_id = serializers.IntegerField(write_only=True, required=True)
    respondent_relationship_to_fh_id = serializers.IntegerField(write_only=True, required=False, default=1)
    ip_status = serializers.BooleanField(write_only=True, required=False, default=False)
    ip_tribe = serializers.CharField(write_only=True, required=False, allow_blank=True)
    nhts_status = serializers.BooleanField(write_only=True, required=False, default=False)
    water_source_type_id = serializers.IntegerField(write_only=True, required=True)
    toilet_facility_type_id = serializers.IntegerField(write_only=True, required=True)
    waste_management_type_id = serializers.IntegerField(write_only=True, required=True)
    waste_other_text = serializers.CharField(write_only=True, required=False, allow_blank=True)
    
    class Meta:
        model = Family
        fields = [
            'family_code', 'is_visited', 'quarter', 'year', 'created_at',
            'household_type_id', 'family_head_id', 'respondent_id', 
            'respondent_relationship_to_fh_id', 'ip_status', 'ip_tribe', 'nhts_status',
            'water_source_type_id', 'toilet_facility_type_id', 'waste_management_type_id', 'waste_other_text'
        ]
        read_only_fields = ['family_code', 'is_visited', 'quarter', 'year', 'created_at']
    
    def validate(self, data):
        """Validation - following your pattern"""
        # Ensure family_head_id is provided
        if not data.get('family_head_id'):
            raise serializers.ValidationError({'family_head_id': 'Family head is required.'})
        return data
    
    def create(self, validated_data):
        """Create family using service - following your pattern"""
        try:
            request = self.context.get('request')
            personnel_id = request.user.personnel.personnel_id
            household_id = self.context.get('household_id')  # Pass this from view
            
            if not household_id:
                raise serializers.ValidationError("Household ID is required")
            
            print(f"Creating family for household: {household_id}")
            
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

# Simple response serializers
class HouseholdListSerializer(serializers.Serializer):
    """Simple serializer for household list responses"""
    household_id = serializers.IntegerField()
    household_code = serializers.CharField()
    house_number = serializers.CharField(allow_blank=True, allow_null=True)
    household_head_name = serializers.CharField()
    respondent_name = serializers.CharField()
    full_address = serializers.CharField()
    is_visited = serializers.BooleanField()
    family_count = serializers.IntegerField()
    visited_families = serializers.IntegerField()
    quarter = serializers.IntegerField()
    year = serializers.IntegerField()
    

class RelationshipToHouseholdHeadSerializer(serializers.Serializer):
    rth_id = serializers.IntegerField()
    description = serializers.CharField()

class RelationshipListSerializer(serializers.Serializer):
    # This wraps the list returned by your static method
    results = RelationshipToHouseholdHeadSerializer(many=True, read_only=True)

    @staticmethod
    def get_results():
        return Household.sp_get_relationship_to_household_head()

#     def to_representation(self, instance):
#         # instance is ignored; we pull directly from the DB
#         return {"results": self.get_results()}
    
class HouseholdInsertSerializer(serializers.Serializer):
    # Mirror the SP signature (types + nullability)
    house_ownership_id = serializers.IntegerField(required=False, allow_null=True)
    house_type_id = serializers.IntegerField(required=False, allow_null=True)
    barangay = serializers.CharField()
    city_municipality = serializers.CharField()
    sitio_id = serializers.IntegerField(required=False, allow_null=True)
    personnel_id = serializers.IntegerField()
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
    # Common fields
    class_id = serializers.IntegerField(required=True)
    medical_history_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        allow_empty=True
    )
    
    # Female-only fields
    wra_lmp = serializers.DateField(required=False, allow_null=True)
    fp_method_yn = serializers.BooleanField(required=False, allow_null=True)
    fp_method_id = serializers.IntegerField(required=False, allow_null=True)
    fp_status_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, data):
        if not data.get('class_id'):
            raise serializers.ValidationError({'class_id': 'Class/Population Group is required'})
        
        if data.get('fp_method_yn') is True:
            if not data.get('fp_method_id'):
                raise serializers.ValidationError({'fp_method_id': 'FP Method is required when using family planning'})
            if not data.get('fp_status_id'):
                raise serializers.ValidationError({'fp_status_id': 'FP Status is required when using family planning'})
        
        return data
    
    def create(self, validated_data):
        """Create general health record """
        try:
            family_member_id = self.context.get('family_member_id')
            personnel_id = self.context.get('personnel_id')
            
            if not family_member_id:
                raise serializers.ValidationError("Missing family_member_id")
            if not personnel_id:
                raise serializers.ValidationError("Missing personnel_id")
            
            gh_id = save_general_health_for_member(
                family_member_id=family_member_id,
                class_id=validated_data['class_id'],
                medical_history_ids=validated_data.get('medical_history_ids'),
                wra_lmp=validated_data.get('wra_lmp'),
                fp_method_yn=validated_data.get('fp_method_yn'),
                fp_method_id=validated_data.get('fp_method_id'),
                fp_status_id=validated_data.get('fp_status_id'),
                personnel_id=personnel_id
            )
            
            return {'gh_id': gh_id}
                
        except Exception as e:
            raise serializers.ValidationError(f"Failed to save general health: {str(e)}")
