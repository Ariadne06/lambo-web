from rest_framework import viewsets
from .models import DocumentType, ClearancePurpose
from .serializers import DocumentTypeSerializer, ClearancePurposeSerializer


class DocumentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for document types."""
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer


class ClearancePurposeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for clearance purposes."""
    queryset = ClearancePurpose.objects.all()
    serializer_class = ClearancePurposeSerializer