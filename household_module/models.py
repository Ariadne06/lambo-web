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