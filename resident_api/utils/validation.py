from .text_processing import are_names_equivalent, normalize_for_comparison

def validate_field_match(field_name, user_value, ocr_value):
    """Validate if user input matches OCR result for a specific field."""
    if field_name in ['first_name', 'last_name', 'middle_name']:
        return are_names_equivalent(user_value, ocr_value)
    else:
        # For non-name fields (like DOB), use exact comparison
        return normalize_for_comparison(user_value) == normalize_for_comparison(ocr_value)

def find_mismatches(user_data, ocr_data, fields_to_check):
    """Find mismatches between user data and OCR data."""
    mismatches = {}
    
    for field in fields_to_check:
        user_val = user_data.get(field, '')
        ocr_val = ocr_data.get(field, '')
        
        if user_val and ocr_val:
            if not validate_field_match(field, user_val, ocr_val):
                mismatches[field] = {
                    'user': user_val,
                    'ocr': ocr_val
                }
    
    return mismatches