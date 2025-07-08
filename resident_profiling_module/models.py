# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class Resident(models.Model):
    resident_id = models.AutoField(primary_key=True)
    last_name = models.CharField(max_length=100)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)
    dob = models.DateField()
    sex = models.CharField(max_length=10)
    date_recorded = models.DateField()
    religion = models.ForeignKey('Religion', models.DO_NOTHING)
    civil_stat = models.ForeignKey('CivilStatus', models.DO_NOTHING)
    educational_attain = models.ForeignKey('EducationalAttainment', models.DO_NOTHING)
    is_voter = models.BooleanField()
    # personnel = models.ForeignKey('Personnel', models.DO_NOTHING, blank=True, null=True)
    address = models.ForeignKey('Address', models.DO_NOTHING)
    status = models.ForeignKey('ResidentStatus', models.DO_NOTHING)
    quarter = models.ForeignKey('Quarter', models.DO_NOTHING)

    class Meta:
        db_table = 'resident'
        managed = False

class Religion(models.Model):
    religion_id = models.AutoField(primary_key=True)
    religion_cat_id = models.IntegerField()  # or ForeignKey if available
    other_religion = models.CharField(max_length=100, blank=True, null=True)

    class Meta: 
        db_table = 'religion'
        managed = False

class CivilStatus(models.Model):
    civil_stat_id = models.AutoField(primary_key=True)
    civil_code = models.CharField(max_length=100)
    civil_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'civil_status'
        managed = False


class EducationalAttainment(models.Model):
    educational_attain_id = models.AutoField(primary_key=True)
    educational_level = models.CharField(max_length=100)
    educational_attain_name = models.CharField(max_length=100)

    class Meta:
        db_table = 'educational_attainment'
        managed = False

class Address(models.Model):
    address_id = models.AutoField(primary_key=True)
    barangay = models.CharField(max_length=100)
    street = models.CharField(max_length=100, blank=True, null=True)
    house_number = models.CharField(max_length=100, blank=True, null=True)
    sitio_id = models.IntegerField(blank=True, null=True)  # or ForeignKey if available

    class Meta:
        db_table = 'address'
        managed = False

class ResidentStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=100)
    description = models.CharField(max_length=100)

    class Meta:
        db_table = 'resident_status'
        managed = False

class Quarter(models.Model):
    quarter_id = models.AutoField(primary_key=True)
    quarter = models.CharField(max_length=100)

    class Meta:
        db_table = 'quarter'
        managed = False