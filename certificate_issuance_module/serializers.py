from rest_framework import serializers
from .models import DocumentType, ClearancePurpose, ApplicationStatus, Application, PaymentTransactions, DocumentIssuance
from resident_profiling_module.models import Resident
from .services.certificate_service import CertificateService


class DocumentTypeSerializer(serializers.ModelSerializer):
    """Document type serializer - matching SQL schema"""
    class Meta:
        model = DocumentType
        fields = ['document_type_id', 'document_type_name']


class ClearancePurposeSerializer(serializers.ModelSerializer):
    """Clearance purpose serializer - matching SQL schema"""
    class Meta:
        model = ClearancePurpose
        fields = ['clearance_purpose_id', 'purpose_name', 'fee']


class ApplicationStatusSerializer(serializers.ModelSerializer):
    """Application status serializer - matching SQL schema"""
    class Meta:
        model = ApplicationStatus
        fields = ['application_status_id', 'application_status_name']


class FeeQuoteRequestSerializer(serializers.Serializer):
    """Fee quote request serializer - following household_module pattern"""
    resident_id = serializers.IntegerField(required=True)
    document_type_id = serializers.IntegerField(required=True)
    business_id = serializers.IntegerField(required=False, allow_null=True)
    clearance_purpose_id = serializers.IntegerField(required=False, allow_null=True)
    
    def validate(self, data):
        """Validation - following household_module pattern"""
        document_type_id = data.get('document_type_id')
        clearance_purpose_id = data.get('clearance_purpose_id')
        
        # Check if Barangay Clearance requires purpose (document_type_id = 1)
        if document_type_id == 1 and not clearance_purpose_id:
            raise serializers.ValidationError({
                'clearance_purpose_id': 'Barangay Clearance requires a purpose to be selected.'
            })
        
        return data


class CertificateApplicationSerializer(serializers.ModelSerializer):
    """Certificate application serializer - matching SQL schema"""
    # Write-only fields for creation
    applicant_id = serializers.IntegerField(write_only=True, required=True)
    document_type_id = serializers.IntegerField(write_only=True, required=True)
    application_description = serializers.CharField(write_only=True, required=True, max_length=255)
    business_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    clearance_purpose_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    
    class Meta:
        model = Application
        fields = [
            'application_id', 'application_date', 'approval_date',
            'applicant_id', 'document_type_id', 'application_description', 
            'business_id', 'clearance_purpose_id'
        ]
        read_only_fields = ['application_id', 'application_date', 'approval_date']
    
    def validate(self, data):
        """Validation - following household_module pattern"""
        document_type_id = data.get('document_type_id')
        clearance_purpose_id = data.get('clearance_purpose_id')
        
        # Check if Barangay Clearance requires purpose (document_type_id = 1)
        if document_type_id == 1 and not clearance_purpose_id:
            raise serializers.ValidationError({
                'clearance_purpose_id': 'Barangay Clearance requires a purpose to be selected.'
            })
        
        return data
    
    def create(self, validated_data):
        """Create application using service - following household_module pattern"""
        try:
            applicant_id = validated_data['applicant_id']
            document_type_id = validated_data['document_type_id']
            application_description = validated_data['application_description']
            business_id = validated_data.get('business_id')
            clearance_purpose_id = validated_data.get('clearance_purpose_id')
            
            print(f"Creating certificate application for applicant: {applicant_id}")
            
            application_id = CertificateService.submit_application(
                applicant_id, document_type_id, application_description, 
                business_id, clearance_purpose_id
            )
            
            if not application_id:
                raise serializers.ValidationError("Failed to create certificate application")
            
            # Return a mock application object for response
            application = Application()
            application.application_id = application_id
            application.applicant_id = applicant_id
            application.document_type_id = document_type_id
            
            print(f"Certificate application created successfully with ID: {application_id}")
            return application
            
        except Exception as e:
            print(f"Certificate application creation failed: {str(e)}")
            raise serializers.ValidationError(f"Application creation failed: {str(e)}")


class ApplicationListSerializer(serializers.Serializer):
    """Simple serializer for application list responses - matching SQL query results"""
    application_id = serializers.IntegerField()
    document_type_name = serializers.CharField()
    application_description = serializers.CharField(allow_blank=True, allow_null=True)
    purpose_name = serializers.CharField(allow_blank=True, allow_null=True)
    application_status_name = serializers.CharField()
    fee_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    application_date = serializers.DateTimeField()
    approval_date = serializers.DateTimeField(allow_null=True)
    remarks = serializers.CharField(allow_blank=True, allow_null=True)


class ApplicationDetailSerializer(serializers.Serializer):
    """Detailed application serializer - matching SQL query results"""
    application_id = serializers.IntegerField()
    applicant_id = serializers.IntegerField()
    applicant_name = serializers.CharField()
    document_type_name = serializers.CharField()
    application_description = serializers.CharField(allow_blank=True, allow_null=True)
    purpose_name = serializers.CharField(allow_blank=True, allow_null=True)
    application_status_name = serializers.CharField()
    fee_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    application_date = serializers.DateTimeField()
    approval_date = serializers.DateTimeField(allow_null=True)
    processed_by = serializers.CharField(allow_blank=True, allow_null=True)
    remarks = serializers.CharField(allow_blank=True, allow_null=True)
    certificate_number = serializers.CharField(allow_blank=True, allow_null=True)
    issued_date = serializers.DateTimeField(allow_null=True)
    valid_until = serializers.DateField(allow_null=True)


class PendingApplicationSerializer(serializers.Serializer):
    """Serializer for pending applications list - matching SQL query results"""
    application_id = serializers.IntegerField()
    applicant_id = serializers.IntegerField()
    applicant_name = serializers.CharField()
    document_type_name = serializers.CharField()
    application_description = serializers.CharField(allow_blank=True, allow_null=True)
    purpose_name = serializers.CharField(allow_blank=True, allow_null=True)
    fee_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    application_date = serializers.DateTimeField()
    address = serializers.CharField()


class ReviewApplicationSerializer(serializers.Serializer):
    """Serializer for secretary reviewing applications - matching SQL functions"""
    decision = serializers.ChoiceField(choices=['FOR_PAYMENT', 'REJECT'], required=True)
    review_notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class RecordPaymentSerializer(serializers.Serializer):
    """Serializer for treasurer recording payment - matching SQL functions"""
    document_type_id = serializers.IntegerField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    or_number = serializers.CharField(max_length=50, required=True)
    extra_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, default=0)


class MarkCompletedSerializer(serializers.Serializer):
    """Serializer for secretary marking application completed - matching SQL functions"""
    remarks = serializers.CharField(required=False, allow_blank=True, allow_null=True)