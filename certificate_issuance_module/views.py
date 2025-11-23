from rest_framework import viewsets, status, views
from rest_framework.response import Response
from .models import DocumentType, ClearancePurpose
from .serializers import (
    DocumentTypeSerializer, 
    ClearancePurposeSerializer,
    CreateBarangayClearanceSerializer,
    BarangayClearanceResponseSerializer
)
from .utils.database_helpers import create_barangay_clearance


class DocumentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for document types."""
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer


class ClearancePurposeViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only viewset for clearance purposes."""
    queryset = ClearancePurpose.objects.all()
    serializer_class = ClearancePurposeSerializer


class CreateClearanceApplicationView(views.APIView):
    """API view for creating barangay clearance applications."""
    
    def post(self, request):
        """
        Create a new barangay clearance application.
        
        Expected payload:
        {
            "resident_id": 123,
            "other_clearance_id": 1
        }
        """
        serializer = CreateBarangayClearanceSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            application_id = create_barangay_clearance(
                resident_id=serializer.validated_data['resident_id'],
                other_clearance_id=serializer.validated_data['other_clearance_id']
            )
            
            if application_id:
                response_data = {
                    'application_id': application_id,
                    'message': 'Barangay clearance application created successfully'
                }
                return Response(response_data, status=status.HTTP_201_CREATED)
            else:
                return Response(
                    {'error': 'Failed to create barangay clearance application'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
                
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )