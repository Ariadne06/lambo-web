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