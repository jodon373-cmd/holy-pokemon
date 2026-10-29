"""High-priority Pokémon Promo research discovery, without treating guides as sold comps."""
from __future__ import annotations
import json
from pathlib import Path
from typing import Any

CONFIG = Path(__file__).resolve().parents[1] / "research" / "pokemon_promo_priority.json"

def preset():
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    if data["id"] != "pokemon-promo" or data["priority_weight"] != 100:
        raise ValueError("Unexpected promo priority configuration")
    return data

def queries(limit=None):
    data = preset()
    requested = data["default_query_limit"] if limit is None else limit
    if not isinstance(requested, int) or not 1 <= requested <= len(data["queries"]):
        raise ValueError("Query limit out of range")
    return data["queries"][:requested]

def matches_promo(title: str) -> bool:
    """Conservative promo tag; exact set/variant still requires independent review."""
    s = " ".join(title.lower().split())
    return "pokemon" in s and (
        "black star" in s or "blackstar" in s or "promo" in s
    )

def tag_listing(row: dict[str, Any], query_id: str) -> dict[str, Any]:
    """Enrich a read-only listing; never alter provider evidence or claim a verified comp."""
    result = dict(row)
    matched = matches_promo(str(row.get("title", "")))
    result["promo_source_candidate"] = matched
    result["priority_research_tier"] = "CRITICAL_RESEARCH" if matched else "NORMAL"
    result["research_preset"] = query_id
    result["promo_variant_verified"] = False
    result["promo_trade_approved"] = False
    return result

def discover(client, limit=None):
    """Use existing authorized, cached eBay Browse client, without provider bypass."""
    results = {}
    for search in queries(limit):
        for row in client.search(search["q"]):
            tagged = tag_listing(row, search["id"])
            if not tagged["promo_source_candidate"]:
                continue
            key = str(tagged.get("listing_id", ""))
            if not key:
                continue
            if key not in results:
                results[key] = tagged
            else:
                result = results[key]
                result.setdefault("matched_promo_queries", []).append(search["id"])
    return list(results.values())
