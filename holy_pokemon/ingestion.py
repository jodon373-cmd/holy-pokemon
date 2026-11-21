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
class SeenListingStore:
    """Persistent aliases for cross-query and cross-run dedupe; no transactions or messaging."""
    def __init__(self, path):
        import sqlite3
        from pathlib import Path
        if str(path) != ':memory:':
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path))
        self.db.execute('CREATE TABLE IF NOT EXISTS seen_listing_alias(alias TEXT PRIMARY KEY, first_seen TEXT NOT NULL)')

    @staticmethod
    def aliases(row):
        import re
        from .title_parser import parse_title
        result=[]
        listing=str(row.get('listing_id') or row.get('id') or '')
        if listing:
            result.append('listing:'+listing)
        ebay=str(row.get('ebay_item_id') or '')
        if not ebay:
            m=re.search(r'(?:v1\||/itm/(?:[^/]+/)?)?(\d{9,15})(?:\||[/?#]|$)', listing+' '+str(row.get('url') or ''))
            ebay=m.group(1) if m else ''
        if ebay:
            result.append('ebay:'+ebay)
        cert=str(row.get('certification_number') or row.get('cert') or '')
        grader=row.get('grader') or parse_title(row.get('title','')).grader
        if cert and grader:
            result.append('cert:'+str(grader).upper()+':'+cert)
        return result

    def observe(self, row):
        from datetime import datetime, timezone
        aliases=sorted(set([*self.aliases(row),*row.get('seen_aliases',[])]))
        if not aliases:
            return True
        with self.db:
            self.db.execute('BEGIN IMMEDIATE')
            old=any(self.db.execute('SELECT 1 FROM seen_listing_alias WHERE alias=?',(a,)).fetchone() for a in aliases)
            self.db.executemany('INSERT OR IGNORE INTO seen_listing_alias VALUES(?,?)',
                                [(a,datetime.now(timezone.utc).isoformat()) for a in aliases])
        return not old

    def close(self):
        self.db.close()
