"""Unified offline/live scan pipeline for Holy Pokémon.

Ties together title_parser -> comp_index -> optional centering_v3 -> roi_scorer,
producing ranked JSON and CSV research reports without autonomous purchasing.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .comp_index import CompIndex
from .roi_scorer import FeeSchedule, score_opportunity
from .strategy_common import export_csv


def scan_listings(
    listings: Iterable[Mapping[str, Any]],
    *,
    comp_index: CompIndex | None = None,
    target_grader: str = "CGC",
    target_grade_bucket: str = "GEM_MINT_10",
    fees: FeeSchedule | None = None,
    include_disqualified: bool = False,
) -> dict[str, Any]:
    """Parse, match against dated comps, and rank a batch of listings."""
    idx = comp_index or CompIndex.from_csvs()
    results: list[dict[str, Any]] = []
    disqualified_count = 0

    for item in listings:
        card = str(item.get("card") or "").strip()
        number = str(item.get("number") or "").strip()
        scored = score_opportunity(
            listing=item,
            card=card,
            number=number,
            comp_index=idx,
            target_grader=target_grader,
            target_grade_bucket=target_grade_bucket,
            set_name=item.get("set_name") or item.get("set"),
            edition=item.get("edition"),
            centering_result=item.get("centering"),
            fees=fees,
        )
        if scored["status"] == "DISQUALIFIED":
            disqualified_count += 1
            if not include_disqualified:
                continue
        results.append(scored)

    results.sort(key=lambda r: float(r.get("opportunity_score") or 0.0), reverse=True)
    return {
        "mode": "OFFLINE_SCAN_RESEARCH_ONLY",
        "trade_approved": False,
        "total_scanned": len(results) + (0 if include_disqualified else disqualified_count),
        "disqualified_filtered": disqualified_count,
        "returned_count": len(results),
        "ranked_leads": results,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", required=True, help="JSON file containing a list of candidate listings")
    p.add_argument("--output-json", help="Optional path to write ranked JSON report")
    p.add_argument("--output-csv", help="Optional path to write ranked CSV report")
    p.add_argument("--target-grader", default="CGC")
    p.add_argument("--target-grade", default="GEM_MINT_10")
    p.add_argument("--include-disqualified", action="store_true")
    args = p.parse_args(argv)

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    listings = raw["listings"] if isinstance(raw, dict) and "listings" in raw else raw
    report = scan_listings(
        listings,
        target_grader=args.target_grader,
        target_grade_bucket=args.target_grade,
        include_disqualified=args.include_disqualified,
    )
    if args.output_json:
        out = Path(args.output_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.output_csv:
        flat = [
            {
                "listing_id": r.get("listing_id"),
                "card": r.get("card"),
                "number": r.get("number"),
                "title": r.get("title"),
                "status": r.get("status"),
                "opportunity_score": r.get("opportunity_score"),
                "landed_cost_usd": r.get("landed_cost_usd"),
                "conservative_net_profit_usd": r.get("conservative_net_profit_usd"),
                "upside_net_profit_usd": r.get("upside_net_profit_usd"),
                "downside_net_profit_usd": r.get("downside_net_profit_usd"),
                "break_even_upgrade_rate": r.get("break_even_upgrade_rate"),
                "url": r.get("url"),
                "trade_approved": False,
            }
            for r in report["ranked_leads"]
        ]
        export_csv(args.output_csv, flat)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
