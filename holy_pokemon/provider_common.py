"""Minimal shared provider input sanitizers; do not import legacy DB/schema."""
from datetime import datetime,timezone
from urllib.parse import urlparse

def timestamp(value):
    dt=datetime.fromisoformat(str(value).replace("Z","+00:00"))
    if dt.tzinfo is None:raise ValueError("Timestamp needs timezone")
    return dt.astimezone(timezone.utc)

def public_url(value):
    value=str(value or "").strip()
    parsed=urlparse(value)
    if parsed.scheme!="https" or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError("HTTPS public source URL required")
    if any(k in parsed.query.lower() for k in ("key=","token=","secret=","authorization=")):
        raise ValueError("Credential-bearing URL rejected")
    return value
