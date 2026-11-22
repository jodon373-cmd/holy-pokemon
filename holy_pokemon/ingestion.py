"""SQLite connection and schema setup for eBay discovery and local evidence."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
from urllib.parse import urlparse


def timestamp(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ValueError("Retrieval timestamp needs a timezone")
    return dt.astimezone(timezone.utc)


def public_url(value: str) -> str:
    value = str(value or "").strip()
    p = urlparse(value)
    if p.scheme != "https" or not p.netloc or p.username or p.password:
        raise ValueError("Public HTTPS provenance URL required")
    if any(token in p.query.lower() for token in ("key=", "token=", "secret=", "authorization=")):
        raise ValueError("Credential-bearing provenance URL rejected")
    return value


def connect(path: str | Path) -> sqlite3.Connection:
    """Open or initialize the local discovery SQLite database."""
    db_path = str(path)
    if db_path != ":memory:":
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(db_path)
    db.execute(
        "CREATE TABLE IF NOT EXISTS ebay_api_usage "
        "(requested_at TEXT, status INTEGER, cooldown_until TEXT)"
    )
    db.execute(
        "CREATE TABLE IF NOT EXISTS ebay_discovery_cache "
        "(cache_key TEXT PRIMARY KEY, retrieved_at TEXT, payload TEXT)"
    )
    return db
