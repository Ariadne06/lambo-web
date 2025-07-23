from rest_framework import viewsets, generics, status
from .serializers import ResidentSerializer, SitioSerializer, CivilStatusSerializer, EducationalAttainmentSerializer, ReligionSerializer, ResidentStatusSerializer, ReligionCategorySerializer, ResidentRegistrationSerializer, AddressSerializer
from resident_profiling_module.models import Resident, Sitio, CivilStatus, EducationalAttainment, Religion, ResidentStatus, ReligionCategory, Address, ResidentIdDocument
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



pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

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
        # No need to parse registrationData or get id_image from request.FILES
        resident = serializer.save()
        return Response({'resident_id': resident.resident_id})

# class ResidentIdDocumentUploadView(generics.CreateAPIView):
#     queryset = ResidentIdDocument.objects.all()
#     serializer_class = ResidentIdDocumentSerializer

def extract_fields(ocr_text, doc_type, registration_data=None):
    import re
    text = ocr_text
    lines = [l.strip() for l in text.split('\n') if l.strip()]

    # Helper: check if a line is a label (e.g., 'First Name', 'Apelyido', etc.)
    def is_label(line, label_keywords):
        for kw in label_keywords:
            if kw.lower() in line.lower():
                return True
        return False

    # Helper: clean and extract name values with better noise removal
    def clean_name_line(line):
        # Remove common OCR noise and artifacts
        cleaned = re.sub(r'[^\w\s]', ' ', line)  # Remove special characters except spaces
        cleaned = re.sub(r'\s+', ' ', cleaned)   # Normalize multiple spaces
        cleaned = cleaned.strip()
        
        # Remove common OCR noise words at the beginning
        noise_words = ['che', 'chee', 'chea', 'cheo', 'cheu', 'chei', 'chey', 'chew', 'cheq', 'chez']
        words = cleaned.split()
        if words and words[0].lower() in noise_words:
            words = words[1:]
        
        # Remove very short words (likely noise)
        words = [word for word in words if len(word) > 1]
        
        return ' '.join(words)

    # Helper: normalize names for comparison (remove extra spaces, convert to title case)
    def normalize_name(name):
        if not name:
            return ''
        # Remove extra spaces and convert to title case
        normalized = ' '.join(name.split()).title()
        return normalized

    # Helper: get value after colon or on next line, with improved logic
    def extract_value(label_keywords, lines, value_type=None):
        def clean_line(line):
            # Remove leading/trailing non-alphabetic characters and extra spaces
            return re.sub(r'^[^a-zA-Z0-9]+|[^a-zA-Z0-9]+$', '', line).strip()

        for i, line in enumerate(lines):
            if is_label(line, label_keywords):
                # Check up to 3 lines after the label
                for j in range(i+1, min(i+4, len(lines))):
                    next_line = lines[j]
                    if not is_label(next_line, label_keywords) and len(next_line) > 1:
                        if value_type == 'name':
                            # Use improved name cleaning
                            cleaned = clean_name_line(next_line)
                            # Only accept if mostly alphabetic and not a label
                            alpha_count = sum(c.isalpha() for c in cleaned)
                            if alpha_count >= max(3, len(cleaned)//2) and len(cleaned) > 2:
                                return cleaned
                        elif value_type == 'date':
                            # Extract date from the line
                            date_match = re.search(r'(\d{4}-\d{2}-\d{2}|[A-Za-z]+\s+\d{1,2},\s*\d{4}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-\d{1,2}-\d{4})', next_line)
                            if date_match:
                                date_str = date_match.group(1)
                                # Correct month name if needed
                                date_str = correct_month_name(date_str)
                                from dateutil import parser
                                try:
                                    dt = parser.parse(date_str, dayfirst=False, yearfirst=True)
                                    return dt.strftime('%Y-%m-%d')
                                except Exception:
                                    return date_str
                        else:
                            cleaned = clean_line(next_line)
                            return cleaned
        return ''

    # Helper: fallback to plausible value (longest line, not a label)
    def plausible_value(label_keywords, lines):
        candidates = [l for l in lines if not is_label(l, label_keywords) and len(l) > 2]
        if candidates:
            return max(candidates, key=len)
        return ''

    if doc_type == 'Philippine National ID':
        # Expanded label permutations for each field (English, Filipino, common OCR errors, and common misspellings/near-similar)
        # These include common OCR misreads like 'GIVEN NANE', 'F1RST NAME', 'G1VEN NAME', etc.
        first_name_labels = [
            'First Name', 'Given Name', 'Given Names', 'Mga Pangalan', 'Pangalan',
            'Mega Pangalan', 'Mga Pangalan/Given Names', 'GivenNames', 'GivenName',
            'PANGALAN', 'GIVEN', 'GIVEN NAMES', 'GIVEN NAME', 'PANGALAN/GIVEN NAMES',
            'Mga Pangalan/Given Names', 'Mga Pangalan/GivenName', 'Mga Pangalan/GivenNames',
            'PANGALAN/GIVEN', 'PANGALAN/GIVEN NAMES', 'PANGALAN/GIVEN NAME',
            # Common OCR misspellings and near-similar
            'GIVEN NANE', 'GIVEN NARE', 'GIVEN NAMS', 'GIVEN NAMES', 'GIVEN NANE',
            'F1RST NAME', 'F1RST NANE', 'F1RST NARE', 'F1RST NAMS', 'F1RST NAMES',
            'G1VEN NAME', 'G1VEN NANE', 'G1VEN NARE', 'G1VEN NAMS', 'G1VEN NAMES',
            'GIVEN NANE', 'GIVEN NARE', 'GIVEN NAMS', 'GIVEN NAMES',
            'GIVENNAME', 'GIVENNAMES', 'GIVENNANE', 'GIVENNARE', 'GIVENNAMS',
            'GIVEN NANE', 'GIVEN NARE', 'GIVEN NAMS', 'GIVEN NAMES',
            'GIVENNAME', 'GIVENNAMES', 'GIVENNANE', 'GIVENNARE', 'GIVENNAMS',
            'GIVEN NANE', 'GIVEN NARE', 'GIVEN NAMS', 'GIVEN NAMES',
            'GIVENNAME', 'GIVENNAMES', 'GIVENNANE', 'GIVENNARE', 'GIVENNAMS',
            'GIVEN NANE', 'GIVEN NARE', 'GIVEN NAMS', 'GIVEN NAMES',
            'GIVENNAME', 'GIVENNAMES', 'GIVENNANE', 'GIVENNARE', 'GIVENNAMS',
            
        ]
        last_name_labels = [
            'Last Name', 'Apelyido', 'Apelyido/Last Name', 'Apelyido/Last',
            'LAST NAME', 'LASTNAME', 'APELYIDO', 'APELYIDO/LAST NAME',
            'Apelyido/LastName', 'Apelyido/Last', 'Apelyido',
            # Common OCR misspellings
            'LAST NANE', 'LAST NARE', 'LAST NAMS', 'LAST NAMES',
            'L4ST NAME', 'L4ST NANE', 'L4ST NARE', 'L4ST NAMS', 'L4ST NAMES',
        ]
        middle_name_labels = [
            'Middle Name', 'Gitnang Apelyido', 'Gitnang', 'Gitnang Apelyido/Middle Name',
            'MIDDLE NAME', 'MIDDLENAME', 'GITNANG', 'GITNANG APELYIDO',
            'Gitnang Apelyido/MiddleName', 'Gitnang Apelyido/Middle',
            # Common OCR misspellings
            'M1DDLE NAME', 'M1DDLE NANE', 'M1DDLE NARE', 'M1DDLE NAMS', 'M1DDLE NAMES',
            'MIDDLE NANE', 'MIDDLE NARE', 'MIDDLE NAMS', 'MIDDLE NAMES',
        ]
        dob_labels = [
            'Date of Birth', 'Petsa ng Kapanganakan', 'Kapanganakan',
            'Vetsa ng Kapanganakan', 'Date of Birt', 'Date of Birth!', 'Date ofBirth',
            'DATE OF BIRTH', 'PETSA NG KAPANGANAKAN', 'KAPANGANAKAN',
            'VETSA NG KAPANGANAKAN', 'DATE OF BIRT', 'DATE OF BIRTH!', 'DATE OFBIRTH',
            # Common OCR misspellings
            'DATE 0F BIRTH', 'DATE 0F BIRT', 'DATE 0F B1RTH', 'DATE 0F B1RT',
            'D4TE OF BIRTH', 'D4TE OF BIRT', 'D4TE OF B1RTH', 'D4TE OF B1RT',
            'DATE OF B1RTH', 'DATE OF B1RT', 'DATE OF B1RTH!', 'DATE OFB1RTH',
        ]

        first_name = extract_value(first_name_labels, lines, value_type='name')
        if not first_name:
            first_name = plausible_value(first_name_labels, lines)
        last_name = extract_value(last_name_labels, lines, value_type='name')
        if not last_name:
            last_name = plausible_value(last_name_labels, lines)
        middle_name = extract_value(middle_name_labels, lines, value_type='name')
        if not middle_name:
            middle_name = plausible_value(middle_name_labels, lines)
        dob = extract_value(dob_labels, lines, value_type='date')
        if not dob:
            dob = plausible_value(dob_labels, lines)
        
        # NEW: Post-processing to fix common extraction issues
        # If we have registration data, use it to validate and correct the extracted fields
        if registration_data:
            user_first = registration_data.get('first_name', '').lower()
            user_last = registration_data.get('last_name', '').lower()
            user_middle = registration_data.get('middle_name', '').lower()
            
            # Check if we have the right names but they're assigned to wrong fields
            extracted_names = []
            if first_name:
                extracted_names.append(('first', first_name.lower()))
            if last_name:
                extracted_names.append(('last', last_name.lower()))
            if middle_name:
                extracted_names.append(('middle', middle_name.lower()))
            
            # Try to match extracted names with user input
            corrected_first = ''
            corrected_last = ''
            corrected_middle = ''
            
            for field_type, extracted_name in extracted_names:
                # Check for exact matches first
                if user_first and extracted_name == user_first:
                    corrected_first = extracted_name
                elif user_last and extracted_name == user_last:
                    corrected_last = extracted_name
                elif user_middle and extracted_name == user_middle:
                    corrected_middle = extracted_name
                # Check for partial matches and OCR variations
                elif user_first and (user_first in extracted_name or extracted_name in user_first):
                    corrected_first = extracted_name
                elif user_last and (user_last in extracted_name or extracted_name in user_last):
                    corrected_last = extracted_name
                elif user_middle and (user_middle in extracted_name or extracted_name in user_middle):
                    corrected_middle = extracted_name
            
            # If we found corrections, use them
            if corrected_first:
                first_name = corrected_first.title()
            if corrected_last:
                last_name = corrected_last.title()
            if corrected_middle:
                middle_name = corrected_middle.title()
            
            # NEW: If we're missing the last name, search for it in the OCR text
            if not corrected_last and user_last:
                for line in lines:
                    line_lower = line.lower()
                    # Look for the last name in the OCR text
                    if user_last in line_lower:
                        # Clean the line and extract just the name
                        cleaned_line = re.sub(r'[^\w\s]', ' ', line).strip()
                        words = cleaned_line.split()
                        for word in words:
                            if user_last in word.lower() or word.lower() in user_last:
                                last_name = word.title()
                                print(f'DEBUG: Found missing last name: "{last_name}"')
                                break
                        if last_name != corrected_last:
                            break
            
            print(f'DEBUG: Post-processing results - First: "{first_name}", Last: "{last_name}", Middle: "{middle_name}"')
        
        # Fix DOB extraction - look for date patterns in the text
        if not dob or len(dob) > 20:  # If DOB is too long, it's probably wrong
            # Look for date patterns in the OCR text
            for line in lines:
                # Look for date patterns like "OCTOBER 06, 2003"
                date_patterns = [
                    r'([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})',  # OCTOBER 06, 2003
                    r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',  # 06 OCTOBER 2003
                    r'(\d{1,2})\/(\d{1,2})\/(\d{4})',      # 06/10/2003
                    r'(\d{1,2})-(\d{1,2})-(\d{4})',        # 06-10-2003
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, line)
                    if match:
                        try:
                            if len(match.groups()) == 3:
                                if match.group(1).isalpha():
                                    # Format: OCTOBER 06, 2003
                                    month_str = match.group(1)
                                    day = match.group(2)
                                    year = match.group(3)
                                else:
                                    # Format: 06 OCTOBER 2003
                                    day = match.group(1)
                                    month_str = match.group(2)
                                    year = match.group(3)
                                
                                # Correct month name if needed
                                month_str = correct_month_name(month_str)
                                from dateutil import parser
                                date_str = f"{day} {month_str} {year}"
                                dt = parser.parse(date_str, dayfirst=False, yearfirst=True)
                                dob = dt.strftime('%Y-%m-%d')
                                print(f'DEBUG: Found DOB using pattern matching: "{dob}"')
                                break
                        except Exception:
                            continue
                if dob and len(dob) <= 20:  # Valid DOB found
                    break
        
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
    elif doc_type == 'Birth Certificate':
        # Philippine Birth Certificate specific labels
        # Looking at the OCR output, we need to find the child's name and date of birth
        
        # Child name labels - look for the actual name fields in the birth certificate
        child_name_labels = [
            '1. NAME OF CHILD', 'NAME OF CHILD', 'CHILD', 'CHILD NAME',
            '1 NAME OF CHILD', 'NAME OF CHILD', 'CHILD NAME',
            # Common OCR variations
            'NAME OF CHILD', 'CHILD NAME', 'CHILD',
            '1 NAME OF CHILD', '1. NAME OF CHILD',
            # Look for patterns that indicate the child's name section
            '1.', '1 ', 'NAME', 'CHILD'
        ]
        
        # Date of birth labels - more comprehensive for birth certificates
        dob_labels = [
            '3. DATE OF BIRTH', 'DATE OF BIRTH', 'BIRTH DATE', 'BIRTH',
            '3 DATE OF BIRTH', 'DATE OF BIRTH', 'BIRTH DATE',
            '3. DATE OF BIRTH', '3 DATE OF BIRTH',
            'DATE OF BIRTH', 'BIRTH DATE', 'BIRTH',
            # Common OCR variations
            'DATE OF B1RTH', 'DATE OF B1RT', 'DATE OF BIRTH',
            'B1RTH DATE', 'B1RT DATE', 'BIRTH DATE',
            # Look for date patterns
            'day', 'month', 'year', 'Octobver', 'October'
        ]
        
        # Extract child name - look for the actual name in the document
        child_name = extract_value(child_name_labels, lines, value_type='name')
        
        # If we can't find the child name through labels, look for name patterns
        if not child_name:
            # Look for lines that look like names (multiple words, mostly alphabetic)
            for line in lines:
                # Skip lines that are clearly labels or numbers
                if any(label.lower() in line.lower() for label in ['date', 'birth', 'place', 'hospital', 'clinic', 'institution']):
                    continue
                if re.match(r'^\d+$', line.strip()):  # Skip pure numbers
                    continue
                
                # Look for lines that could be names (2-4 words, mostly letters)
                words = line.split()
                if 2 <= len(words) <= 4:
                    alpha_count = sum(sum(c.isalpha() for c in word) for word in words)
                    total_chars = sum(len(word) for word in words)
                    if alpha_count / total_chars > 0.7 and total_chars > 5:  # Mostly alphabetic and reasonable length
                        child_name = line
                        break
        
        # Extract date of birth - look for date patterns
        dob = extract_value(dob_labels, lines, value_type='date')
        
        # If we can't find DOB through labels, look for date patterns in the text
        if not dob:
            # Look for date patterns like "6 Octobver/2003" or similar
            for line in lines:
                # Look for date patterns
                date_patterns = [
                    r'(\d{1,2})\s+([A-Za-z]+)\s*\/\s*(\d{4})',  # 6 Octobver/2003
                    r'(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})',      # 6 Octobver 2003
                    r'(\d{1,2})\/(\d{1,2})\/(\d{4})',          # 6/10/2003
                    r'(\d{1,2})-(\d{1,2})-(\d{4})',            # 6-10-2003
                ]
                
                for pattern in date_patterns:
                    match = re.search(pattern, line)
                    if match:
                        try:
                            if len(match.groups()) == 3:
                                day, month, year = match.groups()
                                # Try to parse the date
                                if month.isdigit():
                                    # Numeric month
                                    dob = f"{year}-{int(month):02d}-{int(day):02d}"
                                else:
                                    # Text month - try to parse
                                    date_str = f"{day} {month} {year}"
                                    date_str = correct_month_name(date_str)
                                    from dateutil import parser
                                    dt = parser.parse(date_str, dayfirst=False, yearfirst=True)
                                    dob = dt.strftime('%Y-%m-%d')
                                break
                        except Exception:
                            continue
                if dob:
                    break
        
        # NEW: Fallback extraction using registration data as hints
        # If we still don't have proper names, try to find them in the OCR text using the registration data
        if not child_name or len(child_name.split()) < 2:
            # Get registration data from the parameter
            user_first_name = registration_data.get('first_name', '').lower() if registration_data else ''
            user_last_name = registration_data.get('last_name', '').lower() if registration_data else ''
            user_middle_name = registration_data.get('middle_name', '').lower() if registration_data else ''
            
            # Look for lines that contain the user's names
            best_match_line = None
            best_match_score = 0
            
            for line in lines:
                line_lower = line.lower()
                match_score = 0
                
                # Check if this line contains any of the user's names
                if user_first_name and user_first_name in line_lower:
                    match_score += 1
                if user_last_name and user_last_name in line_lower:
                    match_score += 1
                if user_middle_name and user_middle_name in line_lower:
                    match_score += 1
                
                # If this line has at least 2 matching names, it's likely the name line
                if match_score >= 2:
                    best_match_line = line
                    best_match_score = match_score
                    break
                elif match_score > best_match_score:
                    best_match_line = line
                    best_match_score = match_score
            
            if best_match_line and best_match_score >= 1:
                child_name = best_match_line
                print(f'DEBUG: Found name using registration data hint: "{child_name}" (score: {best_match_score})')
            
            # Additional pattern matching for Birth Certificate format
            # Look for patterns like "(First) ... (Middle) ... (last) ..."
            if not child_name or len(child_name.split()) < 2:
                for line in lines:
                    # Look for the specific pattern we see in the OCR
                    if re.search(r'\(First\)|\(Middle\)|\(last\)|\( Middte\]', line):
                        # This looks like a name line with labels
                        # Extract the actual names by removing the labels
                        cleaned_line = re.sub(r'\([^)]*\)', '', line)  # Remove (First), (Middle), etc.
                        cleaned_line = re.sub(r'[^\w\s]', ' ', cleaned_line)  # Remove special chars
                        cleaned_line = re.sub(r'\s+', ' ', cleaned_line).strip()  # Normalize spaces
                        
                        # Check if this cleaned line contains user names
                        if registration_data:
                            user_names = [user_first_name, user_last_name, user_middle_name]
                            user_names = [name for name in user_names if name]
                            
                            if any(name in cleaned_line.lower() for name in user_names):
                                child_name = cleaned_line
                                print(f'DEBUG: Found name using pattern matching: "{child_name}"')
                                break
        
        # Parse child name into first, last, middle names
        if child_name:
            # Clean the name
            child_name = clean_name_line(child_name) if 'clean_name_line' in locals() else child_name.strip()
            name_parts = child_name.split()
            
            if len(name_parts) >= 2:
                # Assume format: LastName FirstName MiddleName
                last_name = name_parts[0]
                first_name = name_parts[1]
                middle_name = ' '.join(name_parts[2:]) if len(name_parts) > 2 else ''
            else:
                first_name = child_name
                last_name = ''
                middle_name = ''
        else:
            first_name = ''
            last_name = ''
            middle_name = ''
        
        # Normalize names
        first_name = normalize_name(first_name) if 'normalize_name' in locals() else first_name.title()
        last_name = normalize_name(last_name) if 'normalize_name' in locals() else last_name.title()
        middle_name = normalize_name(middle_name) if 'normalize_name' in locals() else middle_name.title()
        
        return {
            'first_name': first_name,
            'last_name': last_name,
            'middle_name': middle_name,
            'dob': dob,
        }
    return {}



class ResidentIdDocumentOCRView(APIView):
    def get(self, request, pk):
        try:
            doc = ResidentIdDocument.objects.get(pk=pk)
            image = Image.open(BytesIO(doc.image_data))
            text = pytesseract.image_to_string(image)
            # Optionally, extract fields here
            return Response({'extracted_text': text})
        except ResidentIdDocument.DoesNotExist:
            return Response({'error': 'Document not found'}, status=404)


def preprocess_image_for_ocr(pil_image):
    import numpy as np
    import cv2
    # 1. Convert to grayscale
    gray = pil_image.convert('L')
    image = np.array(gray)
    # 2. Denoise
    image = cv2.fastNlMeansDenoising(image, h=30)
    # 3. Adaptive thresholding
    image = cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15)
    # 4. Deskew (rotation correction)
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
    text = re.sub(r'[^\x20-\x7E\n]', '', text)
    lines = text.split('\n')
    cleaned_lines = [line for line in lines if len(re.sub(r'[^a-zA-Z0-9]', '', line)) > 2]
    return '\n'.join(cleaned_lines)

def run_ocr_and_extract_fields(id_image_file, doc_type=None, registration_data=None):
    pil_image = Image.open(id_image_file)
    processed_image = preprocess_image_for_ocr(pil_image)
    enhancer = ImageEnhance.Contrast(processed_image)
    processed_image = enhancer.enhance(2.0)
    ocr_text = pytesseract.image_to_string(processed_image, config='--psm 3')
    ocr_text = clean_ocr_text(ocr_text)
    print('DEBUG: Cleaned OCR text:', repr(ocr_text))
    return extract_fields(ocr_text, doc_type, registration_data)

def id_analyzer_scan(image_file):
    api_key = getattr(settings, 'ID_ANALYZER_API_KEY', None)
    if not api_key:
        raise Exception("ID Analyzer API key not set in settings.")
    files = {'file': image_file}
    data = {'apikey': api_key}
    response = requests.post('https://api.idanalyzer.com', files=files, data=data)
    print("ID Analyzer raw response:", response.text)
    return response.json()

def run_ocr_and_extract_fields_switchable(id_image_file, doc_type=None, registration_data=None):
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

        
            # If full_name and last_name are present, extract all given names
            if full_name and last_name and full_name.upper().endswith(last_name.upper()):
                names_part = full_name[:-(len(last_name))].strip()
                # Remove middle name if present and at the end
                if middle_name and names_part.upper().endswith(middle_name.upper()):
                    given_names = names_part[:-(len(middle_name))].strip()
                else:
                    given_names = names_part
                # Use all given names as first_name
                if given_names:
                    first_name = given_names
      

            # Format DOB to use dashes (YYYY-MM-DD)
            if dob and '/' in dob:
                dob = dob.replace('/', '-')

            fields = {
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'dob': dob,
            }

            # Fallback: If first_name is only one word, but full_name minus last_name has more, use that
            if full_name and last_name and full_name.upper().endswith(last_name.upper()):
                names_part = full_name[:-(len(last_name))].strip()
                if middle_name and names_part.upper().endswith(middle_name.upper()):
                    given_names = names_part[:-(len(middle_name))].strip()
                else:
                    given_names = names_part
                if len(given_names.split()) > 1 and len(first_name.split()) < 2 and doc_type == "Philippine National ID":
                    print("ID Analyzer result seems incomplete, using all given names from fullName.")
                    fields['first_name'] = given_names

            if (
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

            return fields
        except Exception as e:
            print("ID Analyzer failed, falling back to Tesseract:", e)
            id_image_file.seek(0)  # Reset file pointer
            return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)
    else:
        return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)


class VerifyIdFieldsView(APIView):
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        import re
        registration_data = json.loads(request.data.get('registrationData', '{}'))
        id_image = request.FILES.get('id_image')
        doc_type = registration_data.get('document_type', None)
        
        # Pass registration data to the extraction function for better name detection
        ocr_fields = run_ocr_and_extract_fields_switchable(id_image, doc_type, registration_data)
        
        print('DEBUG: registration_data:', registration_data)
        print('DEBUG: ocr_fields:', ocr_fields)
        mismatches = {}

        # Helper: normalize values for comparison (remove non-alphanumeric, lowercase, strip)
        def normalize(val):
            if not val:
                return ''
            return re.sub(r'[^a-z0-9]', '', val.lower().strip())

        # Helper: normalize names for comparison (more flexible)
        def normalize_name_for_comparison(name):
            if not name:
                return ''
            # Remove extra spaces, convert to lowercase, remove special characters
            normalized = re.sub(r'[^a-z0-9\s]', '', name.lower().strip())
            # Remove extra spaces
            normalized = ' '.join(normalized.split())
            return normalized

        for key in ['first_name', 'last_name', 'dob']:
            reg_val = registration_data.get(key, '')
            ocr_val = ocr_fields.get(key, '')
            print(f'DEBUG: Comparing field "{key}": user="{reg_val}" ocr="{ocr_val}"')
            
            if key in ['first_name', 'last_name']:
                # Use more flexible name comparison
                reg_normalized = normalize_name_for_comparison(reg_val)
                ocr_normalized = normalize_name_for_comparison(ocr_val)
                
                # Check if names are similar (allowing for minor differences)
                if reg_normalized != ocr_normalized:
                    # Additional check: see if one name contains the other (for multi-word names)
                    reg_words = set(reg_normalized.split())
                    ocr_words = set(ocr_normalized.split())
                    
                    # If there's significant overlap, consider it a match
                    if len(reg_words) > 0 and len(ocr_words) > 0:
                        overlap = len(reg_words.intersection(ocr_words))
                        total_words = len(reg_words.union(ocr_words))
                        similarity = overlap / total_words if total_words > 0 else 0
                        
                        # If similarity is high enough, consider it a match
                        if similarity >= 0.7:  # 70% similarity threshold
                            print(f'DEBUG: Names are similar enough (similarity: {similarity:.2f}), treating as match')
                            continue
                    
                    mismatches[key] = {
                        'user': reg_val,
                        'ocr': ocr_val
                    }
            else:
                    # For non-name fields (like DOB), use exact comparison
                if normalize(reg_val) != normalize(ocr_val):
                    mismatches[key] = {
                        'user': reg_val,
                        'ocr': ocr_val
                    }
        
        print('DEBUG: mismatches:', mismatches)
        if mismatches:
            return Response({'status': 'mismatch', 'mismatches': mismatches})
        return Response({'status': 'match'})


def correct_month_name(date_str):
    import difflib
    months = [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
    ]
    # Find a word that looks like a month
    words = date_str.upper().split()
    for i, word in enumerate(words):
        # Only check words with at least 3 letters
        if len(word) >= 3:
            matches = difflib.get_close_matches(word, months, n=1, cutoff=0.6)
            if matches:
                words[i] = matches[0]
                return " ".join(words)
    return date_str

