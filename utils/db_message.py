import re
import json
from collections.abc import Mapping

CODE_MESSAGES = {}

def _clean_db_error(err: Exception) -> str:
    text = str(err)

    if "CONTEXT:" in text:
        text = text.split("CONTEXT:")[0].strip()

    m = re.search(r"(E\d{4,5})\s*:\s*(.*)", text)
    if m:
        code, raw_msg = m.group(1), m.group(2).strip()
        friendly = CODE_MESSAGES.get(code, raw_msg or "An error occurred.")
        return f"{friendly}"

    return "We couldn't complete your request. Please try again."

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