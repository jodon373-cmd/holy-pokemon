"""Holy Pokemon read-only, quota-aware, unattended research discovery.

Uses only the authorized eBay Browse API and operator-supplied evidence files.
No scraping, bidding, checkout, sold-price fabrication, or unlicensed data reuse.
Compatible with the repository's EbayBrowse HTTP/quota adapter.

Commands:
  python -m holy_pokemon.automated_discovery --import-csv leads.csv --once
  python -m holy_pokemon.automated_discovery --live --authorized-keyset --once
  python -m holy_pokemon.automated_discovery --live --authorized-keyset --watch
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import sys
import time
from urllib.parse import urlencode, urlparse

from .ebay_browse import EbayBrowse, EbayError, credentials, discovery_row

DEFAULT_QUERIES = (
    ("legacy-cgc", "CGC 9.5 Pokemon", "newlyListed", "FIXED_PRICE"),
    ("psa-vintage", "PSA 9 Pokemon vintage", "newlyListed", "FIXED_PRICE"),
    ("bgs-upside", "BGS 9.5 Pokemon", "newlyListed", "FIXED_PRICE"),
    ("cgc-older", "CGC blue label Pokemon", "newlyListed", "FIXED_PRICE"),
    ("eseries", "Skyridge Pokemon PSA", "newlyListed", "FIXED_PRICE"),
    ("expedition", "Expedition Pokemon CGC", "newlyListed", "FIXED_PRICE"),
    ("gold-star", "Pokemon gold star PSA 8", "newlyListed", "FIXED_PRICE"),
    ("aquapolis", "Aquapolis Pokemon PSA", "newlyListed", "FIXED_PRICE"),
    ("japanese-vintage", "Japanese Pokemon 1997 PSA", "newlyListed", "FIXED_PRICE"),
    ("auction-expiring", "Pokemon BGS 9.5", "endingSoonest", "AUCTION"),
    ("auction-cgc", "Pokemon CGC 9.5", "endingSoonest", "AUCTION"),
)
KNOWN_GRADERS = re.compile(r"\b(PSA|CGC|BGS|BECKETT|SGC)\s*(?:GEM\s*MINT|MINT\s*\+|PRISTINE)?\s*(10|9[.,]5|9|8[.,]5|8|7)\b", re.I)
VINTAGE = re.compile(r"\b(1st edition|first edition|shadowless|base set|jungle|fossil|neo|rocket|skyridge|aquapolis|expedition|gold star|e[- ]series|ex dragon|ex team|gym challenge|gym heroes|199[6-9]|200[0-7])\b", re.I)
ACCESSORIES = re.compile(r"\b(code card|code cards|proxy|replica|custom art|digital item|empty slab|card stand|case only|slab protector|booster box|booster pack|sealed pack|binder|stickers|lot of [0-9]{2,})\b", re.I)
CERT = re.compile(r"\b(?:PSA\s*(?:CERT|#)?\s*)(\d{7,12})\b", re.I)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def valid_ebay_link(raw: str) -> str:
    """Do not accept redirects, credentials, or lookalike domains from imports."""
    u = urlparse(str(raw))
    if u.scheme != "https" or u.hostname not in ("ebay.com", "www.ebay.com") or u.username or u.password or not u.path.startswith("/itm/"):
        raise ValueError("A direct HTTPS eBay /itm/ listing URL is required")
    return u._replace(fragment="").geturl()


def dollars(raw):
    if raw in (None, ""):
        return None
    try:
        number = Decimal(str(raw).replace("$", "").replace(",", ""))
    except (InvalidOperation, ValueError):
        return None
    return str(number) if number.is_finite() and number >= 0 else None


def rank_for_research(row: dict) -> dict:
    """Ranks inspection interest, NOT expected profits or grading probabilities."""
    title = str(row.get("title") or "")
    text = title.casefold()
    grade = KNOWN_GRADERS.search(title)
    reasons = []
    score = 0
    if grade:
        grader = grade.group(1).upper()
        grade_label = grade.group(2).replace(",", ".")
        score += 22
        reasons.append("grading_holder_mentioned_in_title_unverified")
        if grader == "CGC" and grade_label in ("9.5", "9"):
            score += 18
            reasons.append("cgc_holder_for_manual_regrade_review")
        elif grader in ("BGS", "BECKETT") and grade_label == "9.5":
            score += 16
            reasons.append("bgs_9_5_holder_for_manual_review")
        elif grader == "PSA" and grade_label in ("8", "9"):
            score += 14
            reasons.append("psa_8_9_holder_for_manual_review")
    else:
        grader, grade_label = None, None
        score += 10
        reasons.append("grade_not_evident_needs_visual_identification")
    if VINTAGE.search(title):
        score += 30
        reasons.append("vintage_or_high_interest_variant_keyword")
    if "1st edition" in text or "shadowless" in text or "gold star" in text:
        score += 10
        reasons.append("high_stakes_variant_requires_exact_verification")
    if row.get("image_urls"):
        score += 5
    else:
        reasons.append("missing_card_photographs")
    if ACCESSORIES.search(title):
        score -= 80
        reasons.append("likely_accessory_bundle_or_non_card")
    if row.get("currency") is None:
        reasons.append("unknown_listing_currency")
    elif row.get("currency") != "USD":
        score -= 10
        reasons.append("non_usd_currency_requires_conversion")
    price = dollars(row.get("ask", row.get("asking_price")))
    if price is None:
        reasons.append("unknown_asking_price")
    return {
        "research_score": max(0, min(100, score)),
        "research_reasons": reasons,
        "title_grader_hint": grader,
        "title_grade_hint": grade_label,
        "economic_profit": None,
        "probability_upgrade": None,
        "approval": "NEED_MORE_EVIDENCE",
        "missing": ["exact_variant", "seller_review", "front_back_condition_review", "verified_sold_comps", "all_in_costs", "downside_branches"],
    }


def initialize(db: sqlite3.Connection) -> None:
    db.execute("""CREATE TABLE IF NOT EXISTS holy_auto_leads (
        listing_id TEXT PRIMARY KEY, first_seen TEXT NOT NULL,
        last_seen TEXT NOT NULL, snapshot_json TEXT NOT NULL,
        research_score INTEGER NOT NULL, last_query TEXT NOT NULL,
        changed_count INTEGER NOT NULL DEFAULT 0
    )""")
    db.execute("""CREATE TABLE IF NOT EXISTS holy_auto_queries (
        query_id TEXT PRIMARY KEY, last_success TEXT, last_error TEXT,
        searches INTEGER NOT NULL DEFAULT 0
    )""")
    db.commit()


def normalize(row: dict, retrieved: str, query_id: str) -> dict:
    url = valid_ebay_link(row.get("url") or row.get("source_url") or "")
    item_id = str(row.get("listing_id") or row.get("item_id") or "").strip()
    if not item_id:
        # Stable fallback for manual entries with no item ID, NEVER guess eBay item IDs.
        item_id = "manual-" + hashlib.sha256(url.encode()).hexdigest()[:20]
    image_urls = row.get("image_urls") or []
    if isinstance(image_urls, str):
        try:
            loaded = json.loads(image_urls)
            image_urls = loaded if isinstance(loaded, list) else [image_urls] if image_urls else []
        except ValueError:
            image_urls = [image_urls] if image_urls else []
    price = dollars(row.get("ask", row.get("asking_price")))
    shipping = dollars(row.get("shipping"))
    enriched = {
        "listing_id": item_id,
        "title": str(row.get("title") or "")[:500],
        "source_url": url,
        "ask": price,
        "shipping": shipping,
        "currency": row.get("currency") or None,
        "image_urls": image_urls,
        "auction_deadline": row.get("auction_deadline"),
        "bid_count": row.get("bid_count"),
        "buying_options": row.get("buying_options") or [],
        "cert_number_hint": row.get("certification_number"),
        "provider": "ebay",
        "source": row.get("source", "operator_import"),
        "evidence_kind": "active_listing_only",
        "observed_at": row.get("observed_at") or retrieved[:10],
        "retrieved_at": retrieved,
        "search_query_id": query_id,
        "photo_condition_verified": False,
        "exact_identity_verified": False,
        "sold_comp_verified": False,
        "purchase_authorized": False,
    }
    enriched.update(rank_for_research(enriched))
    return enriched


def store_leads(db: sqlite3.Connection, rows: list[dict], *, query_id: str, now: datetime | None = None):
    initialize(db)
    stamp = (now or utcnow()).isoformat()
    alerts = []
    for row in rows:
        try:
            normalized = normalize(row, stamp, query_id)
        except (ValueError, TypeError):
            continue
        item_id = normalized["listing_id"]
        prior = db.execute("SELECT snapshot_json,changed_count FROM holy_auto_leads WHERE listing_id=?", (item_id,)).fetchone()
        old = json.loads(prior[0]) if prior else None
        normalized["first_seen"] = old.get("first_seen") if old else stamp
        # Only meaningful listing changes trigger a watch update; research state never implies approval.
        changed = bool(old) and any(old.get(k) != normalized.get(k) for k in ("ask", "auction_deadline", "bid_count"))
        with db:
            db.execute("""INSERT INTO holy_auto_leads
                (listing_id,first_seen,last_seen,snapshot_json,research_score,last_query,changed_count)
                VALUES(?,?,?,?,?,?,?)
                ON CONFLICT(listing_id) DO UPDATE SET last_seen=excluded.last_seen,
                snapshot_json=excluded.snapshot_json,research_score=excluded.research_score,
                last_query=excluded.last_query,changed_count=excluded.changed_count""",
                (item_id, normalized["first_seen"], stamp, json.dumps(normalized, sort_keys=True),
                 normalized["research_score"], query_id, (prior[1] if prior else 0)+int(changed)))
        if not prior or changed:
            alerts.append({"event": "NEW_LISTING" if not prior else "LISTING_CHANGED", **normalized})
    return alerts


def load_operator_csv(path: Path) -> list[dict]:
    if not path.is_file():
        raise FileNotFoundError(str(path))
    with path.open(newline="", encoding="utf-8-sig") as f:
        records = list(csv.DictReader(f))
    if len(records) > 50000:
        raise ValueError("CSV import exceeds 50,000-row safety limit")
    return records


def direct_search(client: EbayBrowse, q: str, sort: str, purchase_type: str, *, limit: int = 100):
    """One cached official Browse search; no page loops, scraping, or hidden endpoints."""
    if sort not in ("newlyListed", "endingSoonest") or purchase_type not in ("AUCTION", "FIXED_PRICE"):
        raise ValueError("Unsupported search mode")
    if not (1 <= limit <= 200) or not q or len(q) > 100:
        raise ValueError("Invalid Browse request")
    if not client.enabled or not client.approved or not client.cid or not client.secret:
        raise EbayError("Official Browse API unavailable: authorized production keyset required")
    url = "https://api.ebay.com/buy/browse/v1/item_summary/search?" + urlencode({
        "q": q, "category_ids": "183454", "sort": sort,
        "filter": f"buyingOptions:{{{purchase_type}}}", "limit": limit})
    key = hashlib.sha256((str(client.cid)+url).encode()).hexdigest()
    cached = client.db.execute("SELECT retrieved_at,payload FROM ebay_discovery_cache WHERE cache_key=?", (key,)).fetchone()
    now = client.now()
    if cached and 0 <= (now - datetime.fromisoformat(cached[0].replace("Z", "+00:00"))).total_seconds() < 3600:
        return json.loads(cached[1]), True
    response = client._call("GET", url, {
        "Authorization": "Bearer " + client._token(),
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"})
    records = response.get("itemSummaries")
    if not isinstance(records, list):
        raise EbayError("Browse response omitted itemSummaries")
    stamp = client.now().isoformat()
    clean = [discovery_row(r, stamp) for r in records]
    with client.db:
        client.db.execute("INSERT OR REPLACE INTO ebay_discovery_cache VALUES(?,?,?)", (key, stamp, json.dumps(clean)))
    return clean, False


def next_queries(db, count, *, min_gap_hours, now=None, plans=DEFAULT_QUERIES):
    initialize(db)
    now = now or utcnow()
    due = []
    for plan in plans:
        prior = db.execute("SELECT last_success FROM holy_auto_queries WHERE query_id=?", (plan[0],)).fetchone()
        last = datetime.fromisoformat(prior[0]) if prior and prior[0] else None
        if last is None or now - last >= timedelta(hours=min_gap_hours):
            due.append((last or datetime.min.replace(tzinfo=timezone.utc), plan))
    return [p for _, p in sorted(due, key=lambda entry: entry[0])[:count]]


def record_query(db, query_id, *, error=None, when=None):
    now = (when or utcnow()).isoformat()
    with db:
        db.execute("""INSERT INTO holy_auto_queries (query_id,last_success,last_error,searches)
            VALUES(?,?,?,1) ON CONFLICT(query_id) DO UPDATE SET
            last_success=CASE WHEN excluded.last_error IS NULL THEN excluded.last_success ELSE holy_auto_queries.last_success END,
            last_error=excluded.last_error, searches=holy_auto_queries.searches+1""",
            (query_id, now if error is None else None, error))


def csv_cell(value):
    """Prevent spreadsheet formula execution from untrusted listing text."""
    if value is None:
        return ""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def export(db, output: Path, alerts: list[dict]) -> dict:
    output.mkdir(parents=True, exist_ok=True)
    rows = [json.loads(r[0]) for r in db.execute("SELECT snapshot_json FROM holy_auto_leads ORDER BY research_score DESC,last_seen DESC")]
    write_json_atomic(output / "research_leads.json", {
        "kind": "REAL_LISTINGS_RESEARCH_ONLY", "count": len(rows),
        "warning": "Rank means review interest; no profit estimate or purchase approval.", "leads": rows})
    # Compatible with Holy Pokemon's manually imported market lead schema.
    keys = ("listing_id", "title", "source_url", "ask", "shipping", "currency", "observed_at", "retrieved_at",
            "provider", "evidence_kind", "research_score", "approval", "search_query_id", "cert_number_hint")
    with (output / "research_leads.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({k: csv_cell(row.get(k)) for k in keys})
    # Append only on real new/changed events, never resend identical alerts.
    if alerts:
        with (output / "listing_alerts.jsonl").open("a", encoding="utf-8") as f:
            for item in alerts:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    return {"stored_leads": len(rows), "new_or_changed": len(alerts), "csv": str(output / "research_leads.csv"),
            "json": str(output / "research_leads.json")}


def write_json_atomic(path, payload):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    temp.replace(path)


def scan_once(db, client, *, maximum_queries=2, min_gap_hours=6, plans=DEFAULT_QUERIES):
    initialize(db)
    alerts, errors, scanned = [], [], []
    for qid, q, sort, mode in next_queries(db, maximum_queries, min_gap_hours=min_gap_hours, plans=plans):
        # Existing eBay adapter tracks all requests, including OAuth token requests.
        # Pause ahead of the local cap and pick up again next calendar day.
        calls = db.execute("SELECT count(*) FROM ebay_api_usage WHERE substr(requested_at,1,10)=?",
                           (client.now().date().isoformat(),)).fetchone()[0]
        if calls >= client.daily_limit - 2:
            scanned.append({"query_id": qid, "status": "LOCAL_DAILY_QUOTA_PAUSED"})
            break
        try:
            rows, cache_hit = direct_search(client, q, sort, mode)
            alerts.extend(store_leads(db, rows, query_id=qid))
            record_query(db, qid)
            scanned.append({"query_id": qid, "results": len(rows), "cached": cache_hit})
        except EbayError as exc:
            # Do not output credentials, URLs containing tokens, or provider payloads.
            message = str(exc)
            if "429" in message or "cap" in message.lower():
                error = "HTTP_429_OR_LOCAL_LIMIT"
            elif "403" in message:
                error = "HTTP_403_CHECK_PRODUCTION_ACCESS"
            elif "401" in message:
                error = "HTTP_401_CHECK_OAUTH"
            else:
                error = "PROVIDER_REQUEST_FAILED"
            record_query(db, qid, error=error)
            errors.append({"query_id": qid, "error": error})
            break  # Stop rather than hammer denied or rate-limited requests.
    return {"queries": scanned, "errors": errors}, alerts


def sync_into_holy_pokemon(rows: list[dict]) -> dict:
    """Best-effort bridge to Codex's newer local market/Store implementation.

    Never labels imported active asks as completed sales. Does not purchase anything.
    If the Mac has not installed the newer local modules, CSV export still works.
    """
    try:
        from .store import Store
        from .market import import_rows
    except ImportError:
        return {"status": "UNAVAILABLE", "reason": "local market/Store modules not installed"}
    if not rows:
        return {"status": "NO_ROWS", "accepted": 0}
    payload = []
    for row in rows:
        payload.append({
            "provider": "ebay", "listing_id": row["listing_id"],
            "title": row["title"], "source_url": row["source_url"],
            "ask": row.get("ask"), "currency": row.get("currency", "USD"),
            "shipping": row.get("shipping"), "observed_at": row["observed_at"],
            "evidence_kind": "active_listing", "research_score": row["research_score"],
            "condition_verified": False, "sold_comp_verified": False,
        })
    try:
        with Store() as store:
            result = import_rows(store, "lead", payload)
    except Exception as exc:  # Optional bridge must never take down discovery.
        return {"status": "IMPORT_REJECTED", "reason": type(exc).__name__}
    return {"status": "SYNCED", "accepted": len(payload), "result": result}


def mac_notification(count: int) -> bool:
    """Optional local desktop notification; message is static, not listing text."""
    if not count or sys.platform != "darwin":
        return False
    import subprocess
    try:
        subprocess.run(["osascript", "-e",
            'display notification "New or changed research leads found" with title "Holy Pokemon"'],
            timeout=5, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except (OSError, subprocess.SubprocessError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="outputs/holy_auto_discovery.sqlite")
    parser.add_argument("--output", default="outputs/auto_discovery")
    parser.add_argument("--import-csv", action="append", default=[], help="Operator-supplied listing CSV")
    parser.add_argument("--live", action="store_true", help="Enable official read-only eBay Browse")
    parser.add_argument("--sync-app", action="store_true", help="Import discovered research leads into newer Holy Pokemon local Store, if present")
    parser.add_argument("--notify-mac", action="store_true", help="Send local macOS notification when new/changed leads appear")
    parser.add_argument("--authorized-keyset", action="store_true", help="Confirm permitted production credentials and use")
    parser.add_argument("--credentials-file", help="Private mode-0600 JSON; alternatively use eBay env vars")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--once", action="store_true")
    group.add_argument("--watch", action="store_true")
    parser.add_argument("--interval-minutes", type=int, default=30)
    parser.add_argument("--queries-per-cycle", type=int, default=2)
    parser.add_argument("--min-query-hours", type=int, default=6)
    parser.add_argument("--daily-api-limit", type=int, default=30)
    args = parser.parse_args(argv)
    if args.live != args.authorized_keyset:
        parser.error("For live use, both --live and --authorized-keyset are required")
    if not (5 <= args.interval_minutes <= 1440 and 1 <= args.queries_per_cycle <= 5 and
            1 <= args.min_query_hours <= 168 and 1 <= args.daily_api_limit <= 100):
        parser.error("Unsafe polling or quota configuration")
    db_path = Path(args.database)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    output = Path(args.output)
    with sqlite3.connect(db_path) as db:
        initialize(db)
        all_alerts = []
        for path in args.import_csv:
            rows = load_operator_csv(Path(path))
            all_alerts.extend(store_leads(db, rows, query_id="operator_import"))
        if not args.live:
            result = export(db, output, all_alerts)
            if args.sync_app:
                rows = [json.loads(r[0]) for r in db.execute("SELECT snapshot_json FROM holy_auto_leads")]
                result["app_sync"] = sync_into_holy_pokemon(rows)
            if args.notify_mac:
                mac_notification(len(all_alerts))
            print(json.dumps({"mode": "OFFLINE_IMPORT", **result}, indent=2))
            return 0
        try:
            cid, secret = credentials(args.credentials_file)
        except (EbayError, OSError, ValueError) as exc:
            result = export(db, output, all_alerts)
            print(json.dumps({"mode": "NO_AUTHORIZED_CREDENTIALS", "detail": "Set local eBay keyset securely", **result}))
            return 2
        client = EbayBrowse(db, enabled=True, production_approved=True,
                            client_id=cid, client_secret=secret,
                            daily_limit=args.daily_api_limit, max_pages=1)
        failed = False
        try:
            while True:
                status, alerts = scan_once(db, client, maximum_queries=args.queries_per_cycle,
                                           min_gap_hours=args.min_query_hours)
                all_alerts.extend(alerts)
                result = export(db, output, all_alerts)
                if args.sync_app:
                    rows = [json.loads(r[0]) for r in db.execute("SELECT snapshot_json FROM holy_auto_leads")]
                    result["app_sync"] = sync_into_holy_pokemon(rows)
                if args.notify_mac:
                    mac_notification(len(all_alerts))
                print(json.dumps({"mode": "OFFICIAL_EBAY_READ_ONLY", **status, **result}), flush=True)
                all_alerts = []
                if status["errors"]:
                    failed = True
                if not args.watch or failed:
                    break
                time.sleep(args.interval_minutes * 60)
        except KeyboardInterrupt:
            print("Holy Pokemon discovery watcher stopped by user.")
    return 3 if args.live and failed else 0


if __name__ == "__main__":
    sys.exit(main())