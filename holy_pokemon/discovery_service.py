"""Bounded read-only discovery feed; never requests marketplace data."""

from __future__ import annotations
from collections import Counter
from contextlib import closing
import json
from pathlib import Path
import sqlite3
from .store import ROOT

DEFAULT_DATABASE = ROOT / "outputs/holy_auto_discovery.sqlite"


def discovery_snapshot(database=None, *, limit=100):
    if not 1 <= limit <= 1000:
        raise ValueError("Dashboard lead limit must be between 1 and 1000")
    path = Path(database or DEFAULT_DATABASE).resolve()
    base = {
        "count": 0,
        "leads": [],
        "last_seen": None,
        "source": "local_research_discovery",
        "live_verified": False,
        "source_counts": {},
        "queries": [],
        "warning": "Active asking prices and research interest are not sold comps or purchase approval.",
    }
    if not path.is_file():
        return {**base, "status": "NOT_STARTED"}
    try:
        with closing(
            sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=3)
        ) as db:
            count = db.execute("SELECT count(*) FROM holy_auto_leads").fetchone()[0]
            rows = db.execute(
                "SELECT snapshot_json FROM holy_auto_leads ORDER BY research_score DESC,last_seen DESC LIMIT ?",
                (limit,),
            ).fetchall()
            recent = db.execute(
                "SELECT max(last_seen) FROM holy_auto_leads"
            ).fetchone()[0]
            queries = [
                dict(zip(("query_id", "last_success", "last_error", "searches"), r))
                for r in db.execute(
                    "SELECT query_id,last_success,last_error,searches FROM holy_auto_queries ORDER BY query_id"
                )
            ]
        leads = [json.loads(r[0]) for r in rows]
        if any(not isinstance(r, dict) for r in leads):
            raise ValueError("Invalid discovery snapshot")
    except (sqlite3.Error, ValueError, TypeError):
        return {**base, "status": "UNAVAILABLE"}

    def source(row):
        if row.get("dataset") == "SYNTHETIC" or str(
            row.get("title", "")
        ).upper().startswith("SYNTHETIC"):
            return "synthetic"
        if row.get("source") == "ebay_browse":
            return "official_browse_observation"
        return "operator_import"

    sources = dict(Counter(source(r) for r in leads))
    return {
        **base,
        "status": "READY",
        "count": count,
        "leads": leads,
        "last_seen": recent,
        "queries": queries,
        "source_counts": sources,
        "source_counts_scope": "displayed_feed",
        "live_status": "API_OBSERVATIONS_PRESENT"
        if sources.get("official_browse_observation")
        else "NO_LIVE_API_OBSERVATIONS",
    }
