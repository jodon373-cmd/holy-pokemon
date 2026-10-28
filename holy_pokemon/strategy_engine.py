"""Auditable Holy Pokémon opportunity and exit math.

No implicit market prices, probabilities or transactions. Pure standard-library code.
Use for speculative research and manual approvals, not autonomous purchases.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from typing import Mapping, Any

D = Decimal
ZERO = D("0")
CENT = D("0.01")
ROUTES = (
    "sell_original", "legacy_cgc_reholder", "psa_intact_crossover_success",
    "psa_intact_crossover_rejected", "crack_psa_8", "crack_psa_9",
    "crack_psa_10", "cgc_8", "cgc_8_5", "cgc_9", "cgc_9_5",
    "cgc_gem_10", "cgc_pristine_10", "bgs_9", "bgs_9_5",
    "vault_psa_auction", "vault_psa_buy_it_now", "vault_partner_offer",
    "vault_withdraw_then_sell", "vault_withdraw_then_regrade", "hold",
)

def money(value: Any, *, required: bool = True) -> Decimal | None:
    if value is None or str(value).strip() == "":
        if required:
            raise ValueError("Required monetary field missing")
        return None
    try:
        v = D(str(value).replace("$", "").replace(",", "").strip())
    except (InvalidOperation, ValueError):
        raise ValueError(f"Invalid monetary value: {value!r}") from None
    if not v.is_finite() or v < 0:
        raise ValueError("Money must be finite and nonnegative")
    return v

def q(value: Decimal | None) -> str | None:
    return str(value.quantize(CENT)) if value is not None else None

def acquisition_total(row: Mapping[str, Any]) -> Decimal | None:
    """Tax is charged on item price unless operator supplies effective tax basis."""
    price = money(row.get("ask"), required=False)
    ship = money(row.get("buyer_shipping"), required=False)
    tax = money(row.get("purchase_tax"), required=False)
    premium = money(row.get("buyer_premium"), required=False)
    if any(v is None for v in (price, ship, tax, premium)):
        return None
    return price + ship + tax + premium

def outcome(row: Mapping[str, Any], route: Mapping[str, Any],
            *, baseline_net: Decimal | None = None) -> dict[str, Any]:
    """Separate margin above cost from incremental value of regrading."""
    route_name = route.get("route")
    if route_name not in ROUTES:
        raise ValueError("Unknown exit route")
    landed = acquisition_total(row)
    sale = money(route.get("exit_price"), required=False)
    fee = money(route.get("fee_pct"), required=False)
    fees = [money(route.get(k), required=False) for k in (
        "grading", "grading_shipping", "grading_insurance", "upcharge",
        "outbound_shipping", "vault_withdrawal", "vault_early_fee",
        "vault_consignment_fixed", "holding_cost", "contingency")]
    if fee is not None and fee > 100:
        raise ValueError("Invalid fee percent")
    # Requiring explicit costs avoids fake P&L from absent fees.
    complete = landed is not None and sale is not None and fee is not None and all(v is not None for v in fees)
    net = None
    if complete:
        net = sale * (D("1") - fee / D("100")) - sum(fees, ZERO) - landed
    return {
        "route": route_name, "data_complete": complete, "landed": q(landed),
        "exit_price_kind": route.get("exit_price_kind", "unknown"),
        "exit_price": q(sale), "net_profit_if_sold": q(net),
        "incremental_over_original": q(net - baseline_net) if net is not None and baseline_net is not None else None,
        "sale_is_realized": bool(route.get("actual_payout_verified", False)),
        "missing": [field for field in (
            "ask", "buyer_shipping", "purchase_tax", "buyer_premium")
            if row.get(field) in (None, "")] + [
            k for k in ("exit_price", "fee_pct", "grading", "grading_shipping",
                "grading_insurance", "upcharge", "outbound_shipping",
                "vault_withdrawal", "vault_early_fee", "vault_consignment_fixed",
                "holding_cost", "contingency") if route.get(k) in (None, "")
        ]
    }

def compare(row: Mapping[str, Any], routes: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Require route-level evidence, and calculate incremental vs sell-as-is."""
    original = next((r for r in routes if r.get("route") == "sell_original"), None)
    baseline_result = outcome(row, original) if original else None
    baseline = D(baseline_result["net_profit_if_sold"]) if baseline_result and baseline_result["data_complete"] else None
    return [outcome(row, r, baseline_net=baseline) for r in routes]

def binary_break_even(success_profit: Any, failure_profit: Any) -> str | None:
    """Sensitivity threshold, NOT a measured probability."""
    s, f = D(str(success_profit)), D(str(failure_profit))
    if s <= f:
        return None
    if f >= 0:
        return "0.0000"
    if s <= 0:
        return None
    return str((-f / (s - f)).quantize(D("0.0001")))

def research_signal(candidate: Mapping[str, Any]) -> dict[str, Any]:
    """Keep high-upside research visible without inventing missing comps."""
    desired = money(candidate.get("possible_best_exit"), required=False)
    ask = money(candidate.get("ask"), required=False)
    price_discovery = "unknown"
    spread = None
    if desired is not None and ask is not None and ask > 0:
        spread = q(desired - ask)
        price_discovery = "hypothetical_grade_spread_not_profit"
    issues = [k for k in ("exact_variant_verified", "front_photo_reviewed",
        "back_photo_reviewed", "sold_comps_verified", "complete_cost_quote")
        if not candidate.get(k)]
    return {
        "research_visible": True,
        "research_spread": spread,
        "spread_type": price_discovery,
        "approval": "NOT_READY" if issues else "MANUAL_APPROVAL_REQUIRED",
        "evidence_gaps": issues,
    }

def budget_check(commitments: list[Any], *, cap: Any = "2000", reserve: Any = "5000") -> dict[str, Any]:
    total = sum((money(c) for c in commitments), ZERO)
    limit = money(cap)
    return {"all_in_committed": q(total), "first_batch_cap": q(limit),
            "reserve_untouched": q(money(reserve)),
            "within_cap": total <= limit,
            "automated_purchase_authorized": False}
