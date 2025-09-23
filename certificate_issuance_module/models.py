from django.db import models


class DocumentType(models.Model):
    """Document types for certificates - matching SQL schema"""
    document_type_id = models.AutoField(primary_key=True)
    document_type_name = models.CharField(max_length=100, unique=True)
    
    class Meta:
        managed = False
        db_table = 'document_type'


class ApplicationStatus(models.Model):
    """Application status types - matching SQL schema"""
    application_status_id = models.AutoField(primary_key=True)
    application_status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        managed = False
        db_table = 'application_status'


class ClearancePurpose(models.Model):
    """Clearance purposes with fees - matching SQL schema"""
    clearance_purpose_id = models.AutoField(primary_key=True)
    purpose_name = models.CharField(max_length=120, unique=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    
    class Meta:
        managed = False
        db_table = 'clearance_purpose'


class PaymentStatus(models.Model):
    """Payment status types - matching SQL schema"""
    payment_status_id = models.AutoField(primary_key=True)
    payment_status_name = models.CharField(max_length=50, unique=True)
    
    class Meta:
        managed = False
        db_table = 'payment_status'


class Application(models.Model):
    """Main application table - matching SQL schema"""
    application_id = models.AutoField(primary_key=True)
    application_description = models.CharField(max_length=255)
    application_status_id = models.IntegerField()
    business_id = models.IntegerField(blank=True, null=True)  # for Business Clearance renewals
    applicant_id = models.IntegerField()  # references Resident(resident_id)
    application_date = models.DateTimeField(auto_now_add=True)
    approval_date = models.DateTimeField(blank=True, null=True)
    reviewed_by = models.IntegerField(blank=True, null=True)  # references Personnel_Credentials(personnel_id)
    clearance_purpose_id = models.IntegerField(blank=True, null=True)  # required for Barangay Clearance
    document_type_id = models.IntegerField()  # references Document_Type(document_type_id)
    
    class Meta:
        managed = False
        db_table = 'application'


class PaymentTransactions(models.Model):
    """Payment transactions - matching SQL schema"""
    payment_id = models.AutoField(primary_key=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)  # total collected
    payment_status_id = models.IntegerField()
    application_id = models.IntegerField()
    or_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'payment_transactions'


class DocumentIssuance(models.Model):
    """Document issuance records - matching SQL schema"""
    document_id = models.AutoField(primary_key=True)
    document_type_id = models.IntegerField()
    resident_id = models.IntegerField()
    issued_by = models.IntegerField()  # references Personnel_Credentials(personnel_id)
    date_issued = models.DateTimeField(auto_now_add=True)
    validity_period = models.DateField(blank=True, null=True)
    remarks = models.CharField(max_length=255, blank=True, null=True)
    application_id = models.IntegerField(blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'document_issuance'


class DocumentPricingRules(models.Model):
    """Document pricing rules - matching SQL schema"""
    pricing_rule_id = models.AutoField(primary_key=True)
    business_type_id = models.IntegerField(blank=True, null=True)
    document_type_id = models.IntegerField()
    base_fee = models.DecimalField(max_digits=10, decimal_places=2)
    additional_fee_per_unit = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    unit_limit = models.IntegerField(blank=True, null=True)
    description = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        managed = False
        db_table = 'document_pricing_rules'