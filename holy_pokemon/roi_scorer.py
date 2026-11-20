"""Risk-adjusted ROI & opportunity scorer for Holy Pokémon.

Combines landed acquisition cost, conservative P25/median dated sold comps,
grading/shipping/selling fees, and optional centering_v3 geometry eligibility.
Never sets trade_approved=True; outputs ranked research leads only.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Mapping

from .comp_index import CompIndex, CompSummary
from .title_parser import ParsedListing, parse_title

D = Decimal
CENT = D("0.01")


@dataclass(frozen=True)
class FeeSchedule:
    seller_fee_pct: Decimal = D("13.0")
    grading_fee: Decimal = D("35.0")
    grading_shipping: Decimal = D("20.0")
    grading_insurance: Decimal = D("10.0")
    upcharge: Decimal = D("0.0")
    outbound_shipping: Decimal = D("6.0")
    purchase_tax_pct: Decimal = D("7.0")


def _q(v: Decimal | None) -> str | None:
    return str(v.quantize(CENT)) if v is not None else None


def score_opportunity(
    *,
    listing: Mapping[str, Any],
    card: str,
    number: str,
    comp_index: CompIndex,
    target_grader: str = "CGC",
    target_grade_bucket: str = "GEM_MINT_10",
    set_name: str | None = None,
    edition: str | None = None,
    centering_result: Mapping[str, Any] | None = None,
    fees: FeeSchedule | None = None,
    expected_language: str = "English",
    fallback_grade_bucket: str = "9",
) -> dict[str, Any]:
    """Score a candidate listing against dated comps with full downside math."""
    fees = fees or FeeSchedule()
    title = str(listing.get("title") or "")
    parsed: ParsedListing = parse_title(title, expected_language=expected_language)

    def incomplete(status: str) -> dict[str, Any]:
        return {"listing_id": listing.get("listing_id"), "title": title,
                "parsed": parsed.to_dict(), "status": status,
                "opportunity_score": 0.0, "trade_approved": False,
                "landed_cost_usd": None}

    if parsed.disqualified:
        return incomplete("DISQUALIFIED")
    if parsed.card_number and parsed.card_number.casefold() != str(number).lstrip("0").casefold():
        return incomplete("IDENTITY_MISMATCH")
    if not set_name or not card or not number or parsed.finish == "Unspecified":
        return incomplete("NEEDS_EXACT_IDENTITY")
    if listing.get("currency", "USD") != "USD":
        return incomplete("UNSUPPORTED_CURRENCY")
    ask_raw = listing.get("asking_price", listing.get("ask"))
    ship_raw = listing.get("shipping", listing.get("buyer_shipping"))
    if ask_raw in (None, ""):
        return incomplete("SKIPPED_NO_ASKING_PRICE")
    if ship_raw in (None, ""):
        return incomplete("MISSING_SHIPPING_COST")
    try:
        ask, ship = D(str(ask_raw)), D(str(ship_raw))
        if not ask.is_finite() or not ship.is_finite() or ask <= 0 or ship < 0:
            return incomplete("INVALID_COST")
    except (InvalidOperation, ValueError):
        return incomplete("INVALID_COST")
    tax = (ask * fees.purchase_tax_pct / D("100")).quantize(CENT)
    landed = ask + ship + tax

    target_comp: CompSummary | None = comp_index.summarize(
        card=card,
        number=number,
        grader=target_grader,
        grade_bucket=target_grade_bucket,
        set_name=set_name,
        edition=edition or parsed.edition,
        finish=parsed.finish, language=parsed.language,
    )
    # Regrading destroys the original holder; use target-company failure comps.
    fallback_comp = comp_index.summarize(
        card=card, number=number, grader=target_grader,
        grade_bucket=fallback_grade_bucket, set_name=set_name,
        edition=edition or parsed.edition, finish=parsed.finish, language=parsed.language,
    )

    all_in_grading = fees.grading_fee + fees.grading_shipping + fees.grading_insurance + fees.upcharge
    fee_mult = D("1") - fees.seller_fee_pct / D("100")

    conservative_net: Decimal | None = None
    upside_net: Decimal | None = None
    downside_net: Decimal | None = None
    break_even_rate: Decimal | None = None

    if target_comp is not None:
        conservative_net = target_comp.p25_usd * fee_mult - all_in_grading - fees.outbound_shipping - landed
        upside_net = target_comp.median_usd * fee_mult - all_in_grading - fees.outbound_shipping - landed
    if fallback_comp is not None:
        downside_net = fallback_comp.p25_usd * fee_mult - all_in_grading - fees.outbound_shipping - landed

    if conservative_net is not None and downside_net is not None and conservative_net > downside_net:
        if downside_net >= 0:
            break_even_rate = D("0.0000")
        elif conservative_net > 0:
            break_even_rate = (-downside_net / (conservative_net - downside_net)).quantize(D("0.0001"))

    # Composite 0-100 opportunity score
    score = 0.0
    if not parsed.disqualified and conservative_net is not None and conservative_net > 0:
        roi_pct = float(conservative_net / max(landed, D("1")) * D("100"))
        spread_pts = min(45.0, roi_pct * 0.45)
        comp_pts = min(25.0, (target_comp.count if target_comp else 0) * 5.0)
        conf_pts = parsed.confidence * 20.0
        center_pts = 0.0
        if centering_result and centering_result.get("status") == "MEASURED_NEEDS_VALIDATION":
            elig = centering_result.get("eligibility") or {}
            c_score = float(elig.get("centering_score") or 0.0)
            center_pts = (c_score / 100.0) * 10.0
        score = round(min(100.0, spread_pts + comp_pts + conf_pts + center_pts), 1)

    return {
        "cost_basis": "ILLUSTRATIVE_CONFIGURABLE_FEES_NOT_QUOTES",
        "downside_basis": f"{target_grader}_{fallback_grade_bucket}_SCENARIO_NOT_WORST_CASE",
        "fees": {name: str(value) for name, value in vars(fees).items()},
        "listing_id": listing.get("listing_id"),
        "url": listing.get("url"),
        "title": title,
        "card": card,
        "number": number,
        "parsed": parsed.to_dict(),
        "landed_cost_usd": _q(landed),
        "target_route": f"{target_grader}_{target_grade_bucket}",
        "target_comp": target_comp.to_dict() if target_comp else None,
        "fallback_comp": fallback_comp.to_dict() if fallback_comp else None,
        "conservative_net_profit_usd": _q(conservative_net),
        "upside_net_profit_usd": _q(upside_net),
        "downside_net_profit_usd": _q(downside_net),
        "break_even_upgrade_rate": str(break_even_rate) if break_even_rate is not None else None,
        "opportunity_score": score,
        "status": "DISQUALIFIED" if parsed.disqualified else ("SCORED_LEAD" if target_comp else "MISSING_TARGET_COMPS"),
        "trade_approved": False,
    }
