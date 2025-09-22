# authentication/tokens.py
import json
from django.conf import settings
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired

_SIGNER = TimestampSigner(salt="lambo.password-reset.v1")

def make_reset_token(payload: dict) -> str:
    """
    payload will be JSON-serialized (e.g., {"u": username, "e": email})
    """
    data = json.dumps(payload, separators=(",", ":"))
    return _SIGNER.sign(data)

def load_reset_token(token: str, max_age_seconds: int = 1800) -> dict | None:
    """
    Returns the original dict if valid & not expired; otherwise None.
    """
    try:
        raw = _SIGNER.unsign(token, max_age=max_age_seconds)
        return json.loads(raw)
    except (BadSignature, SignatureExpired, json.JSONDecodeError):
        return None
