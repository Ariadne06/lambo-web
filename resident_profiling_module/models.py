# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models


class ActivityLog(models.Model):
    log_id = models.AutoField(primary_key=True)
    action = models.CharField(max_length=20)
    subsystem = models.ForeignKey('Subsystem', models.DO_NOTHING)
    table_name = models.CharField(max_length=100)
    action_details = models.TextField()
    performed_by = models.IntegerField(blank=True, null=True)
    log_timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'activity_log'


class Address(models.Model):
    address_id = models.AutoField(primary_key=True)
    house_number = models.CharField(max_length=50, blank=True, null=True)
    street = models.CharField(max_length=200, blank=True, null=True)
    barangay = models.CharField(max_length=200, blank=True, null=True)
    sitio = models.ForeignKey('Sitio', models.DO_NOTHING, blank=True, null=True)
    city_municipality = models.CharField(max_length=100)
    country = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'address'


class AuthGroup(models.Model):
    name = models.CharField(unique=True, max_length=150)

    class Meta:
        managed = False
        db_table = 'auth_group'


class AuthGroupPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)
    permission = models.ForeignKey('AuthPermission', models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_group_permissions'
        unique_together = (('group', 'permission'),)


class AuthPermission(models.Model):
    name = models.CharField(max_length=255)
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING)
    codename = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'auth_permission'
        unique_together = (('content_type', 'codename'),)


class AuthUser(models.Model):
    password = models.CharField(max_length=128)
    last_login = models.DateTimeField(blank=True, null=True)
    is_superuser = models.BooleanField()
    username = models.CharField(unique=True, max_length=150)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=150)
    email = models.CharField(max_length=254)
    is_staff = models.BooleanField()
    is_active = models.BooleanField()
    date_joined = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'auth_user'


class AuthUserGroups(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    group = models.ForeignKey(AuthGroup, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_groups'
        unique_together = (('user', 'group'),)


class AuthUserUserPermissions(models.Model):
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)
    permission = models.ForeignKey(AuthPermission, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'auth_user_user_permissions'
        unique_together = (('user', 'permission'),)


class CivilStatus(models.Model):
    civil_stat_id = models.AutoField(primary_key=True)
    civil_code = models.CharField(max_length=10)
    civil_name = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = 'civil_status'


class DjangoAdminLog(models.Model):
    action_time = models.DateTimeField()
    object_id = models.TextField(blank=True, null=True)
    object_repr = models.CharField(max_length=200)
    action_flag = models.SmallIntegerField()
    change_message = models.TextField()
    content_type = models.ForeignKey('DjangoContentType', models.DO_NOTHING, blank=True, null=True)
    user = models.ForeignKey(AuthUser, models.DO_NOTHING)

    class Meta:
        managed = False
        db_table = 'django_admin_log'


class DjangoContentType(models.Model):
    app_label = models.CharField(max_length=100)
    model = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'django_content_type'
        unique_together = (('app_label', 'model'),)


class DjangoMigrations(models.Model):
    id = models.BigAutoField(primary_key=True)
    app = models.CharField(max_length=255)
    name = models.CharField(max_length=255)
    applied = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_migrations'


class DjangoSession(models.Model):
    session_key = models.CharField(primary_key=True, max_length=40)
    session_data = models.TextField()
    expire_date = models.DateTimeField()

    class Meta:
        managed = False
        db_table = 'django_session'


class EducationalAttainment(models.Model):
    educational_attain_id = models.AutoField(primary_key=True)
    educational_level = models.CharField(max_length=30)
    educational_attain_name = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = 'educational_attainment'


class Quarter(models.Model):
    quarter_id = models.AutoField(primary_key=True)
    quarter_number = models.IntegerField()
    quarter_name = models.CharField(max_length=20)
    year = models.IntegerField()
    start_date = models.DateField()
    end_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'quarter'


class Religion(models.Model):
    religion_id = models.AutoField(primary_key=True)
    religion_cat = models.ForeignKey('ReligionCategory', models.DO_NOTHING)
    other_religion = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'religion'


class ReligionCategory(models.Model):
    religion_cat_id = models.AutoField(primary_key=True)
    religion_code = models.CharField(unique=True, max_length=10)
    religion_name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'religion_category'


class Resident(models.Model):
    resident_id = models.AutoField(primary_key=True)
    resident_code = models.CharField(max_length=20, unique=True, blank=True, null=True)
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    suffix = models.CharField(max_length=10, blank=True, null=True)
    dob = models.DateField()
    sex = models.CharField(max_length=10)
    gender = models.CharField(max_length=15, blank=True, null=True)
    is_voter = models.BooleanField(blank=True, null=True)
    email = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_recorded = models.DateField()
    religion = models.ForeignKey('Religion', on_delete=models.SET_NULL, blank=True, null=True, db_column='religion_id')
    civil_status = models.ForeignKey('CivilStatus', on_delete=models.SET_NULL, blank=True, null=True, db_column='civil_stat_id')
    educational_attainment = models.ForeignKey('EducationalAttainment', on_delete=models.SET_NULL, blank=True, null=True, db_column='educational_attain_id')
    status = models.ForeignKey('ResidentStatus', on_delete=models.PROTECT, db_column='status_id')
    address = models.ForeignKey('Address', on_delete=models.SET_NULL, blank=True, null=True, db_column='address_id')

    def __str__(self):
        return f"{self.last_name}, {self.first_name}"

    class Meta:
        managed = False
        db_table = 'resident'


class ResidentBirthCertificate(models.Model):
    birth_cert_id = models.AutoField(primary_key=True)
    resident = models.ForeignKey(Resident, models.DO_NOTHING, null=True, blank=True)
    image_data = models.BinaryField()
    date_uploaded = models.DateTimeField(blank=True, null=True)
    uploaded_by = models.IntegerField(blank=True, null=True)
    verified = models.BooleanField(blank=True, null=True)
    verification_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resident_birth_certificate'


class ResidentCredentials(models.Model):
    account_id = models.AutoField(primary_key=True)
    resident = models.OneToOneField(Resident, models.DO_NOTHING)
    username = models.CharField(unique=True, max_length=50)
    password = models.CharField(max_length=255)
    is_active = models.BooleanField(blank=True, null=True)
    req_pass_change = models.BooleanField(blank=True, null=True)
    password_reset_requested_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resident_credentials'


class ResidentIdDocument(models.Model):
    id_doc_id = models.AutoField(primary_key=True)
    resident = models.ForeignKey(Resident, models.DO_NOTHING, null=True, blank=True)
    document_type = models.CharField(max_length=50)
    document_number = models.CharField(max_length=50, blank=True, null=True)
    image_data = models.BinaryField()
    date_uploaded = models.DateTimeField(blank=True, null=True)
    uploaded_by = models.IntegerField(blank=True, null=True)
    verified = models.BooleanField(blank=True, null=True)
    verification_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resident_id_document'


class ResidentQuarterly(models.Model):
    rq_id = models.AutoField(primary_key=True)
    resident = models.ForeignKey(Resident, models.DO_NOTHING)
    quarter = models.ForeignKey(Quarter, models.DO_NOTHING)
    last_name = models.CharField(max_length=50)
    first_name = models.CharField(max_length=50)
    middle_name = models.CharField(max_length=50, blank=True, null=True)
    suffix = models.CharField(max_length=10, blank=True, null=True)
    dob = models.DateField()
    sex = models.CharField(max_length=10)
    gender = models.CharField(max_length=15, blank=True, null=True)
    is_voter = models.BooleanField()
    email = models.CharField(max_length=100, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    date_snapshot = models.DateField(blank=True, null=True)
    religion = models.ForeignKey(Religion, models.DO_NOTHING, blank=True, null=True)
    civil_stat = models.ForeignKey(CivilStatus, models.DO_NOTHING, blank=True, null=True)
    educational_attain = models.ForeignKey(EducationalAttainment, models.DO_NOTHING, blank=True, null=True)
    status = models.ForeignKey('ResidentStatus', models.DO_NOTHING)
    address = models.ForeignKey(Address, models.DO_NOTHING, blank=True, null=True)
    encoded_by = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'resident_quarterly'


class ResidentStatus(models.Model):
    status_id = models.AutoField(primary_key=True)
    status_name = models.CharField(max_length=20)
    description = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resident_status'


class ResidentUpdateLogs(models.Model):
    request_id = models.AutoField(primary_key=True)
    resident = models.ForeignKey(Resident, models.DO_NOTHING)
    request_by = models.IntegerField()
    field_name = models.TextField()
    current_value = models.TextField()
    proposed_value = models.TextField()
    date_requested = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'resident_update_logs'


class Sitio(models.Model):
    sitio_id = models.AutoField(primary_key=True)
    district_number = models.IntegerField()
    sitio_name = models.CharField(max_length=50)

    class Meta:
        managed = False
        db_table = 'sitio'

class IdentityDocType(models.Model):
    identity_doc_type_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'identity_document_type'  


class Subsystem(models.Model):
    subsystem_id = models.AutoField(primary_key=True)
    subsystem_name = models.CharField(unique=True, max_length=100)
    description = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'subsystem'
