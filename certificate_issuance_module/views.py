from rest_framework import viewsets, status, views
from rest_framework.response import Response
from .models import DocumentType, ClearancePurpose
from .serializers import (
    DocumentTypeSerializer, 
    ClearancePurposeSerializer,
    CreateBarangayClearanceSerializer,
    BarangayClearanceResponseSerializer,
    ResidentApplicationListRequestSerializer,
    ResidentTransactionListRequestSerializer,
    CancelClearanceSerializer
)
from .utils.database_helpers import (
    create_barangay_clearance,
    get_resident_applications,
    get_resident_application_detail,
    get_resident_transactions,
    get_resident_transaction_detail,
    cancel_resident_clearance
)


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


class ResidentApplicationListView(views.APIView):
    """API view for listing all applications for a specific resident."""
    
    def get(self, request, resident_id):
        """
        Get all applications (barangay & business) for a specific resident.
        
        Query parameters:
        - query: Search term (optional)
        - app_status: Application status filter (optional)
        - pay_status: Payment status filter (optional)
        - limit: Maximum results (default: 50)
        - offset: Pagination offset (default: 0)
        """
        # Validate query parameters using request.query_params
        serializer = ResidentApplicationListRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            applications = get_resident_applications(
                resident_id=resident_id,
                **serializer.validated_data
            )
            
            return Response({
                'success': True,
                'data': applications,
                'count': len(applications),
                'limit': serializer.validated_data.get('limit', 50),
                'offset': serializer.validated_data.get('offset', 0)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResidentApplicationDetailView(views.APIView):
    """API view for getting detailed information about a specific application."""
    
    def get(self, request, resident_id, application_id):
        """
        Get detailed information for a specific application.
        
        Path parameters:
        - resident_id: ID of the resident (for ownership verification)
        - application_id: ID of the application
        """
        try:
            application = get_resident_application_detail(resident_id, application_id)
            
            if not application:
                return Response(
                    {'success': False, 'error': 'Application not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({
                'success': True,
                'data': application
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = str(e)
            
            # Handle ownership error
            if 'not allowed to view' in error_message.lower():
                return Response(
                    {'success': False, 'error': error_message},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return Response(
                {'success': False, 'error': error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResidentTransactionListView(views.APIView):
    """API view for listing all payment transactions for a specific resident."""
    
    def get(self, request, resident_id):
        """
        Get all payment transactions for a specific resident.
        
        Query parameters:
        - query: Search term (optional)
        - pay_status: Payment status filter (optional)
        - limit: Maximum results (default: 50)
        - offset: Pagination offset (default: 0)
        """
        # Validate query parameters using request.query_params
        serializer = ResidentTransactionListRequestSerializer(data=request.query_params)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            transactions = get_resident_transactions(
                resident_id=resident_id,
                **serializer.validated_data
            )
            
            return Response({
                'success': True,
                'data': transactions,
                'count': len(transactions),
                'limit': serializer.validated_data.get('limit', 50),
                'offset': serializer.validated_data.get('offset', 0)
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'success': False, 'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class ResidentTransactionDetailView(views.APIView):
    """API view for getting detailed information about a specific transaction."""
    
    def get(self, request, resident_id, transaction_id):
        """
        Get detailed information for a specific transaction.
        
        Path parameters:
        - resident_id: ID of the resident (for ownership verification)
        - transaction_id: ID of the transaction
        """
        try:
            transaction = get_resident_transaction_detail(resident_id, transaction_id)
            
            if not transaction:
                return Response(
                    {'success': False, 'error': 'Transaction not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            return Response({
                'success': True,
                'data': transaction
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = str(e)
            
            # Handle ownership error
            if 'not allowed to view' in error_message.lower():
                return Response(
                    {'success': False, 'error': error_message},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            return Response(
                {'success': False, 'error': error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CancelClearanceView(views.APIView):
    """API view for cancelling a clearance application."""
    
    def post(self, request, resident_id, application_id):
        """
        Cancel a clearance application.
        
        Path parameters:
        - resident_id: ID of the resident
        - application_id: ID of the application to cancel
        
        Payload (optional):
        {
            "reason": "Reason for cancellation"
        }
        """
        serializer = CancelClearanceSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            cancel_resident_clearance(
                application_id=application_id,
                resident_id=resident_id,
                reason=serializer.validated_data.get('reason')
            )
            
            return Response({
                'success': True,
                'message': 'Clearance application cancelled successfully'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            error_message = str(e)
            
            # Handle specific error cases
            if 'not found' in error_message.lower():
                return Response(
                    {'success': False, 'error': error_message},
                    status=status.HTTP_404_NOT_FOUND
                )
            elif 'only cancel your own' in error_message.lower():
                return Response(
                    {'success': False, 'error': error_message},
                    status=status.HTTP_403_FORBIDDEN
                )
            elif 'cannot cancel' in error_message.lower():
                return Response(
                    {'success': False, 'error': error_message},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            return Response(
                {'success': False, 'error': error_message},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )