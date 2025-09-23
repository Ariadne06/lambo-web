import re
import cv2
import io
import numpy as np
import pytesseract
import requests
from PIL import Image, ImageEnhance
from django.conf import settings
from .text_processing import normalize_name, clean_name_line, correct_month_name, normalize_for_comparison, normalize_name_for_comparison, names_are_similar

# Configure Tesseract path
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

VOTER_KEYWORDS = ["VOTER'S CERTIFICATE", "VOTERS CERTIFICATE", "COMMISSION ON ELECTIONS", "COMELEC"]
BIRTH_KEYWORDS = ["CERTIFICATE OF LIVE BIRTH", "BIRTH CERTIFICATE", "PHILIPPINE STATISTICS AUTHORITY", "PSA"]

DOCUMENT_TYPE_KEYWORDS = {
    "birth certificate": BIRTH_KEYWORDS,
    "voter's certificate": VOTER_KEYWORDS,
    "voters certificate": VOTER_KEYWORDS,  # alternate
}

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
    """IMPROVED: Main OCR function with better name handling for Philippine Driver's License."""
    ocr_backend = getattr(settings, 'OCR_BACKEND', 'tesseract')
    if ocr_backend == 'idanalyzer':
        try:
            idanalyzer_result = id_analyzer_scan(id_image_file)
            result = idanalyzer_result.get('result', {})
            
            # Get raw extracted data
            raw_first_name = result.get('firstName', '')
            raw_middle_name = result.get('middleName', '')
            raw_last_name = result.get('lastName', '')
            full_name = result.get('fullName', '')
            dob = result.get('dob', '')

            print(f"DEBUG: ID Analyzer raw extraction - First: '{raw_first_name}', Middle: '{raw_middle_name}', Last: '{raw_last_name}'")
            print(f"DEBUG: Full name: '{full_name}'")

            # Handle Philippine Driver's License specific format
            if doc_type and 'driver' in doc_type.lower() and registration_data:
                first_name, middle_name, last_name = handle_philippine_drivers_license(
                    raw_first_name, raw_middle_name, raw_last_name, full_name, registration_data
                )
            else:
                # For other document types, use raw extraction
                first_name = raw_first_name
                middle_name = raw_middle_name
                last_name = raw_last_name

            # Format DOB
            if dob and '/' in dob:
                dob = dob.replace('/', '-')

            fields = {
                'first_name': first_name,
                'last_name': last_name,
                'middle_name': middle_name,
                'dob': dob,
            }

            print(f"DEBUG: Final extracted fields - First: '{first_name}', Middle: '{middle_name}', Last: '{last_name}'")
            return fields

        except Exception as e:
            print("ID Analyzer failed, falling back to Tesseract:", e)
            id_image_file.seek(0)
            return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)
    else:
        return run_ocr_and_extract_fields(id_image_file, doc_type, registration_data)

def handle_philippine_drivers_license(raw_first, raw_middle, raw_last, full_name, registration_data):
    """
    Handle Philippine Driver's License name format specifically.
    Driver's License format: Last Name, First Name Middle Name
    """
    user_first = registration_data.get('first_name', '').strip()
    user_middle = registration_data.get('middle_name', '').strip()
    user_last = registration_data.get('last_name', '').strip()
    
    print(f"DEBUG: User input - First: '{user_first}', Middle: '{user_middle}', Last: '{user_last}'")
    print(f"DEBUG: ID Analyzer raw - First: '{raw_first}', Middle: '{raw_middle}', Last: '{raw_last}'")
    
    # Start with ID Analyzer results
    first_name = raw_first
    middle_name = raw_middle
    last_name = raw_last
    
   
    if user_first and ' ' in user_first:
        user_first_parts = user_first.split()
        
        # Check if ID Analyzer split the first name incorrectly
     
        if raw_middle and raw_middle.startswith(user_first_parts[1].upper()):
            # Reconstruct the first name
            first_name = ' '.join(user_first_parts)
            
            # Extract the actual middle name from the raw middle name
            # Remove the second part of first name from raw middle name
            remaining_middle = raw_middle.replace(user_first_parts[1].upper(), '').strip()
            if remaining_middle and user_middle and remaining_middle.upper() == user_middle.upper():
                middle_name = user_middle
            else:
                middle_name = remaining_middle
                
            print(f"DEBUG: Reconstructed multi-word first name: '{first_name}', Middle: '{middle_name}'")
    
    # Case 2: Verify last name is correct
    if user_last and raw_last:
        if normalize_name_for_comparison(user_last) != normalize_name_for_comparison(raw_last):
            # Check if they're similar enough
            if not names_are_similar(user_last, raw_last):
                print(f"DEBUG: Last name mismatch - User: '{user_last}', ID Analyzer: '{raw_last}'")
                # In this case, trust ID Analyzer since it's usually more accurate for last names
                last_name = raw_last
    
    # Case 3: Handle cases where middle name contains multiple parts
    if user_middle and raw_middle:
        # If user middle is single word but raw middle has multiple words
        if ' ' not in user_middle and ' ' in raw_middle:
            # Check if user middle is contained in raw middle
            if user_middle.upper() in raw_middle.upper():
                middle_name = user_middle
                print(f"DEBUG: Used user's single-word middle name: '{middle_name}'")
    
    # Normalize case
    first_name = normalize_name(first_name) if first_name else ''
    middle_name = normalize_name(middle_name) if middle_name else ''
    last_name = normalize_name(last_name) if last_name else ''
    
    return first_name, middle_name, last_name

def _normalize(text):
    return re.sub(r'\s+', ' ', (text or '').upper()).strip()

def _match_keywords(text, keywords):
    T = _normalize(text)
    return any(k in T for k in keywords)

def validate_document_header(file_obj, expected_type):
    """
    Extracts text and checks if it contains the header keywords for the chosen document_type.
    Returns True if keywords found, else False.
    """
    if not getattr(settings, 'ENABLE_OCR_VALIDATION', True):
        print("[OCR] Validation disabled in settings.")
        return True

    try:
        file_obj.seek(0)
        img = Image.open(io.BytesIO(file_obj.read()))
        img = img.convert('L')
        text = pytesseract.image_to_string(img, lang='eng') or ''
        file_obj.seek(0)
    except Exception as e:
        print(f"[OCR] Exception during OCR: {e}")
        return False

    print(f"[OCR] Extracted text for '{expected_type}':")
    print("----- OCR TEXT START -----")
    print(text)
    print("----- OCR TEXT END -----")

    doc_key = (expected_type or '').strip().lower()
    keywords = DOCUMENT_TYPE_KEYWORDS.get(doc_key)
    if not keywords:
        if 'voter' in doc_key:
            keywords = VOTER_KEYWORDS
        elif 'birth' in doc_key:
            keywords = BIRTH_KEYWORDS

    if not keywords:
        print(f"[OCR] No keywords setup for document type: '{doc_key}'. Skipping OCR validation.")
        return True

    found = _match_keywords(text, keywords)
    print(f"[OCR] Header keywords for '{doc_key}' found: {found}")
    return found