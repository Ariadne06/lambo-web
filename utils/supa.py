# utils/supa.py
from supabase import create_client
from django.conf import settings


def _client():
    """Server-side Supabase client using SERVICE KEY (secure)."""
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)


def public_url(bucket: str, file_path: str) -> str:
    """Return a permanent public URL (works only if bucket is Public)."""
    base = settings.SUPABASE_URL.rstrip("/")
    return f"{base}/storage/v1/object/public/{bucket}/{file_path.lstrip('/')}"


def signed_url(bucket: str, file_path: str, expires_seconds: int = 300):
    """Generate a short-lived signed URL for Private buckets."""
    sb = _client()
    res = sb.storage.from_(bucket).create_signed_url(file_path, expires_seconds)
    url = res.get("signedURL") or res.get("signed_url")
    if url and url.startswith("/"):  # sometimes supabase-py gives path only
        url = settings.SUPABASE_URL.rstrip("/") + url
    return url


def url_for_doc(file_path: str):
    """
    Smart helper: 
    - If SUPABASE_BUCKET_DOCS_PUBLIC=true → return permanent public URL
    - If false → return signed URL
    """
    bucket = settings.SUPABASE_BUCKET_DOCS
    if settings.SUPABASE_BUCKET_DOCS_PUBLIC:
        return public_url(bucket, file_path)
    return signed_url(bucket, file_path, settings.SUPABASE_SIGNED_SECONDS)
