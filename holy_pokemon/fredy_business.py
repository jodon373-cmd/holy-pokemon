"""Evidence-backed Fredy business reconstruction. Read-only; never equate video values with cash payouts."""

from __future__ import annotations
import csv
import json
import hashlib
import zipfile
from collections import Counter
from decimal import Decimal as D
from pathlib import Path
from typing import Any

MONTH_ORDER = (
    "2026-02",
    "2026-03",
    "2026-04",
    "2026-05",
    "2026-06",
    "2026-07",
    "2026-08",
    "2026-09",
)


def monthly_analysis(csv_path: str | Path) -> dict[str, Any]:
    with Path(csv_path).open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    if [r["month"] for r in rows] != list(MONTH_ORDER):
        raise ValueError(
            "Expected canonical February–September 2026 without duplicate/retrospective months"
        )
    total = {
        "sold": 0,
        "revenue": D(0),
        "sold_basis": D(0),
        "reported_profit": D(0),
        "monthly_spending": D(0),
    }
    reports = []
    for r in rows:
        sold = int(r["cards_sold"])
        revenue = D(r["revenue_usd"])
        basis = D(r["sold_cost_basis_usd"])
        profit = D(r["reported_pre_tax_profit_usd"])
        spend = D(r["monthly_spend_usd"])
        if sold < 0 or any(x < 0 for x in (revenue, basis, profit, spend)):
            raise ValueError("Negative line not allowed")
        if abs(revenue - basis - profit) > D("0.02"):
            raise ValueError(
                "Monthly sold-cost and reported profit do not reconcile: " + r["month"]
            )
        total["sold"] += sold
        total["revenue"] += revenue
        total["sold_basis"] += basis
        total["reported_profit"] += profit
        total["monthly_spending"] += spend
        reports.append(
            {
                "month": r["month"],
                "cards_sold": sold,
                "revenue": str(revenue),
                "sold_basis": str(basis),
                "reported_profit": str(profit),
                "monthly_spend": str(spend),
                "profit_per_sale": str((profit / sold).quantize(D(".01")))
                if sold
                else None,
                "reported_margin_pct": str((profit * 100 / revenue).quantize(D(".01")))
                if revenue
                else None,
                "origin": r["source_archive"],
                "audit_status": r["source_reliability"],
            }
        )
    return {
        "source_months": len(rows),
        "months": reports,
        "totals": {k: str(v) for k, v in total.items()},
        "note": "Creator-reported screen figures; monthly spending is not COGS, never a verified bank cash-flow statement.",
        "may_vs_april_disagreement": "May retrospective April 42 sold/$7,165.10 profit vs April contemporaneous 43/$7,420; retained April contemporaneous.",
        "july_spend_disagreement": "July source $37,422.43 spending vs August retrospective $39,198.44; retained July source.",
        "march_spend_disagreement": "March source $44,795.41 spending vs April retrospective $45,558.23; retained March source.",
        "august_spending_vs_profit": "August spending $47,931.70 is not sold-card cost basis $33,349.52.",
    }


def inspect_transport(transport_zip: str | Path) -> dict[str, Any]:
    """Validate supplied compact transport, source counts and audit the raw schema families."""
    zpath = Path(transport_zip)
    with zipfile.ZipFile(zpath) as z:
        from .ingest import safe_members

        safe_members(z)
        bad = z.testzip()
        if bad:
            raise ValueError("Corrupt zip member " + bad)
        names = set(z.namelist())
        expected = {"source_case_rows.jsonl", "source_asset_inventory.json"}
        if not expected.issubset(names):
            raise ValueError("Missing canonical transport members")
        asset_index = json.loads(z.read("source_asset_inventory.json"))
        raw = z.read("source_case_rows.jsonl").decode("utf-8")
    records = [json.loads(line) for line in raw.splitlines() if line.strip()]
    raw_count = len(records)
    if raw_count != 250:
        raise ValueError(f"Expected 250 original case rows, found {raw_count}")
    by_source = Counter()
    by_game = Counter()
    statuses = Counter()
    record_keys = set()
    exact_duplicates = 0
    for row in records:
        if not isinstance(row.get("source_row"), dict) or not row.get("archive_sha256"):
            raise ValueError("Unverifiable case row")
        by_source[row["source_archive"]] += 1
        by_game[row.get("game", "unknown")] += 1
        statuses[row.get("provenance_status", "unknown")] += 1
        key = (row["archive_sha256"], row.get("member_path"), row.get("row_number"))
        if key in record_keys:
            exact_duplicates += 1
        record_keys.add(key)
    return {
        "transport_sha256": hashlib.sha256(zpath.read_bytes()).hexdigest(),
        "source_assets": len(asset_index),
        "raw_case_rows": raw_count,
        "raw_unique_source_row_keys": len(record_keys),
        "duplicate_source_row_keys": exact_duplicates,
        "by_source": dict(by_source),
        "by_game": dict(by_game),
        "by_provenance": dict(statuses),
        "physical_unique": None,
        "known_limitation": "Source case rows != unique physical specimens; monthly/public/546 overlap unresolved",
        "training_images": 0,
        "model_trained": False,
    }


def operating_rules() -> list[dict[str, str]]:
    """Machine-readable behavioral rules inferred from the uploaded research, not personal mind-reading."""
    return [
        {
            "id": "acquisition",
            "signal": "high-grade exit spread for exact variant with discount on original slab",
            "implementation": "broad discovery -> photo precheck -> original-grade fallback -> max offer",
            "evidence": "April rejected overpriced PSA7 Chansey; multiple EX-era purchases",
        },
        {
            "id": "inspection",
            "signal": "corner whitening, back-border dots, foil scratching, surface streaks and slab glare",
            "implementation": "front/back high-res + magnifier + uncertainty -> defect severity -> route veto/review",
            "evidence": "May Ho-Oh/Espeon/Venusaur rejections; April Shadowless Venusaur",
        },
        {
            "id": "route",
            "signal": "PSA to CGC, PSA to PSA, BGS/CGC crossover, regrade repeat",
            "implementation": "route-specific outcome ladders; every failure pays its own fee",
            "evidence": "Gengar Triumphant PSA8→CGC10; Gardevoir/Sylveon PSA9→PSA10; Rayquaza CGC9→10",
        },
        {
            "id": "avoid_bad_bgs",
            "signal": "BGS9.5 to PSA9 losses can destroy margin",
            "implementation": "subgrade-specific scrutiny, default loss reserve, no assumed 10",
            "evidence": "March Mewtwo VSTAR -$132.18; April Charizard TG -$137.31; May N's Reshiram losses",
        },
        {
            "id": "cash_cycle",
            "signal": "stock, grading pipeline and sale cash occur in different months",
            "implementation": "physical inventory + capital-by-state + aging + payment settlement",
            "evidence": "May ~$158k outstanding/prep; August ~$152k; September ~$488k ready+grading",
        },
        {
            "id": "channel",
            "signal": "sale routing shifted from eBay toward Fanatics and Arizona TCG",
            "implementation": "channel-specific net fee/auction liquidity and cash time comparison",
            "evidence": "February 63/66 eBay, September 79 Fanatics+41 Arizona TCG",
        },
        {
            "id": "market_rescue",
            "signal": "paper gain from appreciation can hide weak grading choice",
            "implementation": "compare sell original today versus final grade today; attribution of price movement",
            "evidence": "June Gengar Triumphant $5k sale after appreciation, market-saved $7999 experiment",
        },
        {
            "id": "sales_priority",
            "signal": "premium CGC Pristine outliers generate concentrated sales profit",
            "implementation": "distribution and exposure caps, don't anchor on rare pristine success",
            "evidence": "September Umbreon $11.7k, Azumarill $17k, Undaunted Umbreon $19k sales",
        },
        {
            "id": "repeat",
            "signal": "sometimes retries after disappointing grades",
            "implementation": "same physical copy; two charged grading events; incremental P&L vs stopping",
            "evidence": "Rayquaza ex PSA9→CGC9→CGC10, Gengar PSA8→CGC8.5→CGC8",
        },
        {
            "id": "exit",
            "signal": "auctions/liquidation to release capital; sale speed differs by slab",
            "implementation": "inventory aging threshold and channel-dependent liquidation what-if",
            "evidence": "July reported auctions to release capital; April CGC slow-selling note",
        },
    ]
