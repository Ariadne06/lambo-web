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
        fields = ['clearance_purpose_id', 'purpose_name', 'fee']