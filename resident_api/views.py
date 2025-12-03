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

# --- OCR AND EXTRACTION FUNCTIONS ---
#moved to ocr_processing file
# def preprocess_image_for_ocr(pil_image):
#     """Preprocess image for better OCR accuracy."""
#     gray = pil_image.convert('L')
#     image = np.array(gray)
#     image = cv2.fastNlMeansDenoising(image, h=30)
#     image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    
#     coords = np.column_stack(np.where(image > 0))
#     angle = 0
#     if coords.shape[0] > 0:
#         rect = cv2.minAreaRect(coords)
#         angle = rect[-1]
#         if angle < -45:
#             angle = -(90 + angle)
#         else:
#             angle = -angle
#         (h, w) = image.shape[:2]
#         M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
#         image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
#     return Image.fromarray(image)

# def clean_ocr_text(text):
#     """Clean OCR text by removing invalid characters and short lines."""
#     text = re.sub(r'[^\x20-\x7E\n]', '', text)
#     lines = text.split('\n')
#     cleaned_lines = [line for line in lines if len(re.sub(r'[^a-zA-Z0-9]', '', line)) > 2]
#     return '\n'.join(cleaned_lines)

# def extract_fields(ocr_text, doc_type, registration_data=None):
#     """Enhanced field extraction with better accuracy and validation."""
#     text = ocr_text
#     lines = [l.strip() for l in text.split('\n') if l.strip()]

#     def is_label(line, label_keywords):
#         """Check if a line is a label."""
#         return any(kw.lower() in line.lower() for kw in label_keywords)

#     def extract_value(label_keywords, lines, value_type=None):
#         """Extract value after finding label with improved logic."""
#         def clean_line(line):
#             return re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', line).strip()

#         for i, line in enumerate(lines):
#             if is_label(line, label_keywords):
#                 for j in range(i+1, min(i+4, len(lines))):
#                     next_line = lines[j]
#                     if not is_label(next_line, label_keywords) and len(next_line) > 1:
#                         if value_type == 'name':
#                             cleaned = clean_name_line(next_line)
#                             alpha_count = sum(c.isalpha() for c in cleaned)
#                             if alpha_count >= max(3, len(cleaned)//2) and len(cleaned) > 2:
#                                 return cleaned
#                         elif value_type == 'date':
#                             date_match = re.search(r'(\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})', next_line)
#                             if date_match:
#                                 date_str = date_match.group(1)
#                                 date_str = correct_month_name(date_str)
#                                 try:
#                                     from dateutil import parser
#                                     dt = parser.parse(date_str, dayfirst=False, yearfirst=True)
#                                     return dt.strftime('%Y-%m-%d')
#                                 except Exception:
#                                     return date_str
#                         else:
#                             cleaned = clean_line(next_line)
#                             return cleaned
#         return ''

#     if doc_type == 'Philippine National ID':
#         # Enhanced label recognition with more variations
#         first_name_labels = [
#             'First Name', 'Given Name', 'Given Names', 'Mga Pangalan', 'Pangalan',
#             'Mega Pangalan', 'Mga Pangalan/Given Names', 'GivenNames', 'GivenName',
#             'PANGALAN', 'GIVEN', 'GIVEN NAMES', 'GIVEN NAME', 'PANGALAN/GIVEN NAMES',
#             'GIVEN NANE', 'GIVEN NARE', 'GIVEN NAMS', 'F1RST NAME', 'G1VEN NAME'
#         ]
#         last_name_labels = [
#             'Last Name', 'Apelyido', 'Apelyido/Last Name', 'Apelyido/Last',
#             'LAST NAME', 'LASTNAME', 'APELYIDO', 'APELYIDO/LAST NAME',
#             'LAST NANE', 'LAST NARE', 'LAST NAMS', 'L4ST NAME'
#         ]
#         middle_name_labels = [
#             'Middle Name', 'Gitnang Apelyido', 'Gitnang', 'Gitnang Apelyido/Middle Name',
#             'MIDDLE NAME', 'MIDDLENAME', 'GITNANG', 'GITNANG APELYIDO',
#             'M1DDLE NAME', 'MIDDLE NANE', 'MIDDLE NARE'
#         ]
#         dob_labels = [
#             'Date of Birth', 'Petsa ng Kapanganakan', 'Kapanganakan',
#             'DATE OF BIRTH', 'PETSA NG KAPANGANAKAN', 'DATE 0F BIRTH'
#         ]

#         # Extract fields using improved logic
#         first_name = extract_value(first_name_labels, lines, value_type='name')
#         last_name = extract_value(last_name_labels, lines, value_type='name')
#         middle_name = extract_value(middle_name_labels, lines, value_type='name')
#         dob = extract_value(dob_labels, lines, value_type='date')

#         # IMPROVED: Post-processing with registration data validation
#         if registration_data:
#             user_first = registration_data.get('first_name', '').lower()
#             user_last = registration_data.get('last_name', '').lower()
#             user_middle = registration_data.get('middle_name', '').lower()

#             # Extract all potential names from lines
#             extracted_names = []
#             if first_name:
#                 extracted_names.append(('first', first_name.lower()))
#             if last_name:
#                 extracted_names.append(('last', last_name.lower()))
#             if middle_name:
#                 extracted_names.append(('middle', middle_name.lower()))

#             # Try to match extracted names with user input
#             corrected_first = first_name
#             corrected_last = last_name
#             corrected_middle = middle_name

#             # Check for exact matches and corrections
#             for field_type, extracted_name in extracted_names:
#                 if user_first and user_first in extracted_name:
#                     corrected_first = extracted_name.title()
#                 elif user_last and user_last in extracted_name:
#                     corrected_last = extracted_name.title()
#                 elif user_middle and user_middle in extracted_name:
#                     corrected_middle = extracted_name.title()

#             # CRITICAL FIX: Search for missing last name in OCR text
#             if not corrected_last or corrected_last.lower() == corrected_first.lower():
#                 for line in lines:
#                     line_lower = line.lower()
#                     if user_last and user_last in line_lower:
#                         # Clean the line and extract just the name
#                         cleaned_line = re.sub(r'[^\w\s]', ' ', line).strip()
#                         words = cleaned_line.split()
#                         for word in words:
#                             if user_last in word.lower():
#                                 corrected_last = word.title()
#                                 print(f'DEBUG: Found missing last name in OCR: "{corrected_last}"')
#                                 break
#                         if corrected_last.lower() != corrected_first.lower():
#                             break

#             first_name = corrected_first
#             last_name = corrected_last
#             middle_name = corrected_middle

#             print(f'DEBUG: Post-processing results - First: "{first_name}", Last: "{last_name}", Middle: "{middle_name}"')

#         # Normalize the extracted names
#         first_name = normalize_name(first_name)
#         last_name = normalize_name(last_name)
#         middle_name = normalize_name(middle_name)

#         return {
#             'first_name': first_name,
#             'last_name': last_name,
#             'middle_name': middle_name,
#             'dob': dob,
#         }

#     # Birth Certificate logic remains the same...
#     elif doc_type == 'Birth Certificate':
#         # [Previous birth certificate logic - keeping it the same for stability]
#         return {
#             'first_name': '',
#             'last_name': '',
#             'middle_name': '',
#             'dob': '',
#         }

#     return {}

# def run_ocr_and_extract_fields(id_image_file, doc_type=None, registration_data=None):
#     """Run OCR and extract fields using Tesseract."""
#     pil_image = Image.open(id_image_file)
#     processed_image = preprocess_image_for_ocr(pil_image)
#     enhancer = ImageEnhance.Contrast(processed_image)
#     processed_image = enhancer.enhance(2.0)
#     ocr_text = pytesseract.image_to_string(processed_image, config='--psm 3')
#     ocr_text = clean_ocr_text(ocr_text)
#     print('DEBUG: Cleaned OCR text:', repr(ocr_text))
#     return extract_fields(ocr_text, doc_type, registration_data)

# def id_analyzer_scan(image_file):
#     """Scan image using ID Analyzer API."""
#     api_key = getattr(settings, 'ID_ANALYZER_API_KEY', None)
#     if not api_key:
#         raise Exception("ID Analyzer API key not set in settings.")
#     files = {'file': image_file}
#     data = {'apikey': api_key}
#     response = requests.post('https://api.idanalyzer.com', files=files, data=data)
#     print("ID Analyzer raw response:", response.text)
#     return response.json()

# def remap_names_from_fullname(full_name, user_first, user_last, user_middle):
#     """Improved name remapping with better matching logic."""
#     full_parts = [p.strip().lower() for p in full_name.split() if p.strip()]
#     user_first = user_first.lower() if user_first else ''
#     user_last = user_last.lower() if user_last else ''
#     user_middle = user_middle.lower() if user_middle else ''

#     mapping = {'first_name': '', 'middle_name': '', 'last_name': ''}
    
#     # Exact matches first
#     for part in full_parts:
#         if part == user_first and not mapping['first_name']:
#             mapping['first_name'] = part
#         elif part == user_last and not mapping['last_name']:
#             mapping['last_name'] = part
#         elif user_middle and part == user_middle and not mapping['middle_name']:
#             mapping['middle_name'] = part

#     # Partial matches if not all mapped
#     for part in full_parts:
#         if not mapping['first_name'] and user_first and user_first in part:
#             mapping['first_name'] = part
#         if not mapping['last_name'] and user_last and user_last in part:
#             mapping['last_name'] = part
#         if user_middle and not mapping['middle_name'] and user_middle in part:
#             mapping['middle_name'] = part

#     # Fallback: assign by order (common for PH IDs: LAST FIRST MIDDLE)
#     if not mapping['last_name'] or not mapping['first_name']:
#         if len(full_parts) >= 2:
#             mapping['last_name'] = full_parts[0]
#             mapping['first_name'] = full_parts[1]
#             if len(full_parts) > 2:
#                 mapping['middle_name'] = full_parts[2]

#     # Capitalize for output
#     for k in mapping:
#         if mapping[k]:
#             mapping[k] = mapping[k].title()
    
#     return mapping


# def run_ocr_and_extract_fields_switchable(id_image_file, doc_type=None, registration_data=None):
#     """IMPROVED: Main OCR function with better name handling for Philippine Driver's License."""
#     ocr_backend = getattr(settings, 'OCR_BACKEND', 'tesseract')
#     if ocr_backend == 'idanalyzer':
#         try:
#             idanalyzer_result = id_analyzer_scan(id_image_file)
#             result = idanalyzer_result.get('result', {})
            
#             # Get raw extracted data
#             raw_first_name = result.get('firstName', '')
#             raw_middle_name = result.get('middleName', '')
#             raw_last_name = result.get('lastName', '')
#             full_name = result.get('fullName', '')
#             dob = result.get('dob', '')

#             print(f"DEBUG: ID Analyzer raw extraction - First: '{raw_first_name}', Middle: '{raw_middle_name}', Last: '{raw_last_name}'")
#             print(f"DEBUG: Full name: '{full_name}'")

#             # Handle Philippine Driver's License specific format
#             if doc_type and 'driver' in doc_type.lower() and registration_data:
#                 first_name, middle_name, last_name = handle_philippine_drivers_license(
#                     raw_first_name, raw_middle_name, raw_last_name, full_name, registration_data
#                 )
#             else:
#                 # For other document types, use raw extraction
#                 first_name = raw_first_name
#                 middle_name = raw_middle_name
#                 last_name = raw_last_name

#             # Format DOB
#             if dob and '/' in dob:
#                 dob = dob.replace('/', '-')

#             fields = {
#                 'first_name': first_name,
#                 'last_name': last_name,
#                 'middle_name': middle_name,
#                 'dob': dob,
#             }

#             print(f"DEBUG: Final extracted fields - First: '{first_name}', Middle: '{middle_name}', Last: '{last_name}'")
#             return fields

#         except Exception as e:
#             print("ID Analyzer failed, falling back to Tesseract:", e)
#             id_image_file.seek(0)
#             return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)
#     else:
#         return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)

# def handle_philippine_drivers_license(raw_first, raw_middle, raw_last, full_name, registration_data):
#     """
#     Handle Philippine Driver's License name format specifically.
#     Driver's License format: Last Name, First Name Middle Name
#     """
#     user_first = registration_data.get('first_name', '').strip()
#     user_middle = registration_data.get('middle_name', '').strip()
#     user_last = registration_data.get('last_name', '').strip()
    
#     print(f"DEBUG: User input - First: '{user_first}', Middle: '{user_middle}', Last: '{user_last}'")
#     print(f"DEBUG: ID Analyzer raw - First: '{raw_first}', Middle: '{raw_middle}', Last: '{raw_last}'")
    
#     # Start with ID Analyzer results
#     first_name = raw_first
#     middle_name = raw_middle
#     last_name = raw_last
    
   
#     if user_first and ' ' in user_first:
#         user_first_parts = user_first.split()
        
#         # Check if ID Analyzer split the first name incorrectly
     
#         if raw_middle and raw_middle.startswith(user_first_parts[1].upper()):
#             # Reconstruct the first name
#             first_name = ' '.join(user_first_parts)
            
#             # Extract the actual middle name from the raw middle name
#             # Remove the second part of first name from raw middle name
#             remaining_middle = raw_middle.replace(user_first_parts[1].upper(), '').strip()
#             if remaining_middle and user_middle and remaining_middle.upper() == user_middle.upper():
#                 middle_name = user_middle
#             else:
#                 middle_name = remaining_middle
                
#             print(f"DEBUG: Reconstructed multi-word first name: '{first_name}', Middle: '{middle_name}'")
    
#     # Case 2: Verify last name is correct
#     if user_last and raw_last:
#         if normalize_name_for_comparison(user_last) != normalize_name_for_comparison(raw_last):
#             # Check if they're similar enough
#             if not names_are_similar(user_last, raw_last):
#                 print(f"DEBUG: Last name mismatch - User: '{user_last}', ID Analyzer: '{raw_last}'")
#                 # In this case, trust ID Analyzer since it's usually more accurate for last names
#                 last_name = raw_last
    
#     # Case 3: Handle cases where middle name contains multiple parts
#     if user_middle and raw_middle:
#         # If user middle is single word but raw middle has multiple words
#         if ' ' not in user_middle and ' ' in raw_middle:
#             # Check if user middle is contained in raw middle
#             if user_middle.upper() in raw_middle.upper():
#                 middle_name = user_middle
#                 print(f"DEBUG: Used user's single-word middle name: '{middle_name}'")
    
#     # Normalize case
#     first_name = normalize_name(first_name) if first_name else ''
#     middle_name = normalize_name(middle_name) if middle_name else ''
#     last_name = normalize_name(last_name) if last_name else ''
    
#     return first_name, middle_name, last_name

class VerifyIdFieldsView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
   
        try:
            registration_data = json.loads(request.data.get('registrationData', '{}'))
            id_image = request.FILES.get('id_image')
            doc_type = registration_data.get('document_type', None)
            
            if not id_image:
                return Response({'status': 'error', 'message': 'No image provided'}, status=400)

            # --- SUPPORTING DOCS HEADER CHECK ---
            # If this is a supporting document, only check the header/title
            if doc_type and any(x in doc_type.lower() for x in ['birth', 'voter']):
                # Only check header/title for supporting docs
                header_ok = validate_document_header(id_image, doc_type)
                if not header_ok:
                    return Response({
                        'status': 'mismatch',
                        'mismatches': {
                            'header': {
                                'user': doc_type,
                                'ocr': 'Header/title not found in image'
                            }
                        }
                    }, status=200)

                # If header is OK, you can skip field comparison and return match
                return Response({'status': 'match'})

            # Extract fields using improved logic
            ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, registration_data)
            
            if doc_type and 'umid' in doc_type.lower():
                # Simple UMID fix: swap first and last names
                temp_first = ocr_fields.get('first_name', '')
                temp_last = ocr_fields.get('last_name', '')
                ocr_fields['first_name'] = temp_last
                ocr_fields['last_name'] = temp_first
                print(f"DEBUG: UMID name swap applied - First: '{temp_last}', Last: '{temp_first}'")

            print('DEBUG: registration_data:', registration_data)
            print('DEBUG: ocr_fields:', ocr_fields)
            
            mismatches = {}

            # Compare fields with improved logic
            for key in ['first_name', 'last_name', 'dob']:
                reg_val = registration_data.get(key, '')
                ocr_val = ocr_fields.get(key, '')
                print(f'DEBUG: Comparing field "{key}": user="{reg_val}" ocr="{ocr_val}"')
                
                if key in ['first_name', 'last_name']:
                    # Use improved name comparison
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
            
            print('DEBUG: mismatches:', mismatches)
            
            if mismatches:
                return Response({'status': 'mismatch', 'mismatches': mismatches})
            return Response({'status': 'match'})

        except Exception as e:
            print(f"Verification failed with error: {e}")
            return Response({'status': 'error', 'message': str(e)}, status=500)

class VerifyGuardianIdFieldsView(APIView):
    """
    Verify guardian ID fields by comparing OCR results with guardian's stored information
    """
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        try:
            registration_data = json.loads(request.data.get('registrationData', '{}'))
            id_image = request.FILES.get('id_image')
            doc_type = registration_data.get('document_type', None)
            guardian_username = registration_data.get('guardian_username', '')
            
            if not id_image:
                return Response({'error': 'No image provided'}, status=400)
            
            if not guardian_username:
                return Response({'error': 'Guardian username not provided'}, status=400) 

            print(f"DEBUG: Verifying guardian ID for username: {guardian_username}")
            print(f"DEBUG: Document type: {doc_type}")

            # --- GUARDIAN SUPPORTING DOCS HEADER CHECK ---
            if doc_type and any(x in doc_type.lower() for x in ['birth', 'voter']):
                header_ok = validate_document_header(id_image, doc_type)
                if not header_ok:
                    return Response({
                        'status': 'mismatch',
                        'mismatches': {
                            'header': {
                                'user': doc_type,
                                'ocr': 'Header/title not found in image'
                            }
                        }
                    }, status=200)
                return Response({'status': 'match'})

            # Get guardian information from database
            guardian_info = None
            with connection.cursor() as cursor:
                try:
                    cursor.execute("""
                        SELECT guardian_resident_id, last_name, first_name, middle_name, suffix, dob
                        FROM get_guardian_identity_by_username(%s)
                    """, [guardian_username])
                    
                    result = cursor.fetchone()
                    if result:
                        guardian_info = {
                            'guardian_resident_id': result[0],
                            'last_name': result[1],
                            'first_name': result[2],
                            'middle_name': result[3] or '',
                            'suffix': result[4] or '',
                            'dob': result[5].strftime('%Y-%m-%d') if result[5] else ''
                        }
                        print(f"DEBUG: Guardian info retrieved: {guardian_info}")
                    else:
                        return Response({
                            'error': 'Guardian not found or not verified'
                        }, status=400)
                        
                except Exception as db_error:
                    print(f"DEBUG: Database error: {str(db_error)}")
                    return Response({
                        'error': 'Guardian verification failed'
                    }, status=400)

            # Extract fields from guardian's document using OCR
            extracted_fields = run_ocr_and_extract_fields_switchable(
                id_image, 
                doc_type, 
                guardian_info  # Pass guardian info for context
            )

            print(f"DEBUG: OCR extracted fields: {extracted_fields}")

            # IMPORTANT: Remap OCR results to match guardian's stored information
            # The OCR might have the names in wrong order, so we need to match them
            ocr_first = extracted_fields.get('first_name', '').upper()
            ocr_last = extracted_fields.get('last_name', '').upper()
            ocr_middle = extracted_fields.get('middle_name', '').upper()
            
            guardian_first = guardian_info['first_name'].upper()
            guardian_last = guardian_info['last_name'].upper()
            guardian_middle = guardian_info['middle_name'].upper()

            print(f"DEBUG: OCR Names - First: '{ocr_first}', Last: '{ocr_last}', Middle: '{ocr_middle}'")
            print(f"DEBUG: Guardian Names - First: '{guardian_first}', Last: '{guardian_last}', Middle: '{guardian_middle}'")

            # Smart remapping: Check if OCR first/last are swapped
            corrected_fields = {}
            
            # Check if OCR first name matches guardian's last name (indicating swap)
            if ocr_first == guardian_last and ocr_last == guardian_first:
                print("DEBUG: Detected name swap - correcting...")
                corrected_fields = {
                    'first_name': ocr_last,  # Swap: use OCR last as first
                    'last_name': ocr_first,  # Swap: use OCR first as last
                    'middle_name': ocr_middle,
                    'dob': extracted_fields.get('dob', '')
                }
            else:
                # No swap needed
                corrected_fields = {
                    'first_name': ocr_first,
                    'last_name': ocr_last,
                    'middle_name': ocr_middle,
                    'dob': extracted_fields.get('dob', '')
                }

            print(f"DEBUG: Corrected fields: {corrected_fields}")

            # Compare corrected fields with guardian's stored information
            mismatches = {}

            # Compare first name
            if corrected_fields.get('first_name'):
                if not are_names_equivalent(corrected_fields['first_name'], guardian_info['first_name']):
                    mismatches['first_name'] = {
                        'guardian': corrected_fields['first_name'],
                        'expected': guardian_info['first_name']
                    }

            # Compare last name
            if corrected_fields.get('last_name'):
                if not are_names_equivalent(corrected_fields['last_name'], guardian_info['last_name']):
                    mismatches['last_name'] = {
                        'guardian': corrected_fields['last_name'],
                        'expected': guardian_info['last_name']
                    }

            # Compare middle name
            if corrected_fields.get('middle_name') and guardian_info['middle_name']:
                if not are_names_equivalent(corrected_fields['middle_name'], guardian_info['middle_name']):
                    mismatches['middle_name'] = {
                        'guardian': corrected_fields['middle_name'],
                        'expected': guardian_info['middle_name']
                    }

            # Compare date of birth
            if corrected_fields.get('dob') and guardian_info['dob']:
                ocr_dob = normalize_for_comparison(corrected_fields['dob'])
                guardian_dob = normalize_for_comparison(guardian_info['dob'])
                if ocr_dob != guardian_dob:
                    mismatches['dob'] = {
                        'guardian': corrected_fields['dob'],
                        'expected': guardian_info['dob']
                    }

            print(f"DEBUG: Comparison mismatches after correction: {mismatches}")

            if mismatches:
                return Response({
                    'status': 'mismatch',
                    'message': 'Guardian document details do not match stored information',
                    'mismatches': mismatches,
                    'extracted_fields': corrected_fields,
                    'guardian_stored_info': {
                        'first_name': guardian_info['first_name'],
                        'last_name': guardian_info['last_name'],
                        'middle_name': guardian_info['middle_name'],
                        'dob': guardian_info['dob']
                    }
                })
            else:
                return Response({
                    'status': 'match',
                    'message': 'Guardian document verified successfully',
                    'extracted_fields': corrected_fields,
                    'guardian_verified_info': {
                        'first_name': guardian_info['first_name'],
                        'last_name': guardian_info['last_name'],
                        'middle_name': guardian_info['middle_name'],
                        'dob': guardian_info['dob']
                    }
                })

        except Exception as e:
            print(f"Guardian ID verification error: {str(e)}")
            return Response({
                'error': f'Verification failed: {str(e)}'
            }, status=500)
        

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
              
                # if result.get('account_type') == 'resident' and not result.get('is_verified', True):
                #     return Response({
                #         'success': False,
                #         'status': 'not_verified',
                #         'message': 'Your account is pending verification. Please wait for approval.',
                #         'account_type': result.get('account_type'),
                #         'username': result.get('username')
                #     }, status=200)
                
                # return Response({
                #     'success': True,
                #     'status': 'success',
                #     'account_type': result['account_type'],
                #     'user_id': result.get('personnel_id') or result.get('resident_id'),
                #     'username': result['username'],
                #     'role_name': result.get('role_name'),
                #     'role_id': result.get('role_id'),
                #     'session_token': result['session_token'],  
                #     'message': 'Login successful'
                # }, status=200)

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