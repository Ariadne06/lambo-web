import re
import json
from collections.abc import Mapping
from typing import Optional

CODE_MESSAGES = {}

import re
from typing import Optional

CODE_MESSAGES = {}

def _clean_db_error(err: Exception) -> str:
    """
    Extract the most specific DB error:
    - Prefer the original DB error if wrapped (err.orig).
    - Strip noisy sections (CONTEXT/DETAIL/HINT/LINE).
    - Pick the *last* E-code (root cause) and return text after its colon.
    - Fall back to a generic message if nothing matches.
    """
    # 1) unwrap common DB wrappers (psycopg/Django)
    text = str(getattr(err, "orig", err))

    # 2) drop noisy trailing sections
    text = re.split(r"\n(?:CONTEXT|DETAIL|HINT|LINE)\s*:", text, 1)[0].strip()

    # 3) find the *last* E-code occurrence
    last: Optional[re.Match] = None
    for m in re.finditer(r"(E\d{4,5}[A-Z]?)\s*:", text):
        last = m

    if last:
        code = last.group(1)
        # Everything *after* the last code’s colon is the message we want
        msg = text[last.end():].strip()
        # If you maintain friendly overrides, prefer them
        return CODE_MESSAGES.get(code, msg or "An error occurred.")

    # 4) no E-code; try common 'ERROR:' prefix or return first line
    m = re.search(r"ERROR\s*:\s*(.+)$", text, re.IGNORECASE)
    if m:
        return m.group(1).strip()

    # If text has multiple parts split by ':' take the last meaningful segment
    if ':' in text:
        tail = text.split(':')[-1].strip()
        if tail:
            return tail

    # Final fallback: return trimmed original text (avoid leaking stack traces)
    return text or "We couldn't complete your request. Please try again."


def _clean_params(d: dict) -> dict:
    return {k: v for k, v in d.items() if v not in (None, "")}

def coerce_message(result, default="Action completed."):
    """
    Robustly extract a 'message' from various result shapes:
    - dict / Mapping with 'message'
    - JSON string like '{"message":"..."}'
    - list/tuple -> take first element and recurse
    - object with .get('message') or .message attribute
    - plain string
    """
    try:
        if isinstance(result, Mapping):
            return str(result.get("message") or default)

        if isinstance(result, (list, tuple)) and result:
            return coerce_message(result[0], default=default)

        if isinstance(result, str):
            s = result.strip()
            if s.startswith("{") and s.endswith("}"):
                try:
                    obj = json.loads(s)
                    if isinstance(obj, Mapping) and "message" in obj:
                        return str(obj["message"]) or default
                except Exception:
                    pass
            return s or default

        if hasattr(result, "message"):
            val = getattr(result, "message")
            return str(val) if val else default

        if hasattr(result, "get"):
            try:
                val = result.get("message")
                if val:
                    return str(val)
            except Exception:
                pass
    except Exception:
        pass

    return default