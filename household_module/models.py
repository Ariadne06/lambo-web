from django.db import models, connection


class HouseOwnershipType(models.Model):
    house_ownership_id = models.AutoField(primary_key=True)  
    description = models.TextField(blank=True, null=True)  
    
    class Meta:
        managed = False
        db_table = 'house_ownership'

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

# Main tables 
class Household(models.Model):
    household_id = models.AutoField(primary_key=True)
    household_code = models.CharField(max_length=20, unique=True)
    house_ownership_type_id = models.IntegerField(null=True, blank=True)
    house_number = models.CharField(max_length=50, null=True, blank=True)
    address_id = models.IntegerField()
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
    family_head_id = models.IntegerField()  # REQUIRED!
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
        