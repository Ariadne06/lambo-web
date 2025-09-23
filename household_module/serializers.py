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