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
    clearance_purpose_id = models.AutoField(primary_key=True)
    purpose_name = models.CharField(max_length=120, unique=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'clearance_purpose'