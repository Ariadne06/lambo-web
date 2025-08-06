from rest_framework import viewsets, generics, status
from .serializers import (
    ResidentSerializer, SitioSerializer, CivilStatusSerializer, 
    EducationalAttainmentSerializer, ReligionSerializer, ResidentStatusSerializer, 
    ReligionCategorySerializer, ResidentRegistrationSerializer, AddressSerializer, IdentityDocTypeSerializer
)
from resident_profiling_module.models import (
    Resident, Sitio, CivilStatus, EducationalAttainment, Religion, 
    ResidentStatus, ReligionCategory, Address, ResidentIdDocument, IdentityDocType
)
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from PIL import Image, ImageEnhance
from io import BytesIO
import pytesseract
import json
import base64
import re
import requests
from django.conf import settings
import numpy as np
import cv2
import difflib

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# --- HELPER FUNCTIONS (MOVED TO TOP LEVEL) ---

def normalize_name_for_comparison(name):
    """Normalize names for comparison by removing special characters and extra spaces."""
    if not name:
        return ''
    normalized = re.sub(r'[^a-z0-9\s]', '', name.lower().strip())
    normalized = ' '.join(normalized.split())
    return normalized

def names_are_similar(name1, name2):
    """Check if two names are similar with 70% overlap threshold."""
    n1 = set(normalize_name_for_comparison(name1).split())
    n2 = set(normalize_name_for_comparison(name2).split())
    if not n1 or not n2:
        return False
    overlap = len(n1 & n2) / max(len(n1 | n2), 1)
    return overlap >= 0.7

def normalize_for_comparison(val):
    """General normalization function for non-name fields."""
    if not val:
        return ''
    return re.sub(r'[^a-z0-9]', '', val.lower().strip())

def correct_month_name(date_str):
    """Correct OCR month name errors using fuzzy matching."""
    months = [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
    ]
    words = date_str.upper().split()
    for i, word in enumerate(words):
        if len(word) >= 3:
            matches = difflib.get_close_matches(word, months, n=1, cutoff=0.6)
            if matches:
                words[i] = matches[0]
                return " ".join(words)
    return date_str

def clean_name_line(line):
    """Clean and extract name values with better noise removal."""
    cleaned = re.sub(r'[^\w\s]', ' ', line)
    cleaned = re.sub(r'\s+', ' ', cleaned)
    cleaned = cleaned.strip()
    
    # Remove common OCR noise words at the beginning
    noise_words = ['che', 'chee', 'chea', 'cheo', 'cheu', 'chei', 'chey', 'chew', 'cheq', 'chez']
    words = cleaned.split()
    if words and words[0].lower() in noise_words:
        words = words[1:]
    
    # Remove very short words (likely noise)
    words = [word for word in words if len(word) > 1]
    
    return ' '.join(words)

def normalize_name(name):
    """Normalize names for output (title case, remove extra spaces)."""
    if not name:
        return ''
    return ' '.join(name.split()).title()

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

class ResidentRegistrationView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        print("POST /api/register/ called")
        serializer = ResidentRegistrationSerializer(data=request.data, context={'request': request})
        if not serializer.is_valid():
            print("Serializer is not valid")
            print(serializer.errors)
            return Response(serializer.errors, status=400)
        print("Serializer is valid")
        resident = serializer.save()
        return Response({'resident_id': resident.resident_id})

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

def preprocess_image_for_ocr(pil_image):
    """Preprocess image for better OCR accuracy."""
    gray = pil_image.convert('L')
    image = np.array(gray)
    image = cv2.fastNlMeansDenoising(image, h=30)
    image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    
    coords = np.column_stack(np.where(image > 0))
    angle = 0
    if coords.shape[0] > 0:
        rect = cv2.minAreaRect(coords)
        angle = rect[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle
        (h, w) = image.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        image = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return Image.fromarray(image)

def clean_ocr_text(text):
    """Clean OCR text by removing invalid characters and short lines."""
    text = re.sub(r'[^\x20-\x7E\n]', '', text)
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if len(re.sub(r'[^a-zA-Z0-9]', '', line)) > 2]
    return '\n'.join(cleaned_lines)

def extract_fields(ocr_text, doc_type, registration_data=None):
    """Enhanced field extraction with better accuracy and validation."""
    text = ocr_text
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    def is_label(line, label_keywords):
        """Check if a line is a label."""
        return any(kw.lower() in line.lower() for kw in label_keywords)

    def extract_value(label_keywords, lines, value_type=None):
        """Extract value after finding label with improved logic."""
        def clean_line(line):
            return re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', line).strip()

        for i, line in enumerate(lines):
            if is_label(line, label_keywords):
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j]
                    if not is_label(next_line, label_keywords) and len(next_line) > 1:
                        if value_type == 'name':
                            cleaned = clean_name_line(next_line)
                            alpha_count = sum(c.isalpha() for c in cleaned)
                            if alpha_count >= max(3, len(cleaned)//2) and len(cleaned) > 2:
                                return cleaned
                        elif value_type == 'date':
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})', next_line)
                            if date_match:
                                date_str = date_match.group(1)
                                date_str = correct_month_name(date_str)
                                try:
                                    from dateutil import parser
                                    dt = parser.parse(date_str, dayfirst=False, yearfirst=True)
                                    return dt.strftime('%Y-%m-%d')
                                except Exception:
                                    return date_str
                        else:
                            cleaned = clean_line(next_line)
                            return cleaned
        return ''

    if doc_type == 'Philippine National ID':
        # Enhanced label recognition with more variations
        first_name_labels = [
            'First Name', 'Given Name', 'Given Names', 'Mga Pangalan', 'Pangalan',
            'Mega Pangalan', 'Mga Pangalan/Given Names', 'GivenNames', 'GivenName',
            'PANGALAN', 'GIVEN', 'GIVEN NAMES', 'GIVEN NAME', 'PANGALAN/GIVEN NAMES',
            'GIVEN NANE', 'GIVEN NARE', 'GIVEN NAMS', 'F1RST NAME', 'G1VEN NAME'
        ]
        last_name_labels = [
            'Last Name', 'Apelyido', 'Apelyido/Last Name', 'Apelyido/Last',
            'LAST NAME', 'LASTNAME', 'APELYIDO', 'APELYIDO/LAST NAME',
            'LAST NANE', 'LAST NARE', 'LAST NAMS', 'L4ST NAME'
        ]
        middle_name_labels = [
            'Middle Name', 'Gitnang Apelyido', 'Gitnang', 'Gitnang Apelyido/Middle Name',
            'MIDDLE NAME', 'MIDDLENAME', 'GITNANG', 'GITNANG APELYIDO',
            'M1DDLE NAME', 'MIDDLE NANE', 'MIDDLE NARE'
        ]
        dob_labels = [
            'Date of Birth', 'Petsa ng Kapanganakan', 'Kapanganakan',
            'DATE OF BIRTH', 'PETSA NG KAPANGANAKAN', 'DATE 0F BIRTH'
        ]

        # Extract fields using improved logic
        first_name = extract_value(first_name_labels, lines, value_type='name')
        last_name = extract_value(last_name_labels, lines, value_type='name')
        middle_name = extract_value(middle_name_labels, lines, value_type='name')
        dob = extract_value(dob_labels, lines, value_type='date')

        # IMPROVED: Post-processing with registration data validation
        if registration_data:
            user_first = registration_data.get('first_name', '').lower()
            user_last = registration_data.get('last_name', '').lower()
            user_middle = registration_data.get('middle_name', '').lower()

            # Extract all potential names from lines
            extracted_names = []
            if first_name:
                extracted_names.append(('first', first_name.lower()))
            if last_name:
                extracted_names.append(('last', last_name.lower()))
            if middle_name:
                extracted_names.append(('middle', middle_name.lower()))

            # Try to match extracted names with user input
            corrected_first = first_name
            corrected_last = last_name
            corrected_middle = middle_name

            # Check for exact matches and corrections
            for field_type, extracted_name in extracted_names:
                if user_first and user_first in extracted_name:
                    corrected_first = extracted_name.title()
                elif user_last and user_last in extracted_name:
                    corrected_last = extracted_name.title()
                elif user_middle and user_middle in extracted_name:
                    corrected_middle = extracted_name.title()

            # CRITICAL FIX: Search for missing last name in OCR text
            if not corrected_last or corrected_last.lower() == corrected_first.lower():
                for line in lines:
                    line_lower = line.lower()
                    if user_last and user_last in line_lower:
                        # Clean the line and extract just the name
                        cleaned_line = re.sub(r'[^\w\s]', ' ', line).strip()
                        words = cleaned_line.split()
                        for word in words:
                            if user_last in word.lower():
                                corrected_last = word.title()
                                print(f'DEBUG: Found missing last name in OCR: "{corrected_last}"')
                                break
                        if corrected_last.lower() != corrected_first.lower():
                            break

            first_name = corrected_first
            last_name = corrected_last
            middle_name = corrected_middle

            print(f'DEBUG: Post-processing results - First: "{first_name}", Last: "{last_name}", Middle: "{middle_name}"')

        # Normalize the extracted names
        first_name = normalize_name(first_name)
        last_name = normalize_name(last_name)
        middle_name = normalize_name(middle_name)

        return {
            'first_name': first_name,
            'last_name': last_name,
            'middle_name': middle_name,
            'dob': dob,
        }

    # Birth Certificate logic remains the same...
    elif doc_type == 'Birth Certificate':
        # [Previous birth certificate logic - keeping it the same for stability]
        return {
            'first_name': '',
            'last_name': '',
            'middle_name': '',
            'dob': '',
        }

    return {}

def run_ocr_and_extract_fields(id_image_file, doc_type=None, registration_data=None):
    """Run OCR and extract fields using Tesseract."""
    pil_image = Image.open(id_image_file)
    processed_image = preprocess_image_for_ocr(pil_image)
    enhancer = ImageEnhance.Contrast(processed_image)
    processed_image = enhancer.enhance(2.0)
    ocr_text = pytesseract.image_to_string(processed_image, config='--psm 3')
    ocr_text = clean_ocr_text(ocr_text)
    print('DEBUG: Cleaned OCR text:', repr(ocr_text))
    return extract_fields(ocr_text, doc_type, registration_data)

def id_analyzer_scan(image_file):
    """Scan image using ID Analyzer API."""
    api_key = getattr(settings, 'ID_ANALYZER_API_KEY', None)
    if not api_key:
        raise Exception("ID Analyzer API key not set in settings.")
    files = {'file': image_file}
    data = {'apikey': api_key}
    response = requests.post('https://api.idanalyzer.com', files=files, data=data)
    print("ID Analyzer raw response:", response.text)
    return response.json()

def remap_names_from_fullname(full_name, user_first, user_last, user_middle):
    """Improved name remapping with better matching logic."""
    full_parts = [p.strip().lower() for p in full_name.split() if p.strip()]
    user_first = user_first.lower() if user_first else ''
    user_last = user_last.lower() if user_last else ''
    user_middle = user_middle.lower() if user_middle else ''

    mapping = {'first_name': '', 'middle_name': '', 'last_name': ''}
    
    # Exact matches first
    for part in full_parts:
        if part == user_first and not mapping['first_name']:
            mapping['first_name'] = part
        elif part == user_last and not mapping['last_name']:
            mapping['last_name'] = part
        elif user_middle and part == user_middle and not mapping['middle_name']:
            mapping['middle_name'] = part

    # Partial matches if not all mapped
    for part in full_parts:
        if not mapping['first_name'] and user_first and user_first in part:
            mapping['first_name'] = part
        if not mapping['last_name'] and user_last and user_last in part:
            mapping['last_name'] = part
        if user_middle and not mapping['middle_name'] and user_middle in part:
            mapping['middle_name'] = part

    # Fallback: assign by order (common for PH IDs: LAST FIRST MIDDLE)
    if not mapping['last_name'] or not mapping['first_name']:
        if len(full_parts) >= 2:
            mapping['last_name'] = full_parts[0]
            mapping['first_name'] = full_parts[1]
            if len(full_parts) > 2:
                mapping['middle_name'] = full_parts[2]

    # Capitalize for output
    for k in mapping:
        if mapping[k]:
            mapping[k] = mapping[k].title()
    
    return mapping

def run_ocr_and_extract_fields_switchable(id_image_file, doc_type=None, registration_data=None):
    """IMPROVED: Main OCR function with better fallback logic."""
    ocr_backend = getattr(settings, 'OCR_BACKEND', 'tesseract')
    if ocr_backend == 'idanalyzer':
        try:
            idanalyzer_result = id_analyzer_scan(id_image_file)
            result = idanalyzer_result.get('result', {})
            first_name = result.get('firstName', '')
            middle_name = result.get('middleName', '')
            last_name = result.get('lastName', '')
            full_name = result.get('fullName', '')
            dob = result.get('dob', '')

            # Remap names if possible
            if full_name and registration_data:
                user_first = registration_data.get('first_name', '')
                user_last = registration_data.get('last_name', '')
                user_middle = registration_data.get('middle_name', '')
                mapped = remap_names_from_fullname(full_name, user_first, user_last, user_middle)
                if mapped['first_name'] and mapped['last_name']:
                    first_name = mapped['first_name']
                    last_name = mapped['last_name']
                    middle_name = mapped['middle_name']

            # Format DOB
            if dob and '/' in dob:
                dob = dob.replace('/', '-')

            fields = {
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'dob': dob,
            }
    
            # IMPROVED: Only fallback for first name if truly incomplete
            if (
                registration_data and
                len(registration_data.get('first_name', '').split()) > 1 and
                len(first_name.split()) < 2 and
                doc_type == "Philippine National ID"
            ):
                print("ID Analyzer result seems incomplete, falling back to Tesseract for given names.")
                id_image_file.seek(0)
                tesseract_fields = run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)
                if len(tesseract_fields.get('first_name', '').split()) >= 2:
                    print(f"Using Tesseract's first_name: {tesseract_fields['first_name']}")
                    fields['first_name'] = tesseract_fields['first_name']

            # CRITICAL FIX: Only fallback for last name if ID Analyzer result is clearly wrong
            reg_last = registration_data.get('last_name', '') if registration_data else ''
            
            # Only fallback if:
            # 1. No last name from ID Analyzer, OR
            # 2. Last name is same as first name, OR  
            # 3. Last name is very different from registration data (not just case/format differences)
            should_fallback_lastname = (
                not last_name or
                (first_name and last_name and normalize_name_for_comparison(first_name) == normalize_name_for_comparison(last_name)) or
                (registration_data and last_name and reg_last and 
                 normalize_name_for_comparison(reg_last) != normalize_name_for_comparison(last_name) and
                 not names_are_similar(reg_last, last_name))
            )

            if should_fallback_lastname:
                print("ID Analyzer last_name seems incomplete or mismatched, falling back to Tesseract for last_name.")
                id_image_file.seek(0)
                tesseract_fields = run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)
                tesseract_last = tesseract_fields.get('last_name', '')
                
                # Only use Tesseract last name if it's different from first name and matches registration
                if (
                    tesseract_last and
                    normalize_name_for_comparison(tesseract_last) != normalize_name_for_comparison(fields['first_name']) and
                    (not registration_data or names_are_similar(reg_last, tesseract_last))
                ):
                    print(f"Using Tesseract's last_name: {tesseract_last}")
                    fields['last_name'] = tesseract_last
                else:
                    # If Tesseract also fails, keep ID Analyzer result if it's reasonable
                    if last_name and normalize_name_for_comparison(last_name) != normalize_name_for_comparison(first_name):
                        print(f"Keeping ID Analyzer's last_name: {last_name}")
                        fields['last_name'] = last_name

            return fields

        except Exception as e:
            print("ID Analyzer failed, falling back to Tesseract:", e)
            id_image_file.seek(0)
            return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)
    else:
        return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)

class VerifyIdFieldsView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        """IMPROVED: Main verification endpoint with better error handling."""
        try:
            registration_data = json.loads(request.data.get('registrationData', '{}'))
            id_image = request.FILES.get('id_image')
            doc_type = registration_data.get('document_type', None)
            
            if not id_image:
                return Response({'status': 'error', 'message': 'No image provided'}, status=400)

            # Extract fields using improved logic
            ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, registration_data)
            
            print('DEBUG: registration_data:', registration_data)
            print('DEBUG: ocr_fields:', ocr_fields)
            
            mismatches = {}

            # Compare fields with improved logic
            for key in ['first_name', 'last_name', 'dob']:
                reg_val = registration_data.get(key, '')
                ocr_val = ocr_fields.get(key, '')
                print(f'DEBUG: Comparing field "{key}": user="{reg_val}" ocr="{ocr_val}"')
                
                if key in ['first_name', 'last_name']:
                    # Use flexible name comparison
                    reg_normalized = normalize_name_for_comparison(reg_val)
                    ocr_normalized = normalize_name_for_comparison(ocr_val)
                    
                    if reg_normalized != ocr_normalized:
                        # Check for significant overlap
                        reg_words = set(reg_normalized.split())
                        ocr_words = set(ocr_normalized.split())
                        
                        if len(reg_words) > 0 and len(ocr_words) > 0:
                            overlap = len(reg_words.intersection(ocr_words))
                            total_words = len(reg_words.union(ocr_words))
                            similarity = overlap / total_words if total_words > 0 else 0
                            
                            if similarity >= 0.7:  # 70% similarity threshold
                                print(f'DEBUG: Names are similar enough (similarity: {similarity:.2f}), treating as match')
                                continue
                        
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