"""Evidence-based manual readiness. Never grants purchase or money-movement permission."""

from decimal import Decimal as D
from .market import sales_summary, identity_complete
from .strategy_engine import compare, budget_check, money
from .store import stable, now


def review_candidate(store, body, *, persist=True):
    lead = store.get("lead", body["lead_id"])
    if not lead:
        raise ValueError("Unknown lead")
    identity = body.get("identity", {})
    gaps = []
    if not identity_complete(identity) or body.get("identity_confirmed") is not True:
        gaps.append("exact_variant_review")
    if not body.get("seller_evidence") or body.get("seller_verified") is not True:
        gaps.append("seller_and_listing_review")
    if (
        not body.get("front_evidence")
        or not body.get("back_evidence")
        or body.get("photos_reviewed") is not True
    ):
        gaps.append("front_back_physical_condition_review")
    if not body.get("condition_notes"):
        gaps.append("visible_defects_and_hidden_surface_risk")
    sold = sales_summary(
        store.rows("sale"),
        identity,
        grader=body.get("exit_grader"),
        grade=body.get("exit_grade"),
        designation=body.get("exit_designation"),
        label_era=body.get("exit_label_era"),
    )
    if sold.get("windows", {}).get("90", {}).get("count", 0) < 3:
        gaps.append("three_recent_exact_exit_sales")
    original = sales_summary(
        store.rows("sale"),
        identity,
        grader=body.get("original_grader"),
        grade=body.get("original_grade"),
        designation=body.get("original_designation"),
        label_era=body.get("original_label_era"),
    )
    if not original.get("count"):
        gaps.append("original_grade_fallback_sales")
    scenario = body.get("scenario") or {}
    listing = scenario.get("listing", {})
    routes = scenario.get("routes", [])
    evaluated = compare(listing, routes) if listing and routes else []
    if not evaluated or any(not r["data_complete"] for r in evaluated):
        gaps.append("full_cost_quotes")
    if len(evaluated) < 2 or not any(r["route"] == "sell_original" for r in evaluated):
        gaps.append("original_slab_benchmark_and_alternative")
    profits = [
        D(r["net_profit_if_sold"])
        for r in evaluated
        if r["net_profit_if_sold"] is not None
    ]
    downside = min(profits) if profits else None
    if downside is None or downside < -D("200"):
        gaps.append("per_copy_downside_limit_200")
    if len(profits) < 3:
        gaps.append("explicit_unchanged_and_downgrade_or_rejected_outcomes")
    from .vault_workflow import collection

    holdings = collection(store)
    commitments = [
        D(h["all_in_cost"]) + D(h.get("additional_recorded_cash_spent", "0"))
        for h in holdings
        if h.get("all_in_cost") not in ("", None)
    ]
    landed = next((r["landed"] for r in evaluated if r.get("landed")), None)
    # Allocate maximum additional route costs, not just the acquisition ask.
    cost_names = (
        "grading",
        "grading_shipping",
        "grading_insurance",
        "upcharge",
        "vault_withdrawal",
        "vault_early_fee",
        "holding_cost",
        "contingency",
    )
    extra = max(
        (
            sum((money(r.get(k), required=False) or D(0) for k in cost_names), D(0))
            for r in routes
        ),
        default=D(0),
    )
    capital = budget_check(
        commitments + ([D(landed) + extra] if landed is not None else [])
    )
    if (
        not capital["within_cap"]
        or landed is None
        or any(h.get("all_in_cost") in ("", None) for h in holdings)
    ):
        gaps.append("shared_capital_or_unknown_basis")
    status = "NEED_MORE_EVIDENCE" if gaps else "MANUAL_BUY_READY"
    result = {
        "lead_id": lead["id"],
        "approval": status,
        "evidence_gaps": gaps,
        "reviewed_at": now(),
        "identity": identity,
        "sold_evidence": sold,
        "original_grade_evidence": original,
        "routes": evaluated,
        "downside": str(downside) if downside is not None else None,
        "capital": capital,
        "automatic_execution": False,
        "purchase_authorized": False,
        "review_inputs": body,
    }
    if persist:
        store.put("decision", stable(result), result)
    return result
