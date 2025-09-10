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
    update_resident_profile, change_personnel_password
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

# Configure Tesseract path
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- HELPER FUNCTIONS  ---

# def normalize_name_for_comparison(name):
#     """Normalize names for comparison by removing special characters and extra spaces."""
#     if not name:
#         return ''
#     normalized = re.sub(r'[^a-z0-9\s]', '', name.lower().strip())
#     normalized = ' '.join(normalized.split())
#     return normalized

# def names_are_similar(name1, name2):
#     """Check if two names are similar with 70% overlap threshold."""
#     n1 = set(normalize_name_for_comparison(name1).split())
#     n2 = set(normalize_name_for_comparison(name2).split())
#     if not n1 or not n2:
#         return False
#     overlap = len(n1 & n2) / max(len(n1 | n2), 1)
#     return overlap >= 0.7

# def normalize_for_comparison(val):
#     """General normalization function for non-name fields."""
#     if not val:
#         return ''
#     return re.sub(r'[^a-z0-9]', '', val.lower().strip())

# def are_names_equivalent(name1, name2):
#         """Check if two names are equivalent, handling multi-word names properly."""
#         if not name1 or not name2:
#             return False
            
#         # Normalize both names
#         norm1 = normalize_name_for_comparison(name1)
#         norm2 = normalize_name_for_comparison(name2)
        
#         # Exact match
#         if norm1 == norm2:
#             return True
        
#         # Check if all words in one name are contained in the other
#         words1 = set(norm1.split())
#         words2 = set(norm2.split())
        
#         # If one is subset of the other, consider them equivalent
#         if words1.issubset(words2) or words2.issubset(words1):
#             return True
        
#         # Check for significant overlap (at least 70%)
#         if len(words1) > 0 and len(words2) > 0:
#             overlap = len(words1.intersection(words2))
#             total_unique = len(words1.union(words2))
#             similarity = overlap / total_unique
#             return similarity >= 0.7
        
#         return False

# def correct_month_name(date_str):
#     """Correct OCR month name errors using fuzzy matching."""
#     months = [
#         "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
#         "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
#     ]
#     words = date_str.upper().split()
#     for i, word in enumerate(words):
#         if len(word) >= 3:
#             matches = difflib.get_close_matches(word, months, n=1, cutoff=0.6)
#             if matches:
#                 words[i] = matches[0]
#                 return " ".join(words)
#     return date_str

# def clean_name_line(line):
#     """Clean and extract name values with better noise removal."""
#     cleaned = re.sub(r'[^\w\s]', ' ', line)
#     cleaned = re.sub(r'\s+', ' ', cleaned)
#     cleaned = cleaned.strip()
    
#     # Remove common OCR noise words at the beginning
#     noise_words = ['che', 'chee', 'chea', 'cheo', 'cheu', 'chei', 'chey', 'chew', 'cheq', 'chez']
#     words = cleaned.split()
#     if words and words[0].lower() in noise_words:
#         words = words[1:]
    
#     # Remove very short words (likely noise)
#     words = [word for word in words if len(word) > 1]
    
#     return ' '.join(words)

# def normalize_name(name):
#     """Normalize names for output (title case, remove extra spaces)."""
#     if not name:
#         return ''
#     return ' '.join(name.split()).title()

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
        
# Update existing VerifyGuardianView (Original)
# class VerifyGuardianView(APIView):
#     """
#     Verify if a guardian username exists in the system and is verified
#     Uses the database function get_guardian_identity_by_username
#     """
#     def post(self, request):
#         try:
#             guardian_username = request.data.get('guardian_username', '').strip()
            
#             if not guardian_username:
#                 return Response({
#                     'exists': False,
#                     'message': 'Guardian username is required'
#                 }, status=400)
            
#             # Use the database function to check guardian
#             with connection.cursor() as cursor:
#                 try:
#                     cursor.execute("""
#                         SELECT guardian_resident_id, last_name, first_name, middle_name, suffix, dob
#                         FROM get_guardian_identity_by_username(%s)
#                     """, [guardian_username])
                    
#                     guardian_data = cursor.fetchone()
                    
#                     if guardian_data:
#                         # Guardian exists and is verified
#                         return Response({
#                             'exists': True,
#                             'message': 'Guardian found and verified',
#                             'guardian_verified': True
#                         }, status=200)
#                     else:
#                         return Response({
#                             'exists': False,
#                             'message': 'Guardian username not found or guardian is not verified'
#                         }, status=200)
                        
#                 except Exception as db_error:
#                     # Database function raises exception if guardian not found or not verified
#                     error_message = str(db_error)
#                     print(f"Database error: {error_message}")
#                     return Response({
#                         'exists': False,
#                         'message': 'Guardian username not found or guardian is not verified'
#                     }, status=200)
                        
#         except Exception as e:
#             print(f"Guardian verification error: {str(e)}")
#             return Response({
#                 'exists': False,
#                 'error': f'Verification failed: {str(e)}'
#             }, status=500)

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
#ORIGINAL
# class MobileLoginView(APIView):
#     """
#     Handle login for mobile app (both personnel and residents)
#     Uses the login_user_mobile database function
#     """
    
#     def post(self, request):
#         print("Mobile login attempt")
        
#         try:
#             # Get credentials from request
#             username = request.data.get('username', '').strip()
#             password = request.data.get('password', '')
            
#             if not username or not password:
#                 return Response({
#                     'success': False,
#                     'status': 'error',
#                     'message': 'Username and password are required'
#                 }, status=400)
            
#             print(f"Login attempt for username: {username}")
            
#             # Call the database function
#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     SELECT login_user_mobile(%s, %s)
#                 """, [username, password])
                
#                 result = cursor.fetchone()[0]  # Get the JSON result
                
#             print(f"Database response: {result}")
            
#             # Parse the JSON response from the database function
#             if result['status'] == 'success':
#                 return Response({
#                     'success': True,
#                     'status': 'success',
#                     'account_type': result['account_type'],
#                     'user_id': result.get('personnel_id') or result.get('resident_id'),
#                     'username': result['username'],
#                     'role_name': result.get('role_name'),  # Only for personnel
#                     'role_id': result.get('role_id'),      # Only for personnel
#                     'session_token': result['session_token'],
#                     'message': 'Login successful'
#                 }, status=200)
                
#             elif result['status'] == 'require_password_change':
#                 return Response({
#                     'success': False,
#                     'status': 'require_password_change',
#                     'account_type': result['account_type'],
#                     'user_id': result.get('personnel_id') or result.get('resident_id'),
#                     'username': result['username'],
#                     'message': result['message']
#                 }, status=200)
                
#             else:
#                 return Response({
#                     'success': False,
#                     'status': 'error',
#                     'message': result['message']
#                 }, status=401)
                
#         except Exception as e:
#             print(f"Mobile login error: {str(e)}")
#             return Response({
#                 'success': False,
#                 'status': 'error',
#                 'message': 'Login failed due to server error'
#             }, status=500)

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
                    return Response({
                        'success': False,
                        'status': 'not_verified',
                        'message': 'Your account is pending verification. Please wait for approval.',
                        'account_type': result.get('account_type'),
                        'username': result.get('username')
                    }, status=200)
                
                
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
# original
# class ResidentProfileView(APIView):
#     """
#     Get resident profile using the get_resident_profile database function
#     """

#     def get(self, request, resident_id):
#         print(f"Fetching profile for resident_id: {resident_id}")

#         try:
#             # call db function
#             with connection.cursor() as cursor:
#                 cursor.execute(""" SELECT get_resident_profile(%s) """, [resident_id])
#                 result = cursor.fetchone()[0] # get json result

#             print(f"Profile data retrieved: {result}")

#             if result:
#                 return Response({
#                     'success': True,
#                     'profile': result
#                 }, status=200)
#             else:
#                 return Response({
#                     'success': False,
#                     'message': 'Profile not found'
#                 }, status=404)

#         except Exception as e:
#             print(f"Profile fetch error: {str(e)}")
#             return Response({
#                 'success': False,
#                 'message': 'Failed to fetch profile'
#             }, status=500)

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
# original
# class UpdateResidentProfileView(APIView):
#     """
#     Update resident profile using update_resident or update_business_owner database functions
#     """
#     parser_classes = (MultiPartParser, FormParser)
    
#     def post(self, request, resident_id):
#         print(f"Updating profile for resident_id: {resident_id}")
        
#         try:
#             # Get current user session to use as request_by
#             request_by = resident_id  # For now, user updates their own profile
            
#             # Get the current resident's status to determine which function to use
#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     SELECT rs.status_name 
#                     FROM Resident r 
#                     JOIN Resident_Status rs ON r.status_id = rs.status_id 
#                     WHERE r.resident_id = %s
#                 """, [resident_id])
                
#                 result = cursor.fetchone()
#                 if not result:
#                     return Response({
#                         'success': False,
#                         'message': 'Resident not found'
#                     }, status=404)
                
#                 status_name = result[0].lower()
#                 print(f"Resident status: {status_name}")
            
#             # Extract form data
#             data = request.data
#             print(f"Update data received: {list(data.keys())}")
            
#             # Handle profile image upload if provided
#             profile_image_path = None
#             if 'profile_image' in request.FILES:
#                 print("Profile image detected, uploading to Supabase...")
#                 profile_image_path = self.upload_profile_image(request.FILES['profile_image'], resident_id)
#                 print(f"Profile image uploaded: {profile_image_path}")
            
#             # Get current resident data for required fields
#             with connection.cursor() as cursor:
#                 cursor.execute("""
#                     SELECT r.first_name, r.last_name, r.dob, r.sex, a.barangay, a.city_municipality
#                     FROM Resident r 
#                     LEFT JOIN Address a ON r.address_id = a.address_id
#                     WHERE r.resident_id = %s
#                 """, [resident_id])
                
#                 current_data = cursor.fetchone()
#                 if not current_data:
#                     return Response({
#                         'success': False,
#                         'message': 'Resident data not found'
#                     }, status=404)
                
#                 current_first_name, current_last_name, current_dob, current_sex, current_barangay, current_city = current_data
            
#             # Prepare parameters based on resident type
#             if status_name == 'non-resident':
#                 # Use update_business_owner function for non-residents
#                 print("Using update_business_owner function for non-resident")
                
#                 with connection.cursor() as cursor:
#                     cursor.execute("""
#                         SELECT update_business_owner(
#                             %s, %s, %s, %s, %s, %s, %s, %s,
#                             %s, %s, %s, %s, %s, %s, %s, %s
#                         )
#                     """, [
#                         resident_id,                           # p_resident_id
#                         request_by,                            # p_request_by
#                         current_last_name,                     # p_last_name (unchanged)
#                         current_first_name,                    # p_first_name (unchanged)
#                         current_dob,                           # p_dob (unchanged)
#                         current_sex,                           # p_sex (unchanged)
#                         data.get('barangay', current_barangay),                # p_barangay
#                         data.get('city_municipality', current_city),           # p_city_municipality
#                         None,                                  # p_middle_name (unchanged for non-residents)
#                         None,                                  # p_suffix (unchanged for non-residents)
#                         data.get('email'),                     # p_email
#                         data.get('phone_number'),              # p_phone_number
#                         data.get('house_number'),              # p_house_number
#                         data.get('street'),                    # p_street
#                         data.get('country', 'Philippines'),    # p_country
#                         profile_image_path                     # p_profile_image_path
#                     ])
#             else:
#                 # Use update_resident function for residents (REMOVED is_voter parameter)
#                 print("Using update_resident function for resident")
                
#                 with connection.cursor() as cursor:
#                     cursor.execute("""
#                         SELECT update_resident(
#                             %s, %s, %s, %s, %s, %s, %s, %s,
#                             %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
#                         )
#                     """, [
#                         resident_id,                           # p_resident_id
#                         request_by,                            # p_request_by
#                         current_last_name,                     # p_last_name (unchanged)
#                         current_first_name,                    # p_first_name (unchanged)
#                         current_dob,                           # p_dob (unchanged)
#                         current_sex,                           # p_sex (unchanged)
#                         current_barangay,                      # p_barangay (unchanged for residents)
#                         current_city,                          # p_city_municipality (unchanged for residents)
#                         None,                                  # p_middle_name (unchanged)
#                         None,                                  # p_suffix (unchanged)
#                         data.get('gender'),                    # p_gender
#                         False,                                 # p_is_voter (HIDDEN: default to False)
#                         data.get('email'),                     # p_email
#                         data.get('phone_number'),              # p_phone_number
#                         data.get('religion_cat_id'),           # p_religion_cat_id
#                         data.get('other_religion'),            # p_other_religion
#                         data.get('civil_stat_id'),             # p_civil_stat_id
#                         data.get('educational_attain_id'),     # p_educational_attain_id
#                         data.get('house_number'),              # p_house_number
#                         data.get('street'),                    # p_street
#                         None,                                  # p_sitio_id (unchanged)
#                         'Philippines',                         # p_country (unchanged)
#                         profile_image_path                     # p_profile_image_path
#                     ])
            
#             print("Profile update successful")
#             return Response({
#                 'success': True,
#                 'message': 'Profile updated successfully',
#                 'profile_image_url': profile_image_path if profile_image_path else None
#             }, status=200)
            
#         except Exception as e:
#             print(f" Profile update error: {str(e)}")
#             return Response({
#                 'success': False,
#                 'message': f'Failed to update profile: {str(e)}'
#             }, status=500)
    
#     def upload_profile_image(self, image_file, resident_id):
#         """
#         Upload profile image to Supabase Storage using existing upload_file_to_supabase function
#         """
#         try:
#             # print(f" Starting profile image upload for resident {resident_id}")
            
          
#             supabase_path = upload_file_to_supabase(
#                 file=image_file,
#                 bucket_name='profile-images',  
#                 folder='profile_images'       
#             )
            
#             # print(f"Supabase upload returned: {supabase_path}")
#             # print(f"Upload result type: {type(supabase_path)}")
            
#             if supabase_path:
#                 # Check if it's already a full URL or just a path
#                 if supabase_path.startswith('http'):
#                     # Already a full URL
#                     public_url = supabase_path
#                 else:
#                     # Construct the public URL
#                     base_url = os.getenv('SUPABASE_URL')
#                     public_url = f"{base_url}/storage/v1/object/public/profile-images/{supabase_path}"
                
#                 print(f"Final public URL: {public_url}")
#                 return public_url
#             else:
#                 raise Exception("Upload failed - no path returned from Supabase")
                
#         except ImportError as ie:
#             print(f"Import error: {str(ie)}")
#             raise Exception("Supabase storage function not available")
#         except Exception as e:
#             print(f"Image upload error: {str(e)}")
#             raise Exception(f"Failed to upload profile image: {str(e)}")
   
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


# MOBILE DEFAULT PERSONNEL CHANGE PASSWORD
# original
# class ChangePersonnelPasswordView(APIView):
#     """
#     Change personnel default password
#     """
#     def post(self, request):
#         print("Personnel password change attempt")

#         try:
#             # get request data
#             personnel_id = request.data.get('personnel_id')
#             old_password = request.data.get('old_password')
#             new_password = request.data.get('new_password')

#             print(f"Password change for personnel_id: {personnel_id}")

#             # validate required fields
#             if not all([personnel_id, old_password, new_password]):
#                 return Response({
#                     'success': False,
#                     'message': 'Personnel ID, old password, and new password are required.'
#                 }, status=400)
            
#             # call database function
#             with connection.cursor() as cursor:
#                 cursor.execute(""" SELECT change_personnel_default_password (%s, %s, %s)""", [personnel_id, old_password, new_password])

#                 result = cursor.fetchone()[0]
#                 print(f"Password change result: {result}")
            
#             return Response({
#                 'success': True,
#                 'message': result
#             }, status=200)


#         except Exception as e:
#             error_message = str(e)
#             print(f"Password change error: {error_message}")

#             # Handle specific database errors
#             if 'E6015' in error_message:
#                 message = 'Personnel not found'
#             elif 'E6016' in error_message:
#                 message = 'Incorrect current password'
#             elif 'E6017' in error_message:
#                 message = 'New password must be at least 8 characters'
#             elif 'E6018' in error_message:
#                 message = 'New password must be different from current password'
#             else:
#                 message = 'Failed to change password. Please try again.'
            
#             return Response({
#                 'success': False,
#                 'message': message
#             }, status=400)

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