"""Source-neutral cash-cycle, venue and retry comparisons with explicit unknowns."""

from __future__ import annotations
from datetime import date
from decimal import Decimal as D
from .strategy_engine import money, q, binary_break_even, budget_check


def venue_comparison(body):
    basis = money(body.get("basis"), required=False)
    annual = money(body.get("annual_capital_pct"), required=False)
    rows = []
    for quote in body.get("venues", []):
        required = (
            "gross",
            "fee_pct",
            "fixed_fee",
            "shipping",
            "insurance",
            "tax",
            "days_to_cash",
        )
        vals = {k: money(quote.get(k), required=False) for k in required}
        missing = [k for k, v in vals.items() if v is None]
        if not quote.get("source_url") or not quote.get("effective_at"):
            missing.append("dated_source_quote")
        net = profit = capital_cost = None
        if not missing:
            if vals["fee_pct"] > 100:
                raise ValueError("Invalid fee percentage")
            net = vals["gross"] * (1 - vals["fee_pct"] / 100) - sum(
                vals[k] for k in ("fixed_fee", "shipping", "insurance", "tax")
            )
            profit = net - basis if basis is not None else None
            capital_cost = (
                basis * annual / 100 * vals["days_to_cash"] / 365
                if basis is not None and annual is not None
                else None
            )
        rows.append(
            {
                "venue": quote.get("venue"),
                "net_if_sold": q(net),
                "profit_if_sold": q(profit),
                "capital_carry_cost": q(capital_cost),
                "time_adjusted_profit": q(profit - capital_cost)
                if profit is not None and capital_cost is not None
                else None,
                "days_to_cash": quote.get("days_to_cash"),
                "source_url": quote.get("source_url"),
                "effective_at": quote.get("effective_at"),
                "missing": missing,
                "realized": False,
            }
        )
    return {
        "venues": rows,
        "note": "Own dated fee quotes and liquidity assumptions, not guaranteed sales or payouts.",
    }


def retry_analysis(stop_net, success_exit, failure_exit, remaining_attempt_cost):
    stop = money(stop_net)
    success = money(success_exit)
    failure = money(failure_exit)
    cost = money(remaining_attempt_cost)
    a = success - cost - stop
    b = failure - cost - stop
    return {
        "stop_net": q(stop),
        "retry_success_incremental": q(a),
        "retry_failure_incremental": q(b),
        "break_even_success_sensitivity": binary_break_even(a, b),
        "measured_success_probability": None,
        "decision": "NO_FINANCIAL_UPSIDE"
        if a <= 0
        else "REQUIRES_INDEPENDENT_EVIDENCE",
        "note": "Prior fees are sunk; a failed prior attempt does not make the next attempt more likely to succeed.",
    }


def portfolio_report(holdings, *, asof):
    locked = D(0)
    unknown = 0
    by_state = {}
    by_grader = {}
    aging = []
    for r in holdings:
        basis = money(r.get("all_in_cost"), required=False)
        state = r.get("current_state", r.get("state", "unknown"))
        if r.get("realized_cash") is None and state != "transferred":
            if basis is None:
                unknown += 1
            else:
                locked += basis
                by_state[state] = by_state.get(state, D(0)) + basis
                grader = r.get("grader", "unknown")
                by_grader[grader] = by_grader.get(grader, D(0)) + basis
        acquired = r.get("owner_acquired_at") or r.get("observed_at")
        age = (asof - date.fromisoformat(acquired[:10])).days if acquired else None
        aging.append(
            {
                "id": r["id"],
                "age_days": age,
                "review_liquidation": age is not None
                and age >= 90
                and r.get("realized_cash") is None,
            }
        )
    return {
        "capital_locked_known": q(locked),
        "holdings_unknown_basis": unknown,
        "by_state": {k: q(v) for k, v in by_state.items()},
        "by_grader": {k: q(v) for k, v in by_grader.items()},
        "aging": aging,
        "capital": budget_check([locked]),
        "realized_vs_paper": "Only matched verified receipts are realized.",
    }
