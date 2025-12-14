from rest_framework import serializers
from .models import DocumentType, ClearancePurpose


class DocumentTypeSerializer(serializers.ModelSerializer):
    """Serializer for document types."""
    class Meta:
        model = DocumentType
        fields = ['document_type_id', 'document_type_name']


class ClearancePurposeSerializer(serializers.ModelSerializer):
    """Serializer for clearance purposes."""
    class Meta:
        model = ClearancePurpose
        fields = ['other_clearance_id', 'purpose_name', 'fee_amount']


class CreateBarangayClearanceSerializer(serializers.Serializer):
    """Serializer for creating a barangay clearance application."""
    resident_id = serializers.IntegerField(required=True, help_text="ID of the resident requesting clearance")
    other_clearance_id = serializers.IntegerField(required=True, help_text="ID of the clearance purpose type")


class BarangayClearanceResponseSerializer(serializers.Serializer):
    """Serializer for barangay clearance creation response."""
    application_id = serializers.IntegerField(help_text="ID of the created clearance application")
    message = serializers.CharField(help_text="Success message")


class ResidentApplicationListRequestSerializer(serializers.Serializer):
    """Serializer for resident applications list request parameters."""
    query = serializers.CharField(required=False, allow_blank=True, help_text="Search query")
    app_status = serializers.CharField(required=False, allow_blank=True, help_text="Filter by application status")
    pay_status = serializers.CharField(required=False, allow_blank=True, help_text="Filter by payment status")
    limit = serializers.IntegerField(required=False, default=50, min_value=1, max_value=500, help_text="Maximum results")
    offset = serializers.IntegerField(required=False, default=0, min_value=0, help_text="Pagination offset")


class ResidentTransactionListRequestSerializer(serializers.Serializer):
    """Serializer for resident transactions list request parameters."""
    query = serializers.CharField(required=False, allow_blank=True, help_text="Search query")
    pay_status = serializers.CharField(required=False, allow_blank=True, help_text="Filter by payment status")
    limit = serializers.IntegerField(required=False, default=50, min_value=1, max_value=500, help_text="Maximum results")
    offset = serializers.IntegerField(required=False, default=0, min_value=0, help_text="Pagination offset")


class CancelClearanceSerializer(serializers.Serializer):
    """Serializer for cancelling a clearance application."""
    reason = serializers.CharField(required=False, allow_blank=True, help_text="Reason for cancellation")


class RegisterBusinessResidentSerializer(serializers.Serializer):
    """Serializer for resident business registration."""
    # Required fields
    resident_id = serializers.IntegerField(required=True, help_text="ID of the resident registering the business")
    business_name = serializers.CharField(required=True, max_length=255, help_text="Name of the business")
    business_type_id = serializers.IntegerField(required=True, help_text="ID of the business type")
    nature_of_business = serializers.CharField(required=True, help_text="Description of business nature")
    ownership_id = serializers.IntegerField(required=True, help_text="ID of the ownership type")
    
    # Address fields
    house_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=50)
    street = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    barangay = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    sitio_id = serializers.IntegerField(required=True, help_text="ID of the sitio (required)")
    city_municipality = serializers.CharField(required=True, max_length=100)
    country = serializers.CharField(required=False, default='Philippines', max_length=100)
    
    # Financial/docs
    total_gross_income = serializers.DecimalField(required=True, max_digits=15, decimal_places=2, help_text="Total gross income")
    dti_sec_cda_reg_number = serializers.CharField(required=False, allow_blank=True, allow_null=True, max_length=100)
    
    # Clearance category (required)
    clearance_category_id = serializers.IntegerField(required=True, help_text="ID of the clearance category")
    
    # Units (optional, required if category supports units)
    total_units = serializers.IntegerField(required=False, allow_null=True, help_text="Total units for categories that support it")
    
    # Amusement device quantities (required if category = Amusement)
    videoke_count = serializers.IntegerField(required=False, allow_null=True, help_text="Number of videoke devices")
    billiard_count = serializers.IntegerField(required=False, allow_null=True, help_text="Number of billiard tables")
    other_device_count = serializers.IntegerField(required=False, allow_null=True, help_text="Number of other amusement devices")