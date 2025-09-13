import re
import difflib

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

def are_names_equivalent(name1, name2):
    """Check if two names are equivalent, handling multi-word names properly."""
    if not name1 or not name2:
        return False
        
    # Normalize both names
    norm1 = normalize_name_for_comparison(name1)
    norm2 = normalize_name_for_comparison(name2)
    
    # Exact match
    if norm1 == norm2:
        return True
    
    # Check if all words in one name are contained in the other
    words1 = set(norm1.split())
    words2 = set(norm2.split())
    
    # If one is subset of the other, consider them equivalent
    if words1.issubset(words2) or words2.issubset(words1):
        return True
    
    # Check for significant overlap (at least 70%)
    if len(words1) > 0 and len(words2) > 0:
        overlap = len(words1 & words2) / max(len(words1 | words2), 1)
        return overlap >= 0.7
    
    return False

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

def correct_month_name(date_str):
    """Correct OCR month name errors using fuzzy matching."""
    months = [
        "JANUARY", "FEBRUARY", "MARCH", "APRIL", "MAY", "JUNE",
        "JULY", "AUGUST", "SEPTEMBER", "OCTOBER", "NOVEMBER", "DECEMBER"
    ]
    words = date_str.upper().split()
    for i, word in enumerate(words):
        closest_match = difflib.get_close_matches(word, months, n=1, cutoff=0.6)
        if closest_match:
            words[i] = closest_match[0]
    return ' '.join(words)