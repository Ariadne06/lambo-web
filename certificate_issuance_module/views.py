from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .models import DocumentType, ClearancePurpose, ApplicationStatus
from .serializers import (
    DocumentTypeSerializer, ClearancePurposeSerializer, ApplicationStatusSerializer,
    FeeQuoteRequestSerializer, CertificateApplicationSerializer, ApplicationListSerializer,
    ApplicationDetailSerializer, PendingApplicationSerializer, ReviewApplicationSerializer,
    RecordPaymentSerializer, MarkCompletedSerializer
)
from .services.certificate_service import CertificateService


# ViewSets for lookup data - following household_module pattern
class DocumentTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """Document types viewset - matching SQL schema"""
    queryset = DocumentType.objects.all()
    serializer_class = DocumentTypeSerializer


class ClearancePurposeViewSet(viewsets.ReadOnlyModelViewSet):
    """Clearance purposes viewset - matching SQL schema"""
    queryset = ClearancePurpose.objects.all()
    serializer_class = ClearancePurposeSerializer


class ApplicationStatusViewSet(viewsets.ReadOnlyModelViewSet):
    """Application status viewset - matching SQL schema"""
    queryset = ApplicationStatus.objects.all()
    serializer_class = ApplicationStatusSerializer


# APIViews for complex operations - following household_module pattern
class CertificateDataView(APIView):
    """Get certificate form data - using SQL functions"""
    
    def get(self, request):
        print("GET /api/certificate-data/ called")
        
        try:
            # Get document types and clearance purposes using SQL functions
            document_types = CertificateService.get_all_document_types()
            clearance_purposes = CertificateService.get_all_clearance_purposes()
            
            return Response({
                'success': True,
                'data': {
                    'document_types': document_types,
                    'clearance_purposes': clearance_purposes
                }
            }, status=200)
            
        except Exception as e:
            print(f"Certificate data fetch error: {str(e)}")
            return Response({
                'success': False,
                'message': f'Failed to fetch certificate data: {str(e)}'
            }, status=500)


class FeeQuoteView(APIView):
    """Calculate certificate fee - using SQL function resident_quote_fee()"""
    
    def post(self, request):
        print("POST /api/fee-quote/ called")
        
        try:
            # Validate request data
            serializer = FeeQuoteRequestSerializer(data=request.data)
            if not serializer.is_valid():
                return Response({
                    'success': False,
                    'message': 'Invalid data provided',
                    'errors': serializer.errors
                }, status=400)
            
            # Extract validated data
            data = serializer.validated_data
            resident_id = data['resident_id']
            document_type_id = data['document_type_id']
            business_id = data.get('business_id')
            clearance_purpose_id = data.get('clearance_purpose_id')
            
            print(f"Calculating fee for resident_id: {resident_id}, document_type_id: {document_type_id}")
            
            # Calculate fee using service
            fee = CertificateService.calculate_fee(
                resident_id=resident_id,
                document_type_id=document_type_id,
                business_id=business_id,
                clearance_purpose_id=clearance_purpose_id
            )
            
            return Response({
                'success': True,
                'data': {
                    'fee': fee,
                    'currency': 'PHP',
                    'document_type_id': document_type_id,
                    'clearance_purpose_id': clearance_purpose_id
                }
            }, status=200)
            
        except Exception as e:
            print(f"Fee calculation error: {str(e)}")
            
            # Extract user-friendly error messages from SQL exceptions
            error_message = str(e)
            if 'P6021:' in error_message:
                error_message = 'Invalid document type selected.'
            elif 'P6022:' in error_message:
                error_message = 'Barangay Clearance requires a purpose to be selected.'
            elif 'P6023:' in error_message:
                error_message = 'Invalid clearance purpose selected.'
            elif 'Quote not allowed' in error_message:
                error_message = 'You can only request renewal for your own business.'
            
            return Response({
                'success': False,
                'message': error_message
            }, status=400)


class SubmitApplicationView(APIView):
    """Submit certificate application - using SQL function resident_create_application()"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request):
        print("POST /api/submit-application/ called")
        print(f"Request data keys: {list(request.data.keys())}")
        
        try:
            serializer = CertificateApplicationSerializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                print("Serializer is not valid")
                print("Errors:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=400)
            
            print("Serializer is valid")
            application = serializer.save()
            
            print(f"Certificate application successful for ID: {application.application_id}")
            
            return Response({
                'success': True,
                'message': 'Certificate application submitted successfully',
                'data': {
                    'application_id': application.application_id
                }
            }, status=201)
            
        except Exception as e:
            print(f"Unexpected error in application submission: {e}")
            
            # Extract user-friendly error messages from SQL exceptions
            error_message = str(e)
            if 'P6004:' in error_message:
                error_message = 'Invalid document type selected.'
            elif 'P6005:' in error_message:
                error_message = 'New Business Clearance must be requested at the barangay office.'
            elif 'P6007:' in error_message:
                error_message = 'You can only request renewal for your own business.'
            elif 'P6024:' in error_message:
                error_message = 'Barangay Clearance requires a purpose to be selected.'
            
            return Response({
                'success': False,
                'error': error_message,
                'error_code': 'APPLICATION_SUBMISSION_ERROR'
            }, status=500)


class ResidentApplicationsView(APIView):
    """Get applications for resident - direct SQL query"""
    
    def get(self, request, resident_id):
        print(f"GET /api/resident/{resident_id}/applications/ called")
        
        try:
            applications = CertificateService.get_applications_for_resident(resident_id)
            
            # Serialize the data
            serializer = ApplicationListSerializer(applications, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=200)
            
        except Exception as e:
            print(f"Error fetching resident applications: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ApplicationDetailView(APIView):
    """Get application details - direct SQL query"""
    
    def get(self, request, application_id):
        print(f"GET /api/application/{application_id}/details/ called")
        
        try:
            application = CertificateService.get_application_by_id(application_id)
            
            if not application:
                return Response({
                    'success': False,
                    'message': 'Application not found'
                }, status=404)
            
            # Serialize the data
            serializer = ApplicationDetailSerializer(application)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=200)
            
        except Exception as e:
            print(f"Error fetching application details: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PendingApplicationsView(APIView):
    """Get pending applications for personnel - direct SQL query"""
    
    def get(self, request):
        print("GET /api/pending-applications/ called")
        
        try:
            applications = CertificateService.get_all_pending_applications()
            
            # Serialize the data
            serializer = PendingApplicationSerializer(applications, many=True)
            
            return Response({
                'success': True,
                'data': serializer.data
            }, status=200)
            
        except Exception as e:
            print(f"Error fetching pending applications: {e}")
            return Response({
                'success': False,
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ReviewApplicationView(APIView):
    """Secretary review application - using SQL function secretary_review_application()"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, application_id):
        print(f"POST /api/application/{application_id}/review/ called")
        
        try:
            serializer = ReviewApplicationSerializer(data=request.data)
            
            if not serializer.is_valid():
                print("Review serializer is not valid")
                print("Errors:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=400)
            
            # Get personnel_id from authenticated user (adjust based on your auth system)
            personnel_id = request.user.personnel.personnel_id if hasattr(request.user, 'personnel') else 1
            
            decision = serializer.validated_data['decision']
            review_notes = serializer.validated_data.get('review_notes')
            
            print(f"Reviewing application {application_id} with decision: {decision}")
            
            result = CertificateService.review_application(
                application_id, personnel_id, decision, review_notes
            )
            
            return Response({
                'success': True,
                'message': f'Application {decision.lower()}',
                'data': {
                    'application_id': application_id,
                    'decision': decision
                }
            }, status=200)
            
        except Exception as e:
            print(f"Unexpected error in application review: {e}")
            
            # Extract user-friendly error messages from SQL exceptions
            error_message = str(e)
            if 'P6010:' in error_message:
                error_message = 'Application is not in pending status.'
            elif 'P6011:' in error_message:
                error_message = 'Invalid decision. Use FOR_PAYMENT or REJECT.'
            
            return Response({
                'success': False,
                'error': error_message,
                'error_code': 'APPLICATION_REVIEW_ERROR'
            }, status=500)


class RecordPaymentView(APIView):
    """Treasurer record payment - using SQL function treasurer_record_payment_and_approve()"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, application_id):
        print(f"POST /api/application/{application_id}/payment/ called")
        
        try:
            serializer = RecordPaymentSerializer(data=request.data)
            
            if not serializer.is_valid():
                print("Payment serializer is not valid")
                print("Errors:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=400)
            
            # Get personnel_id from authenticated user (adjust based on your auth system)
            personnel_id = request.user.personnel.personnel_id if hasattr(request.user, 'personnel') else 1
            
            document_type_id = serializer.validated_data['document_type_id']
            amount = serializer.validated_data['amount']
            or_number = serializer.validated_data['or_number']
            extra_amount = serializer.validated_data.get('extra_amount', 0)
            
            print(f"Recording payment for application {application_id}")
            
            payment_id = CertificateService.record_payment_and_approve(
                application_id, personnel_id, document_type_id, amount, or_number, extra_amount
            )
            
            if not payment_id:
                return Response({
                    'success': False,
                    'error': 'Failed to record payment'
                }, status=500)
            
            return Response({
                'success': True,
                'message': 'Payment recorded and application approved',
                'data': {
                    'payment_id': payment_id,
                    'application_id': application_id
                }
            }, status=200)
            
        except Exception as e:
            print(f"Unexpected error in payment recording: {e}")
            
            # Extract user-friendly error messages from SQL exceptions
            error_message = str(e)
            if 'P6014:' in error_message:
                error_message = 'Application must be in For Payment status.'
            elif 'P6015:' in error_message:
                error_message = 'Payment amount does not match expected amount.'
            
            return Response({
                'success': False,
                'error': error_message,
                'error_code': 'PAYMENT_RECORDING_ERROR'
            }, status=500)


class MarkCompletedView(APIView):
    """Secretary mark application completed - using SQL function secretary_mark_completed()"""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, application_id):
        print(f"POST /api/application/{application_id}/complete/ called")
        
        try:
            serializer = MarkCompletedSerializer(data=request.data)
            
            if not serializer.is_valid():
                print("Complete serializer is not valid")
                print("Errors:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=400)
            
            # Get personnel_id from authenticated user (adjust based on your auth system)
            personnel_id = request.user.personnel.personnel_id if hasattr(request.user, 'personnel') else 1
            
            remarks = serializer.validated_data.get('remarks')
            
            print(f"Marking application {application_id} as completed")
            
            result = CertificateService.mark_application_completed(
                application_id, personnel_id, remarks
            )
            
            return Response({
                'success': True,
                'message': 'Application marked as completed',
                'data': {
                    'application_id': application_id
                }
            }, status=200)
            
        except Exception as e:
            print(f"Unexpected error in marking completed: {e}")
            
            # Extract user-friendly error messages from SQL exceptions
            error_message = str(e)
            if 'P7001:' in error_message:
                error_message = 'Application not found.'
            elif 'P7002:' in error_message:
                error_message = 'Application must be approved before marking as completed.'
            
            return Response({
                'success': False,
                'error': error_message,
                'error_code': 'MARK_COMPLETED_ERROR'
            }, status=500)