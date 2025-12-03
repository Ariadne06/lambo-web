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



# class VerifyIdFieldsView(APIView):
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request):
   
#         try:
#             registration_data = json.loads(request.data.get('registrationData', '{}'))
#             id_image = request.FILES.get('id_image')
#             doc_type = registration_data.get('document_type', None)
            
#             if not id_image:
#                 return Response({'status': 'error', 'message': 'No image provided'}, status=400)

#             # --- SUPPORTING DOCS HEADER CHECK ---
#             # If this is a supporting document, only check the header/title
#             if doc_type and any(x in doc_type.lower() for x in ['birth', 'voter']):
#                 # Only check header/title for supporting docs
#                 header_ok = validate_document_header(id_image, doc_type)
#                 if not header_ok:
#                     return Response({
#                         'status': 'mismatch',
#                         'mismatches': {
#                             'header': {
#                                 'user': doc_type,
#                                 'ocr': 'Header/title not found in image'
#                             }
#                         }
#                     }, status=200)

#                 # If header is OK, you can skip field comparison and return match
#                 return Response({'status': 'match'})

#             # Extract fields using improved logic
#             ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, registration_data)
            
#             if doc_type and 'umid' in doc_type.lower():
#                 # Simple UMID fix: swap first and last names
#                 temp_first = ocr_fields.get('first_name', '')
#                 temp_last = ocr_fields.get('last_name', '')
#                 ocr_fields['first_name'] = temp_last
#                 ocr_fields['last_name'] = temp_first
#                 print(f"DEBUG: UMID name swap applied - First: '{temp_last}', Last: '{temp_first}'")

#             print('DEBUG: registration_data:', registration_data)
#             print('DEBUG: ocr_fields:', ocr_fields)
            
#             mismatches = {}

#             # Compare fields with improved logic
#             for key in ['first_name', 'last_name', 'dob']:
#                 reg_val = registration_data.get(key, '')
#                 ocr_val = ocr_fields.get(key, '')
#                 print(f'DEBUG: Comparing field "{key}": user="{reg_val}" ocr="{ocr_val}"')
                
#                 if key in ['first_name', 'last_name']:
#                     # Use improved name comparison
#                     if not are_names_equivalent(reg_val, ocr_val):
#                         mismatches[key] = {
#                             'user': reg_val,
#                             'ocr': ocr_val
#                         }
#                 else:
#                     # For non-name fields (like DOB), use exact comparison
#                     if normalize_for_comparison(reg_val) != normalize_for_comparison(ocr_val):
#                         mismatches[key] = {
#                             'user': reg_val,
#                             'ocr': ocr_val
#                         }
            
#             print('DEBUG: mismatches:', mismatches)
            
#             if mismatches:
#                 # return Response({'status': 'mismatch', 'mismatches': mismatches})
#                 return Response({
#                 'verified': False,
#                 'error_type': 'MISMATCH',
#                 'user_friendly_message': 'Some details don\'t match your ID. Please review and correct.',
#                 'action_required': 'EDIT_OR_RETAKE',
#                 'mismatches': mismatches,  # Keep for debugging
#                 }, status=status.HTTP_200_OK)
#             return Response({'status': 'match'})

#         except Exception as e:
#             print(f"Verification failed with error: {e}")
#             return Response({'status': 'error', 'message': str(e)}, status=500)

class VerifyIdFieldsView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        print("\n=== VerifyIdFieldsView START ===")
        
        try:
            registration_data = json.loads(request.data.get('registrationData', '{}'))
            id_image = request.FILES.get('id_image')
            doc_type = registration_data.get('document_type', None)
            verification_type = registration_data.get('verification_type', 'ID')
            
            print(f"[VerifyIdFieldsView] Document type: {doc_type}")
            print(f"[VerifyIdFieldsView] Verification type: {verification_type}")
            print(f"[VerifyIdFieldsView] Registration data: {registration_data}")
            
            if not id_image:
                return Response({
                    'verified': False,
                    'error_type': 'MISSING_IMAGE',
                    'message': 'No image file provided'
                }, status=400)

            # ============================================
            # STEP 1: HEADER/DOCUMENT TYPE VALIDATION
            # (Applies to ALL documents - both ID and Supporting)
            # ============================================
            if doc_type and ENABLE_OCR_VALIDATION:
                print(f"[VerifyIdFieldsView] Running header validation for document type: {doc_type}")
                
                # Reset file pointer before reading
                id_image.seek(0)
                
                header_valid, header_msg = validate_document_header(
                    BytesIO(id_image.read()), 
                    doc_type
                )
                
                print(f"[VerifyIdFieldsView] Header validation result: {header_valid}, message: {header_msg}")
                
                if not header_valid:
                    # Wrong document type uploaded
                    return Response({
                        'verified': False,
                        'status': 'mismatch',
                        'error_type': 'DOCUMENT_TYPE_MISMATCH',
                        'message': header_msg,
                        'user_friendly_message': f'This does not appear to be a valid {doc_type}. Please upload the correct document type.',
                        'action_required': 'RETAKE',
                        'mismatches': {
                            'header': {
                                'user': doc_type,
                                'ocr': 'Header/title not found in image'
                            }
                        }
                    }, status=200)

            # ============================================
            # STEP 2: SUPPORTING DOCUMENTS - STOP HERE
            # ============================================
            if verification_type == 'SUPPORTING':
                # Supporting documents only need header check - no field matching
                print("[VerifyIdFieldsView] Supporting document header validated - APPROVED for manual review")
                return Response({
                    'verified': True,
                    'status': 'match',
                    'message': 'Supporting document validated successfully. Pending manual review.',
                    'extracted_fields': {}
                }, status=200)

            # ============================================
            # STEP 3: ID DOCUMENTS - OCR + FIELD MATCHING
            # ============================================
            print(f"[VerifyIdFieldsView] Running OCR + field matching for ID document: {doc_type}")
            
            # Reset file pointer after header check
            id_image.seek(0)
            
            # Run OCR extraction
            if ENABLE_OCR_VALIDATION:
                ocr_fields = run_ocr_and_extract_fields_switchable(
                    id_image, 
                    doc_type=doc_type, 
                    registration_data=registration_data
                )
                print(f"[VerifyIdFieldsView] OCR extracted fields: {ocr_fields}")
            else:
                print("[VerifyIdFieldsView] OCR validation disabled in settings")
                ocr_fields = {}

            # UMID name swap fix (UMID has reversed name format)
            if doc_type and 'umid' in doc_type.lower():
                temp_first = ocr_fields.get('first_name', '')
                temp_last = ocr_fields.get('last_name', '')
                ocr_fields['first_name'] = temp_last
                ocr_fields['last_name'] = temp_first
                print(f"[VerifyIdFieldsView] UMID name swap applied - First: '{temp_last}', Last: '{temp_first}'")

            print('[VerifyIdFieldsView] Registration data:', registration_data)
            print('[VerifyIdFieldsView] OCR fields after processing:', ocr_fields)

            # ============================================
            # STEP 4: COMPARE USER INPUT WITH OCR RESULTS
            # ============================================
            mismatches = {}
            fields_to_check = ['first_name', 'last_name', 'dob']

            for key in fields_to_check:
                reg_val = registration_data.get(key, '')
                ocr_val = ocr_fields.get(key, '')
                print(f'[VerifyIdFieldsView] Comparing field "{key}": user="{reg_val}" ocr="{ocr_val}"')
                
                if key in ['first_name', 'last_name']:
                    # Use improved name comparison with fuzzy matching
                    if not are_names_equivalent(reg_val, ocr_val):
                        mismatches[key] = {
                            'user': reg_val,
                            'ocr': ocr_val
                        }
                else:
                    # For non-name fields (like DOB), use exact comparison
                    if normalize_for_comparison(reg_val) != normalize_for_comparison(ocr_val):
                        mismatches[key] = {
                            'user': reg_val,
                            'ocr': ocr_val
                        }
            
            print(f'[VerifyIdFieldsView] Mismatches found: {mismatches}')

            # ============================================
            # STEP 5: RETURN RESULTS
            # ============================================
            if mismatches:
                return Response({
                    'verified': False,
                    'status': 'mismatch',
                    'error_type': 'MISMATCH',
                    'mismatches': mismatches,
                    'user_friendly_message': 'Some details don\'t match your ID. Please review and correct.',
                    'action_required': 'EDIT_OR_RETAKE'
                }, status=200)

            # All fields match!
            print("[VerifyIdFieldsView] ID document verified - all fields match!")
            return Response({
                'verified': True,
                'status': 'match',
                'message': 'ID verified successfully',
                'extracted_fields': ocr_fields
            }, status=200)

        except Exception as e:
            print(f"[VerifyIdFieldsView] ERROR: {str(e)}")
            import traceback
            traceback.print_exc()
            return Response({
                'verified': False,
                'status': 'error',
                'error_type': 'SERVER_ERROR',
                'message': f'Verification failed: {str(e)}'
            }, status=500)
        
        finally:
            print("=== VerifyIdFieldsView END ===\n")



# class VerifyGuardianIdFieldsView(APIView):
#     """
#     Verify guardian ID fields by comparing OCR results with guardian's stored information
#     """
#     parser_classes = (MultiPartParser, FormParser)

#     def post(self, request):
#         try:
#             registration_data = json.loads(request.data.get('registrationData', '{}'))
#             id_image = request.FILES.get('id_image')
#             doc_type = registration_data.get('document_type', None)
#             guardian_username = registration_data.get('guardian_username', '')
            
#             if not id_image:
#                 return Response({'error': 'No image provided'}, status=400)
            
#             if not guardian_username:
#                 return Response({'error': 'Guardian username not provided'}, status=400) 

#             print(f"DEBUG: Verifying guardian ID for username: {guardian_username}")
#             print(f"DEBUG: Document type: {doc_type}")

#             # --- GUARDIAN SUPPORTING DOCS HEADER CHECK ---
#             if doc_type and any(x in doc_type.lower() for x in ['birth', 'voter']):
#                 header_ok = validate_document_header(id_image, doc_type)
#                 if not header_ok:
#                     return Response({
#                         'status': 'mismatch',
#                         'mismatches': {
#                             'header': {
#                                 'user': doc_type,
#                                 'ocr': 'Header/title not found in image'
#                             }
#                         }
#                     }, status=200)
#                 return Response({'status': 'match'})

#             # Get guardian information from database
#             guardian_info = None
#             with connection.cursor() as cursor:
#                 try:
#                     cursor.execute("""
#                         SELECT guardian_resident_id, last_name, first_name, middle_name, suffix, dob
#                         FROM get_guardian_identity_by_username(%s)
#                     """, [guardian_username])
                    
#                     result = cursor.fetchone()
#                     if result:
#                         guardian_info = {
#                             'guardian_resident_id': result[0],
#                             'last_name': result[1],
#                             'first_name': result[2],
#                             'middle_name': result[3] or '',
#                             'suffix': result[4] or '',
#                             'dob': result[5].strftime('%Y-%m-%d') if result[5] else ''
#                         }
#                         print(f"DEBUG: Guardian info retrieved: {guardian_info}")
#                     else:
#                         return Response({
#                             'error': 'Guardian not found or not verified'
#                         }, status=400)
                        
#                 except Exception as db_error:
#                     print(f"DEBUG: Database error: {str(db_error)}")
#                     return Response({
#                         'error': 'Guardian verification failed'
#                     }, status=400)

#             # Extract fields from guardian's document using OCR
#             extracted_fields = run_ocr_and_extract_fields_switchable(
#                 id_image, 
#                 doc_type, 
#                 guardian_info  # Pass guardian info for context
#             )

#             print(f"DEBUG: OCR extracted fields: {extracted_fields}")

#             # IMPORTANT: Remap OCR results to match guardian's stored information
#             # The OCR might have the names in wrong order, so we need to match them
#             ocr_first = extracted_fields.get('first_name', '').upper()
#             ocr_last = extracted_fields.get('last_name', '').upper()
#             ocr_middle = extracted_fields.get('middle_name', '').upper()
            
#             guardian_first = guardian_info['first_name'].upper()
#             guardian_last = guardian_info['last_name'].upper()
#             guardian_middle = guardian_info['middle_name'].upper()

#             print(f"DEBUG: OCR Names - First: '{ocr_first}', Last: '{ocr_last}', Middle: '{ocr_middle}'")
#             print(f"DEBUG: Guardian Names - First: '{guardian_first}', Last: '{guardian_last}', Middle: '{guardian_middle}'")

#             # Smart remapping: Check if OCR first/last are swapped
#             corrected_fields = {}
            
#             # Check if OCR first name matches guardian's last name (indicating swap)
#             if ocr_first == guardian_last and ocr_last == guardian_first:
#                 print("DEBUG: Detected name swap - correcting...")
#                 corrected_fields = {
#                     'first_name': ocr_last,  # Swap: use OCR last as first
#                     'last_name': ocr_first,  # Swap: use OCR first as last
#                     'middle_name': ocr_middle,
#                     'dob': extracted_fields.get('dob', '')
#                 }
#             else:
#                 # No swap needed
#                 corrected_fields = {
#                     'first_name': ocr_first,
#                     'last_name': ocr_last,
#                     'middle_name': ocr_middle,
#                     'dob': extracted_fields.get('dob', '')
#                 }

#             print(f"DEBUG: Corrected fields: {corrected_fields}")

#             # Compare corrected fields with guardian's stored information
#             mismatches = {}

#             # Compare first name
#             if corrected_fields.get('first_name'):
#                 if not are_names_equivalent(corrected_fields['first_name'], guardian_info['first_name']):
#                     mismatches['first_name'] = {
#                         'guardian': corrected_fields['first_name'],
#                         'expected': guardian_info['first_name']
#                     }

#             # Compare last name
#             if corrected_fields.get('last_name'):
#                 if not are_names_equivalent(corrected_fields['last_name'], guardian_info['last_name']):
#                     mismatches['last_name'] = {
#                         'guardian': corrected_fields['last_name'],
#                         'expected': guardian_info['last_name']
#                     }

#             # Compare middle name
#             if corrected_fields.get('middle_name') and guardian_info['middle_name']:
#                 if not are_names_equivalent(corrected_fields['middle_name'], guardian_info['middle_name']):
#                     mismatches['middle_name'] = {
#                         'guardian': corrected_fields['middle_name'],
#                         'expected': guardian_info['middle_name']
#                     }

#             # Compare date of birth
#             if corrected_fields.get('dob') and guardian_info['dob']:
#                 ocr_dob = normalize_for_comparison(corrected_fields['dob'])
#                 guardian_dob = normalize_for_comparison(guardian_info['dob'])
#                 if ocr_dob != guardian_dob:
#                     mismatches['dob'] = {
#                         'guardian': corrected_fields['dob'],
#                         'expected': guardian_info['dob']
#                     }

#             print(f"DEBUG: Comparison mismatches after correction: {mismatches}")

#             if mismatches:
#                 return Response({
#                     'status': 'mismatch',
#                     'message': 'Guardian document details do not match stored information',
#                     'mismatches': mismatches,
#                     'extracted_fields': corrected_fields,
#                     'guardian_stored_info': {
#                         'first_name': guardian_info['first_name'],
#                         'last_name': guardian_info['last_name'],
#                         'middle_name': guardian_info['middle_name'],
#                         'dob': guardian_info['dob']
#                     }
#                 })
#             else:
#                 return Response({
#                     'status': 'match',
#                     'message': 'Guardian document verified successfully',
#                     'extracted_fields': corrected_fields,
#                     'guardian_verified_info': {
#                         'first_name': guardian_info['first_name'],
#                         'last_name': guardian_info['last_name'],
#                         'middle_name': guardian_info['middle_name'],
#                         'dob': guardian_info['dob']
#                     }
#                 })

#         except Exception as e:
#             print(f"Guardian ID verification error: {str(e)}")
#             return Response({
#                 'error': f'Verification failed: {str(e)}'
#             }, status=500)
        

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

            # ✅ STEP 1: Validate document header first
            if doc_type and any(x in doc_type.lower() for x in ['birth', 'voter']):
                header_ok = validate_document_header(id_image, doc_type)
                if not header_ok:
                    return Response({
                        'verified': False,
                        'error_type': 'DOCUMENT_TYPE_MISMATCH',
                        'user_friendly_message': f"This doesn't look like a {doc_type}. Please upload a clear photo of your guardian's {doc_type}.",
                        'message': f'Document header validation failed for {doc_type}'
                    }, status=200)

            # ✅ STEP 2: Extract OCR fields
            guardian_data_for_ocr = {
                'first_name': guardian_first_name,
                'last_name': guardian_last_name,
                'middle_name': guardian_middle_name or '',
                'dob': str(guardian_dob) if guardian_dob else ''
            }

            ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, guardian_data_for_ocr)
            print(f"DEBUG: OCR extracted fields: {ocr_fields}")

            # ✅ STEP 3: Check if OCR returned meaningful data
            ocr_first = (ocr_fields.get('first_name') or '').strip()
            ocr_last = (ocr_fields.get('last_name') or '').strip()
            ocr_dob = (ocr_fields.get('dob') or '').strip()

            print(f"DEBUG: OCR Names - First: '{ocr_first}', Last: '{ocr_last}', Middle: '{ocr_fields.get('middle_name', '')}'")
            print(f"DEBUG: Guardian Names - First: '{guardian_first_name.upper()}', Last: '{guardian_last_name.upper()}', Middle: '{guardian_middle_name or ''}'")

            # ✅ STEP 4: For ID documents, require OCR to extract names
            if doc_type and not any(x in doc_type.lower() for x in ['birth', 'voter']):  # ID documents
                if not ocr_first and not ocr_last:
                    return Response({
                        'verified': False,
                        'error_type': 'QUALITY_ISSUE',
                        'user_friendly_message': f"We couldn't read your guardian's {doc_type} clearly. Please retake the photo with better lighting and ensure all text is visible.",
                        'message': 'OCR could not extract readable names from the document'
                    }, status=200)

            # ✅ STEP 5: Find mismatches between OCR and guardian info
            mismatches = find_mismatches(
                guardian_data_for_ocr,
                ocr_fields,
                ['first_name', 'last_name', 'dob']
            )

            print(f"DEBUG: Corrected fields: {ocr_fields}")
            print(f"DEBUG: Comparison mismatches after correction: {mismatches}")

            # ✅ STEP 6: Handle mismatches
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

            # ✅ SUCCESS: Document verified
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