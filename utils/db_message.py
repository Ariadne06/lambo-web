import re

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

    return "Password change failed. Please check your entries and try again."