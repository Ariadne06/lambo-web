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

class Relationship(models.Model):
    relationship_id = models.AutoField(primary_key=True)
    relationship_name = models.CharField(max_length=50, unique=True)

    class Meta:
        managed = False 
        db_table = 'relationship'

class GeneralHealthMale(models.Model):
    ghtm_id = models.AutoField(primary_key=True)
    family_member_id = models.IntegerField()
    quarter_id = models.IntegerField()
    medical_history_ids = models.JSONField(null=True, blank=True)
    age = models.IntegerField(null=True, blank=True)
    class_id = models.IntegerField()
    smoker = models.BooleanField(null=True, blank=True)
    alcohol_drinker = models.BooleanField(null=True, blank=True)
    sexually_active = models.BooleanField(null=True, blank=True)
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
    smoker = models.BooleanField(null=True, blank=True)
    alcohol_drinker = models.BooleanField(null=True, blank=True)
    sexually_active = models.BooleanField(null=True, blank=True)
    age_of_menarche = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    added_by = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'general_health_female'

# child health models
class FeedingMethod(models.Model):
    feeding_method_id = models.AutoField(primary_key=True)
    method_name = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        managed = False
        db_table = 'feeding_method'


class Month(models.Model):
    month_id = models.AutoField(primary_key=True)
    month_sequence_name = models.CharField(max_length=20, unique=True)
    month_number = models.IntegerField()
    
    class Meta:
        managed = False
        db_table = 'month'


class TTStatus(models.Model):
    tt_status_id = models.AutoField(primary_key=True)
    tt_code = models.CharField(max_length=10, unique=True)
    tt_name = models.CharField(max_length=100)
    
    class Meta:
        managed = False
        db_table = 'tt_status'


class VaccineType(models.Model):
    vaccine_type_id = models.AutoField(primary_key=True)
    vaccine_name = models.CharField(max_length=100, unique=True)
    at_birth = models.BooleanField(default=False)
    first_dose = models.BooleanField(default=False)
    second_dose = models.BooleanField(default=False)
    third_dose = models.BooleanField(default=False)
    interval_between_doses = models.DurationField(null=True, blank=True)
    date_added = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    added_by = models.IntegerField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'vaccine_type'


class DoseType(models.Model):
    dose_type_id = models.AutoField(primary_key=True)
    dose_name = models.CharField(max_length=30, unique=True)
    
    class Meta:
        managed = False
        db_table = 'dose_type'


class Supplements(models.Model):
    supplement_id = models.AutoField(primary_key=True)
    supplement_name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        managed = False
        db_table = 'supplements'


class ChildHealthRecord(models.Model):
    child_health_id = models.AutoField(primary_key=True)
    child_id = models.IntegerField()  # FK to Resident
    time_of_birth = models.TimeField(null=True, blank=True)
    birth_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    birth_length_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    place_of_delivery = models.CharField(max_length=200, null=True, blank=True)
    address_landmark = models.CharField(max_length=200, null=True, blank=True)
    tt_status_of_mother = models.IntegerField(null=True, blank=True)
    tt_status_date = models.DateField(null=True, blank=True)
    newborn_screening_status = models.BooleanField(null=True, blank=True)
    newborn_screening_status_date = models.DateField(null=True, blank=True)
    feeding_method_id = models.IntegerField(null=True, blank=True)
    created_by = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'child_health_record'


class ExclusiveBreastfeed(models.Model):
    eb_id = models.AutoField(primary_key=True)
    child_health_id = models.IntegerField()
    month_id = models.IntegerField()
    date_assessed = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'exclusive_breastfeed'


class ChildImmunizationRecord(models.Model):
    immunization_id = models.AutoField(primary_key=True)
    child_health_id = models.IntegerField()
    vaccine_type_id = models.IntegerField()
    dose_type_id = models.IntegerField()
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'child_immunization_record'


class ChildSupplementRecord(models.Model):
    child_health_id = models.IntegerField()
    supplement_id = models.IntegerField()
    age_in_months = models.IntegerField()
    date_given = models.DateTimeField(auto_now_add=True)
    given_by = models.IntegerField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'child_supplement_record'
        unique_together = (('child_health_id', 'supplement_id', 'age_in_months'),)


class ResidentMedicalHistory(models.Model):
    rmh_id = models.AutoField(primary_key=True)
    child_health_id = models.IntegerField()
    medical_history_name = models.CharField(max_length=200)
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'resident_medical_history'


class ResidentSurgicalHistory(models.Model):
    rsh_id = models.AutoField(primary_key=True)
    child_health_id = models.IntegerField()
    surgical_history_name = models.CharField(max_length=200)
    date_of_surgery = models.DateField()
    date_added = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        managed = False
        db_table = 'resident_surgical_history'


class ChildGrowthMonitoring(models.Model):
    cgm_id = models.AutoField(primary_key=True)
    child_health_id = models.IntegerField()
    date_of_visit = models.DateTimeField(auto_now_add=True)
    age_in_months = models.IntegerField()
    weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    temp_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    resp_rate = models.IntegerField(null=True, blank=True)
    pulse_rate = models.IntegerField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        managed = False
        db_table = 'child_growth_monitoring'

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
                SELECT *
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
                SELECT *
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
                SELECT *
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
                SELECT *
                FROM sitio
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_search_resident(query):
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
        
    @staticmethod
    def sp_get_all_households(
            query,
            barangay,
            sitio_id,
            status,
            quarter_id,
            limit,
            offset
        ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_all_households', [
                    query,
                    barangay,
                    sitio_id,
                    status,
                    quarter_id,
                    limit,
                    offset
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_specific_household(hid, qid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_specific_household', [hid, qid])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_update_household(
            hid,
            pid,
            house_ownership_id,
            house_type_id,
            barangay,
            city, 
            house_number,
            street,        
            sitio_id,
            country,
            household_head_id,
            respondent_id,
            relationship_id,
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('update_household', [
                    hid,
                    pid,
                    house_ownership_id,
                    house_type_id,
                    barangay,
                    city, 
                    house_number,
                    street,        
                    sitio_id,
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
    def sp_mark_household_visited(hid, pid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('mark_household_visited', [hid, pid])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_household_type():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Household_Type
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_quarter():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Quarter
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_current_quarter_id():
        try:
            with connection.cursor() as cursor:
                cursor.callproc("get_current_quarter_id", [])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_reactivate_household(hid, pid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('reactivate_household', [hid, pid])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_deactivate_household(hid, reason, pid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('deactivate_household', [hid, reason, pid,])
                result = cursor.fetchone()
                return result[0] if result else None 
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
        
    @staticmethod
    def sp_insert_family(
            household_id,
            household_type_id,
            family_head_id,
            water_source_type_id,
            toilet_facility_type_id,
            waste_management_type_id,
            respondent_id,
            rtf_id,
            rth_id,
            head_rth_id,
            ip_status,
            ip_tribe,
            nhts_status,
            waste_other_text,
            pid,
            performed_by_type,
            bhw_assignment
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_family', [
                    household_id,
                    household_type_id,
                    family_head_id,
                    water_source_type_id,
                    toilet_facility_type_id,
                    waste_management_type_id,
                    respondent_id,
                    rtf_id,
                    rth_id,
                    head_rth_id,
                    ip_status,
                    ip_tribe,
                    nhts_status,
                    waste_other_text,
                    pid,
                    performed_by_type,
                    bhw_assignment
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_water_source_type():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Water_Source_Type
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_waste_management_type():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Waste_Management_Type
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_toilet_facility_type():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Toilet_Facility_Type
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_relationship_to_family_head():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM relationship_to_familyhead
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_family_summaries_per_household(
            hid,
            qid
        ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_family_summaries_per_household', [
                    hid,
                    qid
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_philhealth_category():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Philhealth_Category
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_nutrition_status():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Nutrition_Status
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise
        
    @staticmethod
    def sp_insert_family_member(
            resident_id,
            family_id,
            rth_id,
            rtf_id,
            philhealth_number,
            membership_type,
            philhealth_category,
            nutrition_status,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('insert_family_member', [
                resident_id,
                family_id,
                rth_id,
                rtf_id,
                philhealth_number,
                membership_type,
                philhealth_category,
                nutrition_status,
                pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_specific_family(fid, qid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_specific_family', [fid, qid])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_mark_family_visited(fid, pid):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('mark_family_visited', [fid, pid])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_update_family(
            fid,
            pid,
            hid,
            household_type_id,
            family_head_id,
            respondent_id,
            rtf_id,
            ip_status,
            ip_tribe,
            nhts_status,
            water_source_type_id,
            toilet_facility_type_id,
            waste_management_type_id,
            waste_other_text,
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('update_family', [
                    fid,
                    pid,
                    hid,
                    household_type_id,
                    family_head_id,
                    respondent_id,
                    rtf_id,
                    ip_status,
                    ip_tribe,
                    nhts_status,
                    water_source_type_id,
                    toilet_facility_type_id,
                    waste_management_type_id,
                    waste_other_text,
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_deactivate_family(fid, pid, reason):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('deactivate_family', [fid, pid, reason])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_update_family_member(
            fm_id,
            pid,
            rth_id,
            rtf_id,
            philhealthid_number,
            membership_type,
            philhealth_category_id,
            nutrition_status_id,
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('update_family_member', [
                    fm_id,
                    pid,
                    rth_id,
                    rtf_id,
                    philhealthid_number,
                    membership_type,
                    philhealth_category_id,
                    nutrition_status_id,
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_specific_family_member(fm_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_specific_family_member', [fm_id])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e

    @staticmethod
    def sp_remove_family_member_from_family(rid, fid, pid, performed_by_type, assignment, reason):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('remove_family_member_from_family', [rid, fid, pid, performed_by_type, assignment, reason])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_link_resident_relation(
            resident_id,
            related_resident_id,
            relationship_id,
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('link_resident_relation', [
                    resident_id,
                    related_resident_id,
                    relationship_id,
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e 
        
    @staticmethod
    def sp_unlink_resident_relation(
            resident_id,
            related_resident_id,
            relationship_id,
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('unlink_resident_relation', [
                    resident_id,
                    related_resident_id,
                    relationship_id,
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_resident_links(
            resident_id,
        ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_resident_links', [
                    resident_id,
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_link_relationship():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Relationship
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_save_general_health_for_member(
            family_member_id,
            class_id,
            medical_history_ids,
            wra_lmp,
            fp_method_yn,
            fp_method_id,
            fp_status_id,
            age_of_menarche,
            smoker,
            alcohol_drinker,
            sexually_active,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('save_general_health_for_member', [
                    family_member_id,
                    class_id,
                    medical_history_ids,
                    wra_lmp,
                    fp_method_yn,
                    fp_method_id,
                    fp_status_id,
                    age_of_menarche,
                    smoker,
                    alcohol_drinker,
                    sexually_active,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_fp_method():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM FP_Method
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_fp_status():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM FP_Status
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_classifications():
        try:
            with connection.cursor() as cursor:
                cursor.execute("""
                SELECT *
                FROM Class
            """)
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_update_general_health_for_member(
            family_member_id,
            class_id,
            apply_medical_history,
            medical_history_ids,
            apply_fp,
            wra_lmp,
            fp_method_yn,
            fp_method_id,
            fp_status_id,
            age_of_menarche,
            apply_lifestyle,
            smoker,
            alcohol_drinker,
            sexually_active,
            pid
            ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('update_general_health_for_member', [
                    family_member_id,
                    class_id,
                    apply_medical_history,
                    medical_history_ids,
                    apply_fp,
                    wra_lmp,
                    fp_method_yn,
                    fp_method_id,
                    fp_status_id,
                    age_of_menarche,
                    apply_lifestyle,
                    smoker,
                    alcohol_drinker,
                    sexually_active,
                    pid
                ])
                result = cursor.fetchone()
                return result[0] if result else None 
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_get_specific_family_member_genhealth(fm_id):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('get_specific_family_member_genhealth', [fm_id])
                cols = [c[0] for c in cursor.description]
                row = cursor.fetchone()
                return dict(zip(cols, row)) if row else None
        except Exception as e:
            raise e
        
    @staticmethod
    def sp_view_all_general_health(
            query,
            quarter_id,
            sitio_id,
            sex,
            limit,
            offset
        ):
        try:
            with connection.cursor() as cursor:
                cursor.callproc('view_all_general_health', [
                    query,
                    quarter_id,
                    sitio_id,
                    sex,
                    limit,
                    offset
                ])
                cols = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
                return [dict(zip(cols, row)) for row in rows]
        except Exception as e:
            raise e