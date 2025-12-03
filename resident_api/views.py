# Standard library imports
import json
import os
import re
import tempfile
from io import BytesIO

# Third-party imports
import pytesseract
import requests
import difflib
from dateutil import parser
from PIL import Image, ImageEnhance
import numpy as np
import cv2

# Django imports
from django.conf import settings
from django.db import connection

# Django REST framework imports
from rest_framework import viewsets, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from .utils.ocr_processing import validate_document_header
from rest_framework.permissions import AllowAny



# Local imports
from .serializers import (
    ResidentSerializer, SitioSerializer, CivilStatusSerializer, 
    EducationalAttainmentSerializer, ReligionSerializer, ResidentStatusSerializer, 
    ReligionCategorySerializer, ResidentRegistrationSerializer, AddressSerializer, IdentityDocTypeSerializer, OccupationSerializer, NationalitySerializer, EmploymentStatusSerializer,
)
from resident_profiling_module.models import (
    Resident, Sitio, CivilStatus, EducationalAttainment, Religion, 
    ResidentStatus, ReligionCategory, Address, ResidentIdDocument, IdentityDocType, Occupation, Nationality, EmploymentStatus,
)
from .supabase_storage import upload_file_to_supabase
from .services.profile_service import ProfileService
from .utils.database_helpers import (
    get_guardian_info, get_resident_profile, mobile_login, 
    update_resident_profile, change_personnel_password, resubmit_supporting_certificate, re_register_resident
)
from .utils.validation import find_mismatches
from .utils.ocr_processing import (
    run_ocr_and_extract_fields_switchable, extract_fields, 
    preprocess_image_for_ocr, clean_ocr_text
)
from .utils.text_processing import (
    normalize_name_for_comparison, are_names_equivalent, 
    normalize_for_comparison, clean_name_line
)

ENABLE_OCR_VALIDATION = getattr(settings, 'ENABLE_OCR_VALIDATION', True)

# --- VIEW CLASSES ---

class ResidentViewSet(viewsets.ModelViewSet):
    queryset = Resident.objects.all()
    serializer_class = ResidentSerializer

class CivilStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = CivilStatus.objects.all()
    serializer_class = CivilStatusSerializer

class EducationalAttainmentViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EducationalAttainment.objects.all()
    serializer_class = EducationalAttainmentSerializer

class SitioViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Sitio.objects.all()
    serializer_class = SitioSerializer

class ReligionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Religion.objects.all()
    serializer_class = ReligionSerializer

class ResidentStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ResidentStatus.objects.all()
    serializer_class = ResidentStatusSerializer

class ReligionCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = ReligionCategory.objects.all()
    serializer_class = ReligionCategorySerializer

class IdentityDocTypeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IdentityDocType.objects.all()
    serializer_class = IdentityDocTypeSerializer

class OccupationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Occupation.objects.all()
    serializer_class = OccupationSerializer

class NationalityViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Nationality.objects.all()
    serializer_class = NationalitySerializer

class EmploymentStatusViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = EmploymentStatus.objects.all()
    serializer_class = EmploymentStatusSerializer

class ResidentRegistrationView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        print(" POST /api/register/ called")
        print(f" [class ResidentRegistrationView] Request data keys: {list(request.data.keys())}")
        
        try:
            serializer = ResidentRegistrationSerializer(data=request.data, context={'request': request})
            
            if not serializer.is_valid():
                print(" Serializer is not valid")
                print("Errors:", serializer.errors)
                return Response({
                    'success': False,
                    'error': 'Validation failed',
                    'details': serializer.errors
                }, status=400)
            
            print(" Serializer is valid")
            resident = serializer.save()
            
            print(f" [class ResidentRegistrationView] Registration successful for resident_id: {resident.resident_id}")
            
            #  UPDATED RESPONSE FORMAT
            return Response({
                'success': True,
                'resident_id': resident.resident_id,
                'is_verified': resident.is_verified,
                'verification_status': {
                    'status': 'verified' if resident.is_verified else 'pending',
                    'message': 'Your account has been successfully verified.' if resident.is_verified else 'Your account is pending verification. Please wait for approval.',
                    'needs_wait': not resident.is_verified
                }
            }, status=201)
            
        except Exception as e:
            error_message = str(e)
            
            # ✅ Handle duplicate resident error (for both residents and non-residents)
            if "E5030" in error_message and ("resident with the same full name" in error_message or "non-resident with the same full name" in error_message):
                return Response({
                    'success': False,
                    'error': 'A person with this name and birthdate already exists in our system. Please check your information or contact support if this is an error.',
                    'error_code': 'DUPLICATE_PERSON'
                }, status=400)
            
            # Handle missing document type error
            elif "E5024" in error_message:
                return Response({
                    'success': False,
                    'error': 'Document type is required for registration.',
                    'error_code': 'MISSING_DOCUMENT_TYPE'
                }, status=400)

            
            # Generic error handling
            else:
                print(f" Unexpected error in registration: {e}")
                return Response({
                    'success': False,
                    'error': 'Registration failed. Please try again or contact support.',
                    'error_code': 'REGISTRATION_ERROR'
                }, status=500)


class ResidentIdDocumentOCRView(APIView):
    def get(self, request, pk):
        try:
            doc = ResidentIdDocument.objects.get(pk=pk)
            image = Image.open(BytesIO(doc.image_data))
            text = pytesseract.image_to_string(image)
            return Response({'extracted_text': text})
        except ResidentIdDocument.DoesNotExist:
            return Response({'error': 'Document not found'}, status=404)




class VerifyIdFieldsView(APIView):
    """
    Verify ID fields by comparing OCR results with user input
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        print("\n=== VerifyIdFieldsView START ===")
        
        try:
            registration_data = json.loads(request.data.get('registrationData', '{}'))
            id_image = request.FILES.get('id_image')
            doc_type = registration_data.get('document_type', '')
            verification_type = registration_data.get('verification_type', 'ID')
            
            print(f"DEBUG: Verifying document type: {doc_type}")
            print(f"DEBUG: Verification type: {verification_type}")
            print(f"DEBUG: Registration data: {registration_data}")
            
            if not id_image:
                return Response({
                    'verified': False,
                    'error_type': 'NO_IMAGE',
                    'message': 'No image provided'
                }, status=400)

            # ✅ FIXED: More specific document classification
            # Check for exact matches to avoid false positives
            doc_type_lower = doc_type.lower().strip()
            
            # Supporting documents - exact matches only
            is_supporting_doc = doc_type_lower in [
                'birth certificate',
                'voters certificate',  # Note: "voters certificate" not "voters id"
                "voter's certificate"
            ]
            
            # ID documents
            is_id_doc = not is_supporting_doc
            
            print(f"DEBUG: Document classification - Supporting: {is_supporting_doc}, ID: {is_id_doc}")
            print(f"DEBUG: Document type (normalized): '{doc_type_lower}'")

            # ✅ STEP 2: MANDATORY HEADER VALIDATION FOR ALL DOCUMENTS
            if doc_type and ENABLE_OCR_VALIDATION:
                print(f"DEBUG: Running header validation for document type: {doc_type}")
                id_image.seek(0)
                
                header_valid = validate_document_header(id_image, doc_type)
                print(f"DEBUG: Header validation result: {header_valid}")
                
                if not header_valid:
                    print(f"❌ Header validation FAILED for {doc_type}")
                    return Response({
                        'verified': False,
                        'error_type': 'DOCUMENT_TYPE_MISMATCH',
                        'user_friendly_message': f"This doesn't look like a {doc_type}. Please upload a clear photo of your {doc_type}.",
                        'message': f'Document header validation failed for {doc_type}'
                    }, status=200)
                
                print(f"✅ Header validation PASSED for {doc_type}")

            # ✅ STEP 3: For SUPPORTING documents, stop here (header check only)
            if is_supporting_doc:
                print(f"DEBUG: Supporting document - returning success after header check")
                
                # Run OCR just to extract fields (even if empty) for admin review
                id_image.seek(0)
                ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, registration_data)
                
                return Response({
                    'verified': True,
                    'status': 'match',
                    'message': 'Document verified successfully',
                    'extracted_fields': ocr_fields
                }, status=200)

            # ✅ STEP 4: For ID documents (including Voter's ID), proceed with FULL OCR validation
            print(f"DEBUG: ID document - proceeding with OCR validation")
            
            id_image.seek(0)
            ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, registration_data)
            print(f"DEBUG: OCR extracted fields: {ocr_fields}")

            # Check if OCR returned meaningful data
            ocr_first = (ocr_fields.get('first_name') or '').strip()
            ocr_last = (ocr_fields.get('last_name') or '').strip()

            print(f"DEBUG: OCR Names - First: '{ocr_first}', Last: '{ocr_last}'")
            print(f"DEBUG: User Names - First: '{registration_data.get('first_name')}', Last: '{registration_data.get('last_name')}'")

            # For ID documents, require OCR to extract names
            if not ocr_first and not ocr_last:
                return Response({
                    'verified': False,
                    'error_type': 'QUALITY_ISSUE',
                    'user_friendly_message': f"We couldn't read your {doc_type} clearly. Please retake the photo with better lighting and ensure all text is visible.",
                    'message': 'OCR could not extract readable names from the document'
                }, status=200)

            # Find mismatches between user input and OCR
            mismatches = find_mismatches(
                registration_data,
                ocr_fields,
                ['first_name', 'last_name', 'dob']
            )

            print(f"DEBUG: Comparison mismatches: {mismatches}")

            if mismatches:
                return Response({
                    'verified': False,
                    'error_type': 'MISMATCH',
                    'user_friendly_message': 'Some details don\'t match your ID. Please review and correct.',
                    'mismatches': mismatches
                }, status=200)

            # SUCCESS: Document verified
            return Response({
                'verified': True,
                'status': 'match',
                'message': 'Document verified successfully',
                'extracted_fields': ocr_fields
            }, status=200)

        except Exception as e:
            print(f"❌ ID verification error: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'verified': False,
                'error_type': 'SERVER_ERROR',
                'message': 'Server error during verification. Please try again.'
            }, status=500)
        
        finally:
            print("=== VerifyIdFieldsView END ===\n")




class VerifyGuardianIdFieldsView(APIView):
    """
    Verify guardian ID fields by comparing OCR results with guardian's stored information
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        print("\n=== VerifyGuardianIdFieldsView START ===")
        
        try:
            registration_data = json.loads(request.data.get('registrationData', '{}'))
            id_image = request.FILES.get('id_image')
            guardian_username = registration_data.get('guardian_username', '')
            doc_type = registration_data.get('document_type', '')
            
            print(f"DEBUG: Verifying guardian ID for username: {guardian_username}")
            print(f"DEBUG: Document type: {doc_type}")
            
            if not id_image:
                return Response({
                    'verified': False,
                    'error_type': 'NO_IMAGE',
                    'message': 'No image provided'
                }, status=400)

            if not guardian_username:
                return Response({
                    'verified': False,
                    'error_type': 'NO_GUARDIAN',
                    'message': 'Guardian username is required'
                }, status=400)

            # Get guardian info
            guardian_info = get_guardian_info(guardian_username)
            if not guardian_info:
                return Response({
                    'verified': False,
                    'error_type': 'GUARDIAN_NOT_FOUND',
                    'message': 'Guardian not found or not verified'
                }, status=400)

            guardian_resident_id, guardian_last_name, guardian_first_name, guardian_middle_name, guardian_suffix, guardian_dob = guardian_info
            print(f"DEBUG: Guardian info retrieved: {{'guardian_resident_id': {guardian_resident_id}, 'last_name': '{guardian_last_name}', 'first_name': '{guardian_first_name}', 'middle_name': '{guardian_middle_name}', 'suffix': '{guardian_suffix}', 'dob': '{guardian_dob}'}}")

            # ✅ FIXED: More specific document classification for guardian documents too
            doc_type_lower = doc_type.lower().strip()
            
            # Supporting documents - exact matches only
            is_supporting_doc = doc_type_lower in [
                'birth certificate',
                'voters certificate',  # Note: "voters certificate" not "voters id"
                "voter's certificate"
            ]
            
            # ID documents
            is_id_doc = not is_supporting_doc
            
            print(f"DEBUG: Guardian document classification - Supporting: {is_supporting_doc}, ID: {is_id_doc}")
            print(f"DEBUG: Document type (normalized): '{doc_type_lower}'")

            # ✅ STEP 2: MANDATORY HEADER VALIDATION FOR ALL GUARDIAN DOCUMENTS
            if doc_type and ENABLE_OCR_VALIDATION:
                print(f"DEBUG: Running header validation for guardian document: {doc_type}")
                id_image.seek(0)
                
                header_valid = validate_document_header(id_image, doc_type)
                print(f"DEBUG: Header validation result: {header_valid}")
                
                if not header_valid:
                    print(f"❌ Guardian header validation FAILED for {doc_type}")
                    return Response({
                        'verified': False,
                        'error_type': 'DOCUMENT_TYPE_MISMATCH',
                        'user_friendly_message': f"This doesn't look like a {doc_type}. Please upload a clear photo of your guardian's {doc_type}.",
                        'message': f'Document header validation failed for {doc_type}'
                    }, status=200)
                
                print(f"✅ Guardian header validation PASSED for {doc_type}")

            # ✅ STEP 3: For GUARDIAN SUPPORTING documents, stop here (header check only)
            if is_supporting_doc:
                print(f"DEBUG: Guardian supporting document - returning success after header check")
                
                guardian_data_for_ocr = {
                    'first_name': guardian_first_name,
                    'last_name': guardian_last_name,
                    'middle_name': guardian_middle_name or '',
                    'dob': str(guardian_dob) if guardian_dob else ''
                }
                
                id_image.seek(0)
                ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, guardian_data_for_ocr)
                
                return Response({
                    'verified': True,
                    'status': 'match',
                    'message': 'Guardian document verified successfully',
                    'extracted_fields': ocr_fields,
                    'guardian_verified_info': {
                        'first_name': guardian_first_name,
                        'last_name': guardian_last_name,
                        'middle_name': guardian_middle_name or '',
                        'dob': str(guardian_dob) if guardian_dob else ''
                    }
                }, status=200)

            # ✅ STEP 4: For GUARDIAN ID documents, proceed with FULL OCR validation
            print(f"DEBUG: Guardian ID document - proceeding with OCR validation")
            
            guardian_data_for_ocr = {
                'first_name': guardian_first_name,
                'last_name': guardian_last_name,
                'middle_name': guardian_middle_name or '',
                'dob': str(guardian_dob) if guardian_dob else ''
            }

            id_image.seek(0)
            ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, guardian_data_for_ocr)
            print(f"DEBUG: OCR extracted fields: {ocr_fields}")

            # Check if OCR returned meaningful data
            ocr_first = (ocr_fields.get('first_name') or '').strip()
            ocr_last = (ocr_fields.get('last_name') or '').strip()

            print(f"DEBUG: OCR Names - First: '{ocr_first}', Last: '{ocr_last}'")
            print(f"DEBUG: Guardian Names - First: '{guardian_first_name}', Last: '{guardian_last_name}'")

            # For guardian ID documents, require OCR to extract names
            if not ocr_first and not ocr_last:
                return Response({
                    'verified': False,
                    'error_type': 'QUALITY_ISSUE',
                    'user_friendly_message': f"We couldn't read your guardian's {doc_type} clearly. Please retake the photo with better lighting and ensure all text is visible.",
                    'message': 'OCR could not extract readable names from the document'
                }, status=200)

            # Find mismatches between OCR and guardian info
            mismatches = find_mismatches(
                guardian_data_for_ocr,
                ocr_fields,
                ['first_name', 'last_name', 'dob']
            )

            print(f"DEBUG: Comparison mismatches: {mismatches}")

            if mismatches:
                return Response({
                    'verified': False,
                    'error_type': 'MISMATCH',
                    'user_friendly_message': 'The document information doesn\'t match your guardian\'s registered details.',
                    'mismatches': mismatches,
                    'guardian_verified_info': {
                        'first_name': guardian_first_name,
                        'last_name': guardian_last_name,
                        'middle_name': guardian_middle_name or '',
                        'dob': str(guardian_dob) if guardian_dob else ''
                    }
                }, status=200)

            # SUCCESS: Guardian document verified
            return Response({
                'verified': True,
                'status': 'match',
                'message': 'Guardian document verified successfully',
                'extracted_fields': ocr_fields,
                'guardian_verified_info': {
                    'first_name': guardian_first_name,
                    'last_name': guardian_last_name,
                    'middle_name': guardian_middle_name or '',
                    'dob': str(guardian_dob) if guardian_dob else ''
                }
            }, status=200)

        except Exception as e:
            print(f"❌ Guardian ID verification error: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'verified': False,
                'error_type': 'SERVER_ERROR',
                'message': 'Server error during verification. Please try again.'
            }, status=500)
        
        finally:
            print("=== VerifyGuardianIdFieldsView END ===\n")
            
#Refactored
class VerifyGuardianView(APIView):
    """Verify guardian username."""
    
    def post(self, request):
        try:
            guardian_username = request.data.get('guardian_username', '').strip()
            
            if not guardian_username:
                return Response({
                    'exists': False,
                    'message': 'Guardian username is required'
                }, status=400)
            
            guardian_data = get_guardian_info(guardian_username)
            
            if guardian_data:
                return Response({
                    'exists': True,
                    'message': 'Guardian found and verified',
                    'guardian_verified': True
                }, status=200)
            else:
                return Response({
                    'exists': False,
                    'message': 'Guardian username not found or guardian is not verified'
                }, status=200)
                        
        except Exception as e:
            print(f"Guardian verification error: {str(e)}")
            return Response({
                'exists': False,
                'error': f'Verification failed: {str(e)}'
            }, status=500)


# MOBILE LOGIN
# Refactored
class MobileLoginView(APIView):
    """Handle mobile login."""
    
    def post(self, request):
        try:
            username = request.data.get('username', '').strip()
            password = request.data.get('password', '')
            
            if not username or not password:
                return Response({
                    'success': False,
                    'message': 'Username and password are required'
                }, status=400)
            
            result = mobile_login(username, password)
            
            if result['status'] == 'success':
              

                if result.get('account_type') == 'resident' and not result.get('is_verified', True):
                    response_data = {
                        'success': False,
                        'status': 'not_verified',
                        'message': 'Your account is pending verification. Please wait for approval.',
                        'account_type': result.get('account_type'),
                        'username': result.get('username')
                    }
                    # Only add rejection_action if present
                    if result.get('rejection_action'):
                        response_data['rejection_action'] = result['rejection_action']
                        response_data['review_notes'] = result.get('review_notes')
                        # If resubmission, add identity_doc_type_id
                        if result['rejection_action'] == 'RESUBMISSION' and result.get('identity_doc_type_id'):
                            response_data['identity_doc_type_id'] = result['identity_doc_type_id']
                            response_data['identity_doc_type_name'] = result.get('identity_doc_type_name')
                    # Optionally add resident_id if present
                    if result.get('resident_id'):
                        response_data['resident_id'] = result['resident_id']
                    return Response(response_data, status=200)

                return Response({
                    'success': True,
                    'status': 'success',
                    'account_type': result['account_type'],
                    'user_id': result.get('personnel_id') or result.get('resident_id'),
                    'username': result['username'],
                    'role_name': result.get('role_name'),
                    'role_id': result.get('role_id'),
                    'session_token': result['session_token'],  
                    'message': 'Login successful'
                }, status=200)
            else:
               
                return Response({
                    'success': False,
                    'status': result['status'],
                    'message': result['message']
                }, status=401)
                
        except Exception as e:
            print(f"Login error: {str(e)}")
            return Response({
                'success': False,
                'message': f'Login failed: {str(e)}'
            }, status=500)

        

# MOBILE RESIDENT USER PROFILE
# Refactored

class ResidentProfileView(APIView):
    """Get resident profile."""
    
    def get(self, request, resident_id):
        try:
            result = get_resident_profile(resident_id)
            
            if result:
                return Response({
                    'success': True,
                    'profile': result
                }, status=200)
            else:
                return Response({
                    'success': False,
                    'message': 'Profile not found'
                }, status=404)
                
        except Exception as e:
            print(f"Profile fetch error: {str(e)}")
            return Response({
                'success': False,
                'message': 'Failed to fetch profile'
            }, status=500)
        
# MOBILE UPDATE PROFILE
# Refactored
class UpdateResidentProfileView(APIView):
    """Update resident profile using ProfileService."""
    parser_classes = (MultiPartParser, FormParser)
    
    def post(self, request, resident_id):
        print(f"Updating profile for resident_id: {resident_id}")
        
        # Extract profile image if provided
        profile_image_file = request.FILES.get('profile_image')
        
        # Use ProfileService to handle all the complex logic
        result = ProfileService.update_resident_profile(
            resident_id=resident_id,
            form_data=request.data,
            profile_image_file=profile_image_file
        )
        
        # Return response based on service result
        return Response({
            'success': result['success'],
            'message': result['message'],
            'profile_image_url': result.get('profile_image_url')
        }, status=result['status_code'])



# Refactored
class ChangePersonnelPasswordView(APIView):
    """Change personnel password."""
    
    def post(self, request):
        try:
            personnel_id = request.data.get('personnel_id')
            old_password = request.data.get('old_password')
            new_password = request.data.get('new_password')
            
            if not all([personnel_id, old_password, new_password]):
                return Response({
                    'success': False,
                    'message': 'Missing required fields'
                }, status=400)
            
            # Use database helper function
            result = change_personnel_password(personnel_id, old_password, new_password)
            
            return Response({
                'success': True,
                'message': 'Password changed successfully'
            }, status=200)
                
        except Exception as e:
            print(f"Password change error: {str(e)}")
            return Response({
                'success': False,
                'message': str(e)
            }, status=500)
        

class ResubmitSupportingCertificateView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            resident_id = int(request.data.get('resident_id'))
            identity_doc_type_id = int(request.data.get('identity_doc_type_id'))
            note = request.data.get('note', 'resubmit photo')
            id_image = request.FILES.get('id_image')

            # OCR header validation
            from resident_profiling_module.models import IdentityDocType
            doc_type_obj = IdentityDocType.objects.get(identity_doc_type_id=identity_doc_type_id)
            expected_doc_type = doc_type_obj.name
            if not validate_document_header(id_image, expected_doc_type):
                return Response({'success': False, 'message': f'Uploaded image does not match expected document type: {expected_doc_type}.'}, status=400)

            # Upload to Supabase
            file_path = upload_file_to_supabase(id_image, folder='id-documents')

            # Call SQL function
            result = resubmit_supporting_certificate(resident_id, identity_doc_type_id, file_path, note)
            return Response({'success': True, 'message': result})
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)
        
class ReRegisterResidentView(APIView):
    def post(self, request):
        try:
            resident_id = int(request.data.get('resident_id'))
            # Only the owner can trigger, so performed_by = resident_id
            result = re_register_resident(resident_id, performed_by=resident_id)
            return Response({'success': True, 'message': result})
        except Exception as e:
            return Response({'success': False, 'message': str(e)}, status=400)
        

class CheckUsernameAvailabilityView(APIView):
    """Check if username is available."""
    
    def post(self, request):
        try:
            username = request.data.get('username', '').strip()
            
            if not username:
                return Response({
                    'available': False,
                    'message': 'Username is required'
                }, status=400)
            
            # Call the database function
            with connection.cursor() as cursor:
                cursor.execute("SELECT is_username_available(%s)", [username])
                result = cursor.fetchone()[0]
                
                # result is 1 if available, 0 if taken
                is_available = result == 1
                
                return Response({
                    'available': is_available,
                    'message': 'Username is available' if is_available else 'Username is already taken'
                }, status=200)
                
        except Exception as e:
            print(f"Username check error: {str(e)}")
            return Response({
                'available': False,
                'message': 'Failed to check username availability'
            }, status=500)
        

def _to_int(value, default=None):
    """Safe int conversion with default fallback."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _dictfetchall(cursor):
    """Return all rows from a cursor as a list of dicts."""
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


class LatestResidentAnnouncements(APIView):
    """
    GET /api/mobile/announcements/latest/

    Query params:
      - limit (int, default=3)
      - offset (int, default=0)
      - q (text, optional)         => search text applied to title/details
      - date_from (YYYY-MM-DD, optional)
      - date_to   (YYYY-MM-DD, optional)

    Uses:
      get_latest_announcements_for_residents(
        p_limit,
        p_offset,
        p_q,
        p_date_from,
        p_date_to
      )

    Returns (example):
      [
        {
          "id": 1,
          "title": "Header title",
          "text": "Details text...",
          "image_path": "/path/to/image.png",
          "date": "2025-07-25"
        },
        ...
      ]
    """
    permission_classes = [AllowAny]  # change to IsAuthenticated for mobile later

    def get(self, request, *args, **kwargs):
        limit = _to_int(request.query_params.get("limit"), 3)
        offset = _to_int(request.query_params.get("offset"), 0)
        q = request.query_params.get("q") or None
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      announcement_id,
                      header_title,
                      details,
                      announcement_image_path,
                      created_date
                    FROM get_latest_announcements_for_residents(%s, %s, %s, %s, %s)
                    """,
                    [limit, offset, q, date_from, date_to],
                )
                rows = _dictfetchall(cursor)

            data = []
            for row in rows:
                created_date = row.get("created_date")
                data.append(
                    {
                        "id": row.get("announcement_id"),
                        "title": row.get("header_title"),
                        "text": row.get("details"),
                        "image_path": row.get("announcement_image_path"),
                        "date": created_date.isoformat() if created_date else None,
                    }
                )

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "error": "E7100",
                    "message": "Failed to fetch latest resident announcements.",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ResidentAnnouncementsList(APIView):
    """
    GET /mobile/announcements/

    Query params:
      - q (text, optional)
      - date_from (YYYY-MM-DD, optional)
      - date_to   (YYYY-MM-DD, optional)
      - sort (text, optional)            => date_asc / date_desc / title_asc / title_desc
      - limit (int, default=50)
      - offset (int, default=0)
      - created_by (int, optional)

    Returns:
      [
        {
          "id": 1,
          "title": "Header title",
          "text": "Details text...",
          "image_path": "/path/to/image.png",
          "date": "2025-07-25",
          "audience": "resident" | "both"
        },
        ...
      ]
    """
    permission_classes = [AllowAny]  # change later if needed

    def get(self, request, *args, **kwargs):
        q = request.query_params.get("q") or None
        date_from = request.query_params.get("date_from") or None
        date_to = request.query_params.get("date_to") or None
        sort = request.query_params.get("sort") or "date_desc"
        limit = _to_int(request.query_params.get("limit"), 50)
        offset = _to_int(request.query_params.get("offset"), 0)

        created_by_raw = request.query_params.get("created_by")
        created_by = _to_int(created_by_raw) if created_by_raw is not None else None

        # ❗ Do NOT force audience here – we will filter outside
        p_audience = None

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                      g.announcement_id,
                      g.header_title,
                      a.details,
                      a.announcement_image_path,
                      g.created_date,
                      g.audience
                    FROM get_all_announcement(%s, %s, %s, %s, %s, %s, %s, %s) AS g
                    JOIN announcement a
                      ON a.announcement_id = g.announcement_id
                    WHERE g.audience IN ('resident','both')
                    """,
                    [
                        q,
                        date_from,
                        date_to,
                        created_by,
                        sort,
                        limit,
                        offset,
                        p_audience,  # NULL => no audience filter inside the function
                    ],
                )
                rows = _dictfetchall(cursor)

            data = []
            for row in rows:
                created_date = row.get("created_date")
                data.append(
                    {
                        "id": row.get("announcement_id"),
                        "title": row.get("header_title"),
                        "text": row.get("details"),
                        "image_path": row.get("announcement_image_path"),
                        "date": created_date.isoformat() if created_date else None,
                        "audience": row.get("audience"),
                    }
                )

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "error": "E7110",
                    "message": "Failed to fetch resident announcements list.",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )



def _to_int(value, default=None):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default

def _dictfetchall(cursor):
    desc = cursor.description
    if not desc:
        return []
    columns = [col[0] for col in desc]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

class OwnerBusinessesMobileView(APIView):
    """
    GET /api/mobile/businesses/?owner_id=<resident_id>&q=&status=&limit=&offset=

    Uses get_all_businesses_mobile_by_owner(p_owner_id, p_search, p_status, p_limit, p_offset)
    and returns a list of businesses owned by the resident.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        owner_id_raw = request.query_params.get("owner_id")
        owner_id = _to_int(owner_id_raw)

        if owner_id is None:
            return Response(
                {
                    "error": "M9001",
                    "message": "owner_id (resident_id) is required as a query parameter.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        q = request.query_params.get("q") or None
        status_filter = request.query_params.get("status") or None
        limit = _to_int(request.query_params.get("limit"), 50)
        offset = _to_int(request.query_params.get("offset"), 0)

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM get_all_businesses_mobile_by_owner(%s, %s, %s, %s, %s);
                    """,
                    [owner_id, q, status_filter, limit, offset],
                )
                rows = _dictfetchall(cursor)

            data = []
            for row in rows:
                updated_at = row.get("updated_at")
                data.append(
                    {
                        "business_id": row.get("business_id"),
                        "business_name": row.get("business_name"),
                        "business_status_name": row.get("business_status_name"),
                        "business_type_name": row.get("business_type_name"),
                        "ownership_name": row.get("ownership_name"),
                        "clearance_category_name": row.get("clearance_category_name"),
                        "reg_number": row.get("reg_number"),
                        "total_gross_income": row.get("total_gross_income"),
                        "address_id": row.get("address_id"),
                        "full_address": row.get("full_address"),
                        "updated_at": updated_at.isoformat() if updated_at else None,
                    }
                )

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            return Response(
                {
                    "error": "M9199",
                    "message": "Failed to load businesses for owner.",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class SpecificBusinessMobileView(APIView):
    """
    GET /api/mobile/businesses/<business_id>/?owner_id=<resident_id>

    Uses get_specific_business_mobile_by_owner(p_owner_id, p_business_id)
    and returns detailed information about a specific business owned by the resident.
    """
    permission_classes = [AllowAny]

    def get(self, request, business_id, *args, **kwargs):
        owner_id_raw = request.query_params.get("owner_id")
        owner_id = _to_int(owner_id_raw)
        business_id_int = _to_int(business_id)

        if owner_id is None:
            return Response(
                {
                    "error": "M9011",
                    "message": "owner_id (resident_id) is required as a query parameter.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        if business_id_int is None:
            return Response(
                {
                    "error": "M9012",
                    "message": "business_id is required.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT *
                    FROM get_specific_business_mobile_by_owner(%s, %s);
                    """,
                    [owner_id, business_id_int],
                )
                rows = _dictfetchall(cursor)

            if not rows:
                return Response(
                    {
                        "error": "M9013",
                        "message": f"Business {business_id_int} not found for owner {owner_id}.",
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )

            row = rows[0]
            updated_at = row.get("updated_at")
            clearance_date_issued = row.get("clearance_date_issued")

            data = {
                "business_id": row.get("business_id"),
                "business_name": row.get("business_name"),
                "nature_of_business": row.get("nature_of_business"),
                "total_gross_income": row.get("total_gross_income"),
                "reg_number": row.get("reg_number"),
                "clearance_date_issued": clearance_date_issued.isoformat() if clearance_date_issued else None,
                "status": row.get("status"),
                "business_type": row.get("business_type"),
                "ownership": row.get("ownership"),
                "clearance_category": row.get("clearance_category"),
                "owner_id": row.get("owner_id"),
                "owner_name": row.get("owner_name"),
                "address_id": row.get("address_id"),
                "address": row.get("address"),
                "updated_at": updated_at.isoformat() if updated_at else None,
                "created_by": row.get("created_by"),
            }

            return Response(data, status=status.HTTP_200_OK)

        except Exception as e:
            error_msg = str(e)
            # Check if it's a database exception with our custom error code
            if "M9013" in error_msg:
                return Response(
                    {
                        "error": "M9013",
                        "message": error_msg,
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {
                    "error": "M9299",
                    "message": "Failed to load business details.",
                    "detail": error_msg,
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )