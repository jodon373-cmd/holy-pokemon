"""Read-only discovery state provider for Holy Pokemon's unified dashboard.

The discovery collector owns its SQLite file. This provider returns only research
leads and an explicit integration status; it never opens marketplace connections.
In the newer local dashboard, add ``discovery_snapshot()`` to app state. The
collector's ``--sync-app`` option also imports leads into the shared Store.
"""
from __future__ import annotations

import json
from pathlib import Path
import sqlite3


def discovery_snapshot(database="outputs/holy_auto_discovery.sqlite", *, limit=100):
    """Return a bounded, offline dashboard-friendly research queue."""
    path = Path(database).resolve()
    if not path.is_file():
        return {"status": "NOT_STARTED", "count": 0, "leads": [], "last_seen": None,
                "source": "local_research_discovery", "live_verified": False}
    if not 1 <= limit <= 1000:
        raise ValueError("Dashboard lead limit must be between 1 and 1000")
    try:
        with sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True, timeout=3) as db:
            count = db.execute("SELECT COUNT(*) FROM holy_auto_leads").fetchone()[0]
            rows = db.execute(
                "SELECT snapshot_json FROM holy_auto_leads "
                "ORDER BY research_score DESC,last_seen DESC LIMIT ?", (limit,)
            ).fetchall()
            most_recent = db.execute("SELECT MAX(last_seen) FROM holy_auto_leads").fetchone()[0]
        leads = [json.loads(row[0]) for row in rows]
    except (sqlite3.Error, ValueError, TypeError, json.JSONDecodeError):
        return {"status": "UNAVAILABLE", "count": 0, "leads": [], "last_seen": None,
                "source": "local_research_discovery", "live_verified": False}
    return {"status": "READY", "count": count, "leads": leads, "last_seen": most_recent,
            "source": "local_research_discovery", "live_verified": False,
            "warning": "Active listing discovery is not evidence of sold comps or purchase approval."}