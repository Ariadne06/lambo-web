from django.db import models


class DocumentType(models.Model):
    """Document types for certificates."""
    document_type_id = models.AutoField(primary_key=True)
    document_type_name = models.CharField(max_length=100, unique=True)

    class Meta:
        managed = False
        db_table = 'document_type'


class ClearancePurpose(models.Model):
    """Clearance purposes with associated fee."""
    other_clearance_id = models.AutoField(primary_key=True, db_column='other_clearance_id')
    purpose_name = models.CharField(max_length=120, db_column='purpose_name')
    fee_amount = models.DecimalField(max_digits=10, decimal_places=2, db_column='fee_amount')

    class Meta:
        managed = False
        db_table = 'other_barangay_clearance_type'