from django.db import models, connection
from resident_profiling_module.models import Address



class HouseOwnershipType(models.Model):
    house_ownership_id = models.AutoField(primary_key=True)  
    description = models.TextField(blank=True, null=True)  
    
    class Meta:
        managed = False
        db_table = 'house_ownership'

class HouseType(models.Model):
    house_type_id = models.AutoField(primary_key=True)
    description = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = 'house_type'

class HouseholdType(models.Model):
    household_type_id = models.AutoField(primary_key=True)               
    description = models.TextField(blank=True, null=True) 
    
    class Meta:
        managed = False
        db_table = 'household_type'

class WaterSourceType(models.Model):
    water_source_type_id = models.AutoField(primary_key=True)    
    level = models.CharField(max_length=100)    
    description = models.TextField(blank=True, null=True)  
    
    class Meta:
        managed = False
        db_table = 'water_source_type'

class ToiletFacilityType(models.Model):
    toilet_facility_type_id = models.AutoField(primary_key=True) 
    code = models.CharField(max_length=5)   
    description = models.TextField(blank=True, null=True)    
    
    class Meta:
        managed = False
        db_table = 'toilet_facility_type'

class WasteManagementType(models.Model):
    waste_management_type_id = models.AutoField(primary_key=True) 
    code = models.CharField(max_length=5) 
    description = models.TextField(blank=True, null=True)   
    
    class Meta:
        managed = False
        db_table = 'waste_management_type'

class RelationshipToHouseholdHead(models.Model):
    rth_id = models.AutoField(primary_key=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'relationship_to_householdhead'

class FamilyMember(models.Model):
    family_member_id = models.AutoField(primary_key=True)
    family_member_code = models.CharField(max_length=20, unique=True)
    family_id = models.IntegerField()
    resident_id = models.IntegerField()
    rth_id = models.IntegerField()  
    rtf_id = models.IntegerField() 
    philhealthid_number = models.CharField(max_length=50, null=True, blank=True)
    membership_type = models.CharField(max_length=1, null=True, blank=True) 
    philhealth_category_id = models.IntegerField(null=True, blank=True)
    nutrition_status_id = models.IntegerField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    added_by = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'family_member'

class PhilhealthCategory(models.Model):
    philhealth_category_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=5)
    description = models.TextField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'philhealth_category'

class NutritionStatus(models.Model):
    nutrition_status_id = models.AutoField(primary_key=True)
    description = models.TextField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'nutrition_status'


class MedicalHistoryType(models.Model):
    medical_history_type_id = models.AutoField(primary_key=True)
    description = models.TextField()
    
    class Meta:
        managed = False
        db_table = 'medical_history_type'

class Class(models.Model):
    class_id = models.AutoField(primary_key=True)
    class_description = models.TextField()
    
    class Meta:
        managed = False
        db_table = 'class'

class FPMethod(models.Model):
    fp_method_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20)
    description = models.TextField()
    
    class Meta:
        managed = False
        db_table = 'fp_method'

class FPStatus(models.Model):
    fp_status_id = models.AutoField(primary_key=True)
    code = models.CharField(max_length=20)
    description = models.TextField()
    
    class Meta:
        managed = False
        db_table = 'fp_status'

class GeneralHealthMale(models.Model):
    ghtm_id = models.AutoField(primary_key=True)
    family_member_id = models.IntegerField()
    quarter_id = models.IntegerField()
    medical_history_ids = models.JSONField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    class_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'general_health_male'

class GeneralHealthFemale(models.Model):
    ghtf_id = models.AutoField(primary_key=True)
    family_member_id = models.IntegerField()
    quarter_id = models.IntegerField()
    medical_history_ids = models.JSONField(null=True, blank=True)
    last_menstrual_period = models.DateField(null=True, blank=True)
    fp_method_yn = models.BooleanField(null=True, blank=True)
    fp_method_id = models.IntegerField(null=True, blank=True)
    fp_status_id = models.IntegerField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    class_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'general_health_female'


# Main tables 
class Household(models.Model):
    household_id = models.AutoField(primary_key=True)
    household_number = models.CharField(max_length=20, unique=True)
    house_ownership_id = models.IntegerField(null=True, blank=True)
    house_type_id = models.IntegerField(null=True, blank=True)
    house_number = models.CharField(max_length=50, null=True, blank=True)
    address = models.ForeignKey('resident_profiling_module.Address', on_delete=models.SET_NULL, null=True, db_column='address_id')
    household_head_id = models.IntegerField()
    respondent_id = models.IntegerField()
    respondent_relationship_to_hh_id = models.IntegerField(null=True, blank=True)
    visited_by_id = models.IntegerField()
    is_visited = models.BooleanField(default=False)
    quarter = models.IntegerField()
    year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = False
        db_table = 'household'
        
    @staticmethod
    def sp_insert_household(
            house_ownership_id,
            house_type_id,
            barangay,
            city,            
            sitio_id,
            pid,
            house_number,
            street,
            country,
            household_head_id,
            respondent_id,
            relationship_id,
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_household', [
                    house_ownership_id,
                    house_type_id,
                    barangay,
                    city,            
                    sitio_id,
                    pid,
                    house_number,
                    street,
                    country,
                    household_head_id,
                    respondent_id,
                    relationship_id,
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_relationship_to_household_head():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT rth_id, description
                FROM relationship_to_householdhead
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_house_ownership():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT house_ownership_id, description
                FROM House_Ownership
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_house_type():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT house_type_id, description
                FROM house_type
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_sitio():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT sitio_id, sitio_name
                FROM sitio
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_search_resaident(query):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('search_resident', [
                    query
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e

class Family(models.Model):
    family_id = models.AutoField(primary_key=True)
    family_code = models.CharField(max_length=20, unique=True)
    household_id = models.IntegerField()
    household_type_id = models.IntegerField()
    family_head_id = models.IntegerField()  
    respondent_id = models.IntegerField()
    respondent_relationship_to_fh_id = models.IntegerField(null=True, blank=True)
    ip_status = models.BooleanField(default=False)
    ip_tribe = models.CharField(max_length=100, null=True, blank=True)
    nhts_status = models.BooleanField(default=False)
    water_source_type_id = models.IntegerField()
    toilet_facility_type_id = models.IntegerField()
    waste_management_type_id = models.IntegerField()
    waste_other_text = models.CharField(max_length=255, null=True, blank=True)
    is_visited = models.BooleanField(default=False)
    quarter = models.IntegerField()
    year = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        managed = False
        db_table = 'family'