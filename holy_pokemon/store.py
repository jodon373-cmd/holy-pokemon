"""Private local evidence store. Observations are immutable; reviews are append-only."""

from __future__ import annotations
import hashlib
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "outputs" / "holy.sqlite3"
KINDS = {
    "lead",
    "sale",
    "holding",
    "vault_event",
    "payout",
    "review",
    "watch",
    "search",
    "annotation",
    "model",
    "quote",
    "source_record",
    "aggregate",
    "specimen",
    "grading_event",
    "identity",
    "transcript",
    "decision",
    "video_frame",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def stable(*parts):
    return hashlib.sha256(
        json.dumps(parts, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()


class Store:
    def __init__(self, path=DEFAULT_DB):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.path, timeout=20)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA foreign_keys=ON")
        self.db.executescript("""
        CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
        INSERT OR IGNORE INTO schema_version VALUES(1);
        CREATE TABLE IF NOT EXISTS record(kind TEXT NOT NULL,id TEXT NOT NULL,payload TEXT NOT NULL,created_at TEXT NOT NULL,PRIMARY KEY(kind,id));
        CREATE TABLE IF NOT EXISTS asset(id TEXT PRIMARY KEY,path TEXT UNIQUE NOT NULL,size INTEGER NOT NULL,mtime_ns INTEGER NOT NULL,sha256 TEXT NOT NULL,kind TEXT NOT NULL,metadata TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS asset_hash ON asset(sha256);
        CREATE TABLE IF NOT EXISTS audit_event(id INTEGER PRIMARY KEY,at TEXT NOT NULL,action TEXT NOT NULL,subject TEXT NOT NULL,payload TEXT NOT NULL);
        """)
        self.db.commit()
        os.chmod(self.path, 0o600)

    def close(self):
        self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def rows(self, kind):
        return [
            dict(json.loads(r["payload"]), id=r["id"])
            for r in self.db.execute(
                "SELECT id,payload FROM record WHERE kind=? ORDER BY created_at,id",
                (kind,),
            )
        ]

    def get(self, kind, id):
        r = self.db.execute(
            "SELECT payload FROM record WHERE kind=? AND id=?", (kind, id)
        ).fetchone()
        return dict(json.loads(r[0]), id=id) if r else None

    def put(self, kind, id, payload):
        if kind not in KINDS or not id:
            raise ValueError("Unknown record kind or missing ID")
        data = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        prior = self.db.execute(
            "SELECT payload FROM record WHERE kind=? AND id=?", (kind, id)
        ).fetchone()
        if prior:
            if prior[0] != data:
                raise ValueError(
                    "Immutable ID conflict; append a new evidence/review record"
                )
            return False
        with self.db:
            inserted = self.db.execute(
                "INSERT OR IGNORE INTO record VALUES(?,?,?,?)", (kind, id, data, now())
            ).rowcount
            if not inserted:
                existing = self.db.execute(
                    "SELECT payload FROM record WHERE kind=? AND id=?", (kind, id)
                ).fetchone()[0]
                if existing != data:
                    raise ValueError("Immutable ID conflict; append a new review")
                return False
            self.db.execute(
                "INSERT INTO audit_event(at,action,subject,payload) VALUES(?,?,?,?)",
                (now(), "import", kind + ":" + id, data),
            )
        return True

    def counts(self):
        return {
            r[0]: r[1]
            for r in self.db.execute("SELECT kind,count(*) FROM record GROUP BY kind")
        }

    def assets(self):
        return [
            dict(r, metadata=json.loads(r["metadata"]))
            for r in self.db.execute("SELECT * FROM asset ORDER BY path")
        ]

    def index(self, path, kind, metadata=None):
        p = Path(path).resolve()
        stat = p.stat()
        prior = self.db.execute(
            "SELECT * FROM asset WHERE path=?", (str(p),)
        ).fetchone()
        if (
            prior
            and prior["size"] == stat.st_size
            and prior["mtime_ns"] == stat.st_mtime_ns
        ):
            return prior["sha256"]
        digest = hashlib.sha256()
        with p.open("rb") as f:
            for block in iter(lambda: f.read(1024 * 1024), b""):
                digest.update(block)
        sha = digest.hexdigest()
        with self.db:
            self.db.execute(
                "INSERT OR REPLACE INTO asset VALUES(?,?,?,?,?,?,?)",
                (
                    stable(str(p)),
                    str(p),
                    stat.st_size,
                    stat.st_mtime_ns,
                    sha,
                    kind,
                    json.dumps(metadata or {}),
                ),
            )
        return sha
