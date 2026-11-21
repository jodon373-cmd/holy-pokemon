"""Authorized/manual market evidence. Exact variant matching, dated sales, no ask contamination."""

from __future__ import annotations
import csv
import io
import os
from datetime import date, datetime, timezone
from statistics import median
from urllib.parse import urlencode
from .provider_common import public_url
from .store import stable, now
from .strategy_engine import money, research_signal

IDENTITY = (
    "game",
    "year",
    "set",
    "number",
    "denominator",
    "name",
    "language",
    "edition",
    "finish",
    "stamp",
    "error_variant",
    "art_version",
)
VENUES = {"ebay", "psa_vault", "fanatics_collect", "arizona_tcg", "private", "manual"}


def exact_key(r):
    return tuple(str(r.get(k, "")).strip().casefold() for k in IDENTITY)


def identity_complete(r):
    return all(
        r.get(k)
        for k in ("game", "set", "number", "name", "language", "edition", "finish")
    )


def provider_status():
    ebay = bool(os.getenv("EBAY_CLIENT_ID") and os.getenv("EBAY_CLIENT_SECRET"))
    return {
        "ebay_browse": {
            "credentials_present": ebay,
            "production_approved": os.getenv("EBAY_PRODUCTION_APPROVED") == "true",
            "enabled": os.getenv("EBAY_ENABLED") == "true",
            "capability": "ACTIVE_ASKS_ONLY",
        },
        "ebay_sold": {
            "mode": "MANUAL_PRODUCT_RESEARCH_IMPORT",
            "limited_release_api": "NOT_CONNECTED",
        },
        "psa_cert": {
            "credentials_present": bool(
                os.getenv("PSA_API_TOKEN") or os.getenv("PSA_ACCESS_TOKEN")
            ),
            "live_verified": False,
            "capability": "SINGLE_CERT_ONLY",
        },
        "psa_vault": {"mode": "MANUAL_OWNER_IMPORT", "private_api": "UNSUPPORTED"},
        "fanatics_collect": {"mode": "MANUAL_EXPORT", "live_api": "NOT_CONNECTED"},
        "arizona_tcg": {"mode": "MANUAL_EXPORT", "live_api": "NOT_CONNECTED"},
    }


def import_rows(store, kind, rows, *, source_type="USER_IMPORT"):
    if kind not in ("lead", "sale", "holding", "watch", "search", "quote"):
        raise ValueError("Unsupported import kind")
    accepted = 0
    duplicates = 0
    errors = []
    for n, raw in enumerate(rows, 2):
        try:
            row = {str(k).strip(): v for k, v in raw.items() if k is not None}
            if any(
                any(
                    secret in k.lower()
                    for secret in (
                        "password",
                        "client_secret",
                        "api_key",
                        "authorization",
                        "cookie",
                        "access_token",
                    )
                )
                for k in row
            ):
                raise ValueError("Credential fields cannot be imported as evidence")
            source = row.get("source_url") or row.get("url")
            if not source:
                raise ValueError("Source URL required")
            public_url(source)
            if row.get("provider", "manual") not in VENUES:
                raise ValueError(
                    "Unknown provider; use manual with original provider in notes"
                )
            row["source_url"] = source
            row["imported_at"] = row.get("imported_at") or now()
            row["source_type"] = source_type
            row["currency"] = row.get("currency") or (None if kind == "lead" else "USD")
            if not row.get("observed_at"):
                raise ValueError("observed_at date required")
            date.fromisoformat(row["observed_at"][:10])
            if kind == "sale":
                if row.get("evidence_kind") != "completed_sale":
                    raise ValueError("Sold comps require completed_sale evidence_kind")
                if not row.get("transaction_id") and not row.get("sale_id"):
                    raise ValueError("Transaction or sale ID required for dedup")
                if not row.get("sale_date"):
                    raise ValueError("sale_date required")
                day = date.fromisoformat(row["sale_date"][:10])
                if day > datetime.now(timezone.utc).date():
                    raise ValueError("Future sale date")
                row["price"] = str(money(row.get("price")))
                key = stable("transaction", row.get("transaction_id") or row["sale_id"])
                if store.get(kind, key):
                    duplicates += 1
                    continue
                # Strong mirrored transaction match; ask-only records never enter here.
                duplicate = next(
                    (
                        x
                        for x in store.rows("sale")
                        if exact_key(x) == exact_key(row)
                        and x.get("cert")
                        and x.get("cert") == row.get("cert")
                        and x["sale_date"] == row["sale_date"]
                        and x["price"] == row["price"]
                    ),
                    None,
                )
                if duplicate:
                    duplicates += 1
                    continue
            elif kind == "holding":
                if not row.get("item_id"):
                    raise ValueError("Owned collection item_id required")
                if row.get("state") not in (
                    "lead",
                    "acquired_pending",
                    "vaulted",
                    "owner_possession",
                    "held",
                    "consigned",
                    "listed_bin",
                    "listed_auction",
                    "sold_unpaid",
                    "sold_paid",
                    "payout_pending",
                    "paid_out",
                    "withdraw_requested",
                    "withdrawn",
                    "submitted_for_grading",
                    "transferred",
                    "unsold",
                    "relisted",
                ):
                    raise ValueError("Unknown custody state")
                row["cert"] = row.get("cert") or row.get("psa_cert")
                if row.get("vault_id_masked") and "*" not in row["vault_id_masked"]:
                    raise ValueError("Vault ID must be masked")
                key = stable("holding", row["item_id"])
                if row.get("cert") and any(
                    x.get("grader") == row.get("grader")
                    and x.get("cert") == row["cert"]
                    for x in store.rows("holding")
                ):
                    duplicates += 1
                    continue
            else:
                key = stable(
                    kind,
                    row.get("listing_id") or row.get("url") or row.get("source_url"),
                    row.get("observed_at"),
                )
                if kind == "lead":
                    # Same-day price/bid changes are distinct immutable observations.
                    fields = (
                        "title",
                        "ask",
                        "currency",
                        "shipping",
                        "buyer_shipping",
                        "auction_deadline",
                        "current_bid",
                        "bid_count",
                        "buying_options",
                    )
                    snapshot = {k: row.get(k) for k in fields}
                    key = stable(
                        kind,
                        row.get("provider"),
                        row.get("listing_id") or source,
                        row.get("retrieved_at") or row.get("observed_at"),
                        snapshot,
                    )
                for field in (
                    "ask",
                    "buyer_shipping",
                    "purchase_tax",
                    "buyer_premium",
                    "possible_best_exit",
                ):
                    if row.get(field):
                        row[field] = str(money(row[field]))
            if store.get(kind, key):
                duplicates += 1
                continue
            # Import flags are observations, never a purchase authorization.
            row["automatic_execution"] = False
            accepted += store.put(kind, key, row)
        except (ValueError, TypeError, KeyError) as exc:
            errors.append({"row": n, "error": str(exc)})
    return {"accepted": accepted, "duplicates": duplicates, "errors": errors}


def sales_summary(
    sales,
    identity,
    *,
    asof=None,
    grader=None,
    grade=None,
    designation=None,
    label_era=None,
):
    asof = asof or datetime.now(timezone.utc).date()
    if not identity_complete(identity):
        return {"status": "INCOMPLETE_IDENTITY", "count": 0, "net": None}
    if grader in ("CGC", "BGS") and str(grade) == "10" and not designation:
        return {"status": "DESIGNATION_REQUIRED", "count": 0}
    if grader == "CGC" and str(grade) == "9.5" and not label_era:
        return {"status": "CGC_LABEL_ERA_REQUIRED", "count": 0}
    valid = []
    for r in sales:
        age = (asof - date.fromisoformat(r["sale_date"][:10])).days
        if age < 0 or exact_key(r) != exact_key(identity) or r.get("currency") != "USD":
            continue
        if r.get("evidence_kind") != "completed_sale" or r.get(
            "exact_variant_verified"
        ) not in (True, "true", "yes", "1"):
            continue
        if (
            grader
            and r.get("grader") != grader
            or grade
            and str(r.get("grade")) != str(grade)
        ):
            continue
        if (
            designation
            and r.get("designation") != designation
            or label_era
            and r.get("label_era") != label_era
        ):
            continue
        if r.get("qualifier") not in (None, "", "none", "unqualified"):
            continue
        valid.append((age, r))
    result = {
        "status": "VERIFIED_MANUAL_EVIDENCE" if valid else "NO_EXACT_SOLD_COMPS",
        "count": len(valid),
        "asof": str(asof),
        "windows": {},
        "sources": [r for _, r in valid],
    }
    for horizon in (30, 90, 180):
        values = sorted(money(r["price"]) for age, r in valid if age <= horizon)
        result["windows"][str(horizon)] = {
            "count": len(values),
            "median": str(median(values)) if values else None,
            "lower_quartile": str(values[(len(values) - 1) // 4]) if values else None,
            "thin_market": len(values) < 3,
        }
    return result


def rank_leads(store):
    items = []
    latest = {}
    for r in store.rows("lead"):
        latest[
            (
                r.get("provider"),
                r.get("listing_id") or r.get("url") or r.get("source_url"),
            )
        ] = r
    for r in latest.values():
        signal = research_signal(r)
        # Explicit manual review, rather than truthy CSV strings, controls readiness.
        signal["approval"] = "NEED_MORE_EVIDENCE"
        decisions = [d for d in store.rows("decision") if d.get("lead_id") == r["id"]]
        if decisions:
            from .provider_common import timestamp
            from datetime import timedelta

            last = decisions[-1]
            if datetime.now(timezone.utc) - timestamp(last["reviewed_at"]) < timedelta(
                hours=24
            ):
                from .decision import review_candidate

                current = review_candidate(store, last["review_inputs"], persist=False)
                signal["approval"] = current["approval"]
                signal["evidence_gaps"] = current["evidence_gaps"]
        spread = signal["research_spread"]
        priority = float(spread) if spread else None
        vault_state = {}
        for attribute in (
            "already_in_psa_vault",
            "vault_eligible",
            "psa_consignment_listing",
        ):
            val = r.get(attribute, "unknown")
            vault_state[attribute] = (
                val
                if val in ("yes", "no") and r.get(attribute + "_evidence")
                else "unknown"
            )
        items.append(
            {
                **r,
                **signal,
                **vault_state,
                "priority": priority,
                "vault_status": r.get("vault_status", "unknown"),
                "sold_search": "https://www.ebay.com/sch/i.html?"
                + urlencode(
                    {
                        "_nkw": r.get("title") or r.get("name", "Pokemon"),
                        "LH_Sold": "1",
                        "LH_Complete": "1",
                    }
                ),
            }
        )
    return sorted(
        items,
        key=lambda r: (
            r["priority"] is not None,
            r["priority"] or 0,
            int(r.get("research_score") or 0),
        ),
        reverse=True,
    )


def csv_export(rows):
    fields = sorted({k for r in rows for k in r})
    f = io.StringIO()
    w = csv.DictWriter(f, fieldnames=fields)
    w.writeheader()
    for row in rows:
        safe = {}
        for k, v in row.items():
            if isinstance(v, (dict, list)):
                import json

                v = json.dumps(v)
            text = str(v) if v is not None else ""
            if text.lstrip().startswith(("=", "+", "-", "@", "\t", "\r")):
                text = "'" + text
            safe[k] = text
        w.writerow(safe)
    return f.getvalue()
