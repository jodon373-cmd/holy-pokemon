"""Read-only, opt-in CompSniper research adapter for Holy Pokémon.

Only published endpoints; no undocumented PSA/Vault image API. stdlib only.
Nothing is purchased and nothing is sent until --live is explicitly supplied.
Third-party sale reports are NOT independently verified transactions.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import statistics
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

BASE = "https://api.compsniper.com"
ALLOWED = {
    "/v1/psa/search", "/v1/psa/card", "/v1/psa/sets", "/v1/psa/set",
    "/v1/research/sold", "/v1/scrape", "/v1/account/usage", "/v1/best-offer-prices",
}
DEFAULT_CACHE = Path("work/compsniper_cache")
PSA_CERT_BASE = "https://www.psacard.com/cert/"
EBAY_ITEM_RE = re.compile(r"/itm/(?:[^/?#]+/)?(\d{9,15})(?:[/?#]|$)")
QUALIFIER_RE = re.compile(r"\b(OC|MC|ST|PD|MK)\b", re.IGNORECASE)


def money(value):
    """Only accept finite non-negative numeric values; never manufacture zero."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value).replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        return None
    if not result.is_finite() or result < 0:
        return None
    return result.quantize(Decimal("0.01"))


def iso_date(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc).isoformat()
    except (TypeError, ValueError):
        return None


def safe_source_url(value):
    """No non-HTTPS sources or credential-bearing URLs in the evidence ledger."""
    if not isinstance(value, str):
        return None
    u = urlparse(value)
    if u.scheme != "https" or not u.hostname or u.username or u.password:
        return None
    if any(k in u.query.lower() for k in ("token=", "key=", "secret=", "authorization=")):
        return None
    return value


def psa_cert_url(cert):
    cert = str(cert or "").strip()
    return PSA_CERT_BASE + cert if re.fullmatch(r"\d{6,12}", cert) else None


def _grade(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        return Decimal(str(value).replace("PSA", "").strip())
    except InvalidOperation:
        return None


def normalize_psa_sales(payload, *, spec_id, grade):
    """Reject ungraded/wrong-company/wrong-grade rows, plus ambiguous sale amounts.

    A response filtered by grade may STILL contain ungraded items per provider docs.
    A PSA population 'gem rate' is descriptive, not an upgrade likelihood.
    """
    card = payload.get("card") or {}
    if not str(spec_id).isdigit() or str(card.get("specId")) != str(spec_id):
        raise ValueError("PSA spec ID mismatch: do not blend different card variants")
    wanted = _grade(grade)
    if wanted is None or wanted < 1 or wanted > 10:
        raise ValueError("Invalid PSA grade")
    kept, rejected, seen = [], {}, set()
    for item in payload.get("items", []):
        reason = None
        if not isinstance(item, dict):
            reason = "malformed_row"
            item = {}
        company = str(item.get("gradingCompany") or "").upper().strip()
        if not reason and company != "PSA":
            reason = "not_psa"  # Example official docs contain an UNGRADED row!
        if not reason and _grade(item.get("grade")) != wanted:
            reason = "wrong_grade_or_ungraded"
        if not reason and (item.get("qualifier") or QUALIFIER_RE.search(str(item.get("grade") or ""))):
            reason = "qualifier_requires_manual_review"
        price = money(item.get("salePrice"))
        if not reason and price is None:
            reason = "no_exact_price"
        date = iso_date(item.get("saleDate"))
        if not reason and not date:
            reason = "no_sale_date"
        url = safe_source_url(item.get("url"))
        if not reason and not url:
            reason = "no_source_link"
        if reason:
            rejected[reason] = rejected.get(reason, 0) + 1
            continue
        match = EBAY_ITEM_RE.search(url)
        item_id = match.group(1) if match else None
        # Source URL and sale date identify the observation; never dedup solely
        # by card identity, price, or grading cert.
        key = (item_id or url, date, str(wanted))
        if key in seen:
            rejected["duplicate_observation"] = rejected.get("duplicate_observation", 0) + 1
            continue
        seen.add(key)
        sale_type = str(item.get("saleType") or "unknown")
        is_offer = "offer" in sale_type.lower()
        kept.append({
            "provider": "compsniper_psa", "evidence_status": "THIRD_PARTY_REPORTED_SALE_NOT_ORIGIN_VERIFIED",
            "psa_spec_id": str(spec_id), "psa_grade": str(wanted),
            "card": card, "sale_date_utc": date, "sale_price_usd_reported": str(price),
            "sale_type": sale_type, "price_basis": "BEST_OFFER_ACCEPTED_UNVERIFIED" if is_offer else "REPORTED_GROSS_SALE",
            "sold_source_url": url, "ebay_item_id": item_id,
            "cert_number": str(item.get("certNumber")) if item.get("certNumber") else None,
            "psa_cert_url": psa_cert_url(item.get("certNumber")),
            "automated_trade_approval": False,
        })
    kept.sort(key=lambda x: x["sale_date_utc"], reverse=True)
    recent = [Decimal(x["sale_price_usd_reported"]) for x in kept[:5]]
    return {
        "identity": card, "psa_spec_id": str(spec_id), "psa_grade": str(wanted),
        "sales": kept, "rejection_counts": rejected,
        "last_five_reported_median_usd": str(statistics.median(recent)) if recent else None,
        "last_five_reported_count": len(recent),
        "provider_summary_is_independent_sale_evidence": False,
        "population_not_upgrade_probability": True,
        "psa_secure_scan_in_this_api": "NOT_DOCUMENTED",
        "trade_approved": False,
    }


def normalize_research_history(payload):
    """3-year endpoint emits listing aggregates, NOT a per-sale transaction feed.

    Only 1-unit records are usable as tentative sold rows. No automatic identity
    matching is available here; a human/strict model must verify exact variant.
    """
    result, skipped = [], {}
    for row in payload.get("results", []):
        reason = None
        if row.get("recordType") != "single_unit_listing" or row.get("soldUnits") != 1:
            reason = "aggregate_not_individual_sale"
        sold = row.get("soldPrice") or {}
        amount = money(sold.get("amount") if isinstance(sold, dict) else None)
        if not reason and amount is None:
            reason = "no_specific_sale_amount"
        url = safe_source_url(row.get("itemUrl"))
        if not reason and not url:
            reason = "no_source_link"
        date = row.get("soldDate")
        if not reason and not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(date)):
            reason = "no_sale_date"
        if reason:
            skipped[reason] = skipped.get(reason, 0) + 1
            continue
        result.append({
            "provider": "compsniper_ebay_research",
            "source": payload.get("source", "ebay_product_research"),
            "sale_date": date, "sale_price_usd_reported": str(amount),
            "title": row.get("title"), "source_url": url,
            "item_id": str(row.get("itemId") or ""),
            "source_image_url": safe_source_url(row.get("imageUrl")),
            "photo_quality": "UNVERIFIED_NOT_PSA_SECURESCAN",
            "grade_and_variant_verified": False,
            "price_basis": "RESEARCH_DISPLAY_PRICE_NOT_CONFIRMED_ACCEPTED_OFFER",
            "trade_approved": False,
        })
    return {"sales_needing_identity_review": result, "rejection_counts": skipped,
            "listings_are_not_unique_transactions": True, "trade_approved": False}


def normalize_recent_sold(payload):
    """Keep exact accepted-offer price semantics; no automatic variant approval.

    Best Offer rows with pending/unavailable accepted price are UNKNOWN, not
    verified transactions at the displayed listing price.
    """
    records, rejected = [], {}
    if not isinstance(payload, dict) or not isinstance(payload.get("items"), list):
        raise ValueError("Unexpected recent-sold response")
    for row in payload["items"]:
        if not isinstance(row, dict):
            rejected["malformed"] = rejected.get("malformed", 0) + 1
            continue
        link = safe_source_url(row.get("url"))
        date = iso_date(row.get("endedAt"))
        title = str(row.get("title") or "").strip()
        if not link or not date or not title:
            rejected["missing_source_date_or_title"] = rejected.get("missing_source_date_or_title", 0) + 1
            continue
        currency = row.get("soldCurrency")
        if currency != "USD":
            rejected["not_usd"] = rejected.get("not_usd", 0) + 1
            continue
        listed = money(row.get("soldPrice"))
        if listed is None:
            rejected["no_listed_sale_price"] = rejected.get("no_listed_sale_price", 0) + 1
            continue
        offer = row.get("bestOfferAccepted") is True
        status = row.get("acceptedOfferPriceStatus")
        accepted = money(row.get("acceptedOfferPrice")) if status == "found" else None
        has_resolved_price = (not offer or accepted is not None)
        records.append({
            "provider": "compsniper_recent_ebay_sold",
            "source_url": link, "item_id": str(row.get("itemId") or ""),
            "title": title, "ended_at_utc": date,
            "listing_price_usd": str(listed),
            "best_offer_accepted": offer,
            "accepted_offer_status": status if offer else None,
            "accepted_offer_price_usd": str(accepted) if accepted is not None else None,
            "transaction_price_usd_reported": str(accepted) if accepted is not None
                else (str(listed) if not offer else None),
            "price_basis": "THIRD_PARTY_REPORTED_ACCEPTED_OFFER" if accepted is not None
                else ("UNKNOWN_PENDING_OR_UNAVAILABLE_BEST_OFFER" if offer
                      else "THIRD_PARTY_REPORTED_SOLD_PRICE"),
            "title_variant_and_grade_verified": False,
            "price_resolved": has_resolved_price,
            "trade_approved": False,
            "image_source_url": safe_source_url(row.get("fullResThumbnailUrl"))
                or safe_source_url(row.get("thumbnailUrl")),
            "image_source_type": "EBAY_MARKETPLACE_IMAGE_NOT_PSA_SECURESCAN",
        })
    return {"records_needing_variant_validation": records,
            "rejection_counts": rejected, "trade_approved": False}


def enrich_comp_index(client, index, listing, *, target_grader='CGC', target_grade='GEM_MINT_10'):
    """Opt-in, exact-identity reports only. Unresolved offers never become price evidence."""
    from .comp_index import CompIndex, CompRecord, _norm_edition, _norm_number, _norm_set
    from .title_parser import parse_title
    card = str(listing.get('card') or '')
    number = str(listing.get('number') or '')
    set_name = str(listing.get('set_name') or listing.get('set') or '')
    if not all((card, number, set_name, listing.get('edition'), listing.get('finish'))):
        return index, dict(status='MISSING_EXACT_IDENTITY', added=0)
    keyword = ' '.join([card, number, set_name, target_grader,
                        '10 Gem Mint' if target_grade=='GEM_MINT_10' else target_grade])[:200]
    report = normalize_recent_sold(client.recent_sold(keyword))
    added, pending = [], []
    for row in report['records_needing_variant_validation']:
        if not row['price_resolved']:
            continue
        p = parse_title(row['title'])
        identity = index.match_title(row['title'])
        bucket = p.cgc_sub_tier or p.grade
        if not identity or p.grader != target_grader or bucket != target_grade:
            pending.append(dict(source_url=row['source_url'], reason='IDENTITY_OR_GRADE_UNRESOLVED'))
            continue
        if (identity['card'].casefold()!=card.casefold() or
            _norm_number(identity['number'])!=_norm_number(number) or
            _norm_set(identity['set_name'])!=_norm_set(set_name) or
            _norm_edition(identity['edition'])!=_norm_edition(listing['edition']) or
            p.finish!=listing['finish'] or p.language!=listing.get('language','English')):
            continue
        added.append(CompRecord(set_name, card, number, listing['edition'], target_grader,
            target_grade,row['ended_at_utc'][:10],money(row['transaction_price_usd_reported']),
            row['source_url'],row['title'],listing['finish'],p.language))
    updated = CompIndex([*index.reported_records, *added])
    newly_usable = set(updated.records) - set(index.records)
    return updated, dict(status='THIRD_PARTY_REPORTED_ONLY',
        added=len(newly_usable), pending_variant_review=pending, trade_approved=False)


class CompSniperClient:
    """Constrained, read-only provider calls with TTL cache and request budgeting."""
    def __init__(self, *, live=False, key=None, max_calls=3,
                 cache_dir=DEFAULT_CACHE, ttl_seconds=21600, timeout=90):
        self.live = bool(live)
        self.key = key if key is not None else os.getenv("COMPSNIPER_API_KEY")
        self.max_calls = int(max_calls)
        if self.max_calls < 0:
            raise ValueError("max_calls must be non-negative")
        self.calls = 0
        self.cache_dir = Path(cache_dir)
        self.ttl_seconds = max(0, int(ttl_seconds))
        self.timeout = int(timeout)

    def get(self, path, **params):
        if path not in ALLOWED:
            raise ValueError("Endpoint not on the reviewed read-only allowlist")
        query = urlencode(sorted((k, str(v).lower() if isinstance(v, bool) else str(v))
                                for k, v in params.items() if v is not None))
        url = BASE + path + ("?" + query if query else "")
        cache_path = self.cache_dir / (sha256(url.encode("utf-8")).hexdigest() + ".json")
        if cache_path.is_file():
            try:
                saved = json.loads(cache_path.read_text(encoding="utf-8"))
                if time.time() - saved["cached_at"] < self.ttl_seconds:
                    return saved["data"]
            except (ValueError, KeyError, OSError, TypeError):
                pass
        if not self.live:
            raise RuntimeError("OFFLINE: no cached response; pass --live to authorize a quota-consuming request")
        if not self.key or not self.key.startswith("cs_live_"):
            raise RuntimeError("COMPSNIPER_API_KEY missing or malformed; create it on provider dashboard")
        if self.calls >= self.max_calls:
            raise RuntimeError("Per-process CompSniper request budget exhausted")
        self.calls += 1  # charge budget even if request fails to avoid retry storms
        req = Request(url, headers={"Authorization": "Bearer " + self.key,
                                    "Accept": "application/json",
                                    "User-Agent": "HolyPokemonResearch/0.1"}, method="GET")
        try:
            with urlopen(req, timeout=self.timeout) as response:
                raw = response.read(8_000_001)
                if len(raw) > 8_000_000:
                    raise RuntimeError("CompSniper response exceeds size cap")
                data = json.loads(raw)
        except HTTPError as exc:
            raise RuntimeError("CompSniper HTTP " + str(exc.code) +
                               "; check permissions, quota and Retry-After (no automatic retry)") from None
        except (URLError, TimeoutError):
            raise RuntimeError("CompSniper network error; no automatic retry") from None
        if not isinstance(data, dict):
            raise RuntimeError("Unexpected CompSniper response type")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        temp = cache_path.with_suffix(".tmp")
        temp.write_text(json.dumps({"cached_at": time.time(), "data": data}), encoding="utf-8")
        temp.replace(cache_path)
        return data

    def psa_search(self, keyword, *, count=10):
        if not keyword or len(keyword) > 200 or not 1 <= count <= 20:
            raise ValueError("Bad PSA search query")
        return self.get("/v1/psa/search", keyword=keyword, count=count)

    def psa_card(self, spec_id, *, grade, count=50, time_range=0):
        if not str(spec_id).isdigit() or not 0 <= count <= 50 or not 0 <= time_range <= 120:
            raise ValueError("Invalid PSA card request")
        return self.get("/v1/psa/card", specId=spec_id, grade=grade,
                        count=count, timeRange=time_range)

    def research_history(self, keyword, *, start, end, page=1):
        if not keyword or len(keyword) > 200:
            raise ValueError("Invalid keyword")
        if not 1 <= page <= 200:
            raise ValueError("Invalid page")
        for date in (start, end):
            datetime.strptime(date, "%Y-%m-%d")
        if start > end:
            raise ValueError("start > end")
        return self.get("/v1/research/sold", keyword=keyword, startDate=start,
                        endDate=end, sort="lastSoldDescending", limit=50,
                        page=page, singleUnitOnly=True, relevance=True,
                        ebaySite="ebay.com")

    def recent_sold(self, keyword, *, count=240):
        if not keyword or len(keyword) > 200 or not 1 <= count <= 240:
            raise ValueError("Invalid eBay search")
        return self.get("/v1/scrape", keyword=keyword, count=count,
                        ebaySite="ebay.com", bestOfferPrice=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Holy Pokémon opt-in, read-only CompSniper access")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--search", help="Discover exact PSA card spec IDs (review before using)")
    selection.add_argument("--spec-id", help="Fetch and validate exact-card PSA sale records")
    selection.add_argument("--history", help="3-year eBay Research; individual one-unit listings only")
    selection.add_argument("--recent", help="Recent sold listings with Best Offer price request")
    parser.add_argument("--grade", default="10")
    parser.add_argument("--start", help="YYYY-MM-DD start for --history")
    parser.add_argument("--end", help="YYYY-MM-DD end for --history")
    parser.add_argument("--live", action="store_true", help="ALLOW quota-consuming HTTPS requests")
    parser.add_argument("--max-calls", type=int, default=3)
    parser.add_argument("--cache-dir", default=str(DEFAULT_CACHE))
    parser.add_argument("--output", help="Optional JSON report path; no secrets")
    args = parser.parse_args(argv)
    if not args.live:
        print(json.dumps({"status": "DRY_RUN_NO_API_REQUESTS", "selected": args.search or args.spec_id or args.history or args.recent,
                          "instructions": "Set COMPSNIPER_API_KEY and repeat with --live; spec-id must be manually selected."}, indent=2))
        return 0
    client = CompSniperClient(live=True, max_calls=args.max_calls, cache_dir=args.cache_dir)
    if args.search:
        report = client.psa_search(args.search)
    elif args.spec_id:
        report = normalize_psa_sales(client.psa_card(args.spec_id, grade=args.grade),
                                     spec_id=args.spec_id, grade=args.grade)
    elif args.history:
        if not args.start or not args.end:
            parser.error("--history requires --start and --end")
        report = normalize_research_history(client.research_history(args.history,
                                                                    start=args.start, end=args.end))
    else:
        report = normalize_recent_sold(client.recent_sold(args.recent))
    if args.output:
        p = Path(args.output)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
