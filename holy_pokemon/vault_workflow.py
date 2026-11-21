"""Owner-reported custody and receipt workflow. All external actions remain manual."""

from __future__ import annotations
from datetime import date
from decimal import Decimal as D
from .store import stable, now
from .vault_engine import (
    STATUS_SEQUENCE,
    transition,
    withdrawal_quote,
    psa_consignment_net,
    partner_offer_net,
    reconcile_payout,
)
from .strategy_engine import money

# Application bookkeeping labels; no remote operation is performed.
STATUS_SEQUENCE["vaulted"].add("transferred")
STATUS_SEQUENCE["held"].add("transferred")
STATUS_SEQUENCE["consigned"].add("unsold")
STATUS_SEQUENCE["unsold"] = {"relisted", "vaulted"}
STATUS_SEQUENCE["transferred"] = set()


def collection(store):
    out = []
    for h in store.rows("holding"):
        events = [e for e in store.rows("vault_event") if e["holding_id"] == h["id"]]
        current = events[-1]["to"] if events else h["state"]
        payouts = [p for p in store.rows("payout") if p["holding_id"] == h["id"]]
        from .inventory import InventoryLedger

        ledger = InventoryLedger(store.path)
        try:
            grading_history = ledger.history(h["id"])
            financials = ledger.financials(h["id"])
            additional_cash = financials["cash_spent"]
        finally:
            ledger.close()
        out.append(
            {
                **h,
                "grading_history": grading_history,
                "latest_observed_grade": financials["latest_grade"],
                "additional_recorded_cash_spent": additional_cash,
                "current_state": current,
                "history": events,
                "payouts": payouts,
                "realized_cash": str(
                    sum((D(p["actual_payout"]) for p in payouts), D(0))
                )
                if payouts
                else None,
                "unpaid": current in ("sold_unpaid", "sold_paid", "payout_pending")
                and not payouts,
            }
        )
    return out


def record_transition(store, body):
    h = next((h for h in collection(store) if h["id"] == body["holding_id"]), None)
    if not h:
        raise ValueError("Unknown holding")
    if not body.get("source_ref") or not body.get("event_at"):
        raise ValueError("Dated status evidence required")
    event = transition(
        h["current_state"],
        body["to"],
        user_confirmed=body.get("user_confirmed") is True,
    )
    event.update(
        holding_id=h["id"],
        source_ref=body["source_ref"],
        event_at=body["event_at"],
        recorded_at=now(),
    )
    store.put(
        "vault_event",
        stable(h["id"], body["to"], body["event_at"], body["source_ref"]),
        event,
    )
    return event


def record_payout(store, body):
    h = store.get("holding", body["holding_id"])
    if not h:
        raise ValueError("Unknown holding")
    required = (
        "receipt_ref",
        "listing_id",
        "paid_at",
        "gross",
        "psa_fee",
        "actual_payout",
    )
    if (
        any(body.get(k) in (None, "") for k in required)
        or body.get("receipt_verified") is not True
    ):
        raise ValueError("Verified receipt, listing, date and amounts required")
    if h.get("ebay_item_id") and h["ebay_item_id"] != body["listing_id"]:
        raise ValueError("Listing does not match owned card")
    if any(
        p["receipt_ref"] == body["receipt_ref"] or p["listing_id"] == body["listing_id"]
        for p in store.rows("payout")
    ):
        raise ValueError(
            "Receipt/listing already reconciled; combined receipts require explicit per-card allocation"
        )
    for k in ("gross", "psa_fee", "actual_payout"):
        money(body[k])
    result = reconcile_payout(
        gross=body["gross"],
        psa_fee=body["psa_fee"],
        actual_payout=body["actual_payout"],
        card_id=h["id"],
        payout_reference=body["receipt_ref"],
    )
    store.put("payout", stable(body["receipt_ref"]), {**body, "reconciliation": result})
    return result


def compare_exits(body):
    asof = date.fromisoformat(body["asof"])
    basis = money(body.get("basis"), required=False)
    value = money(body.get("sale_price"), required=False)
    vaulted = body.get("vaulted_at")
    days = (asof - date.fromisoformat(vaulted)).days if vaulted else None
    if days is not None and days < 0:
        raise ValueError("Vault date is after quote")
    withdraw = withdrawal_quote(
        asof=asof,
        declared_usd=body.get("declared_value") or value or "0",
        item_count=1,
        recently_vaulted_count=1 if days is not None and days < 90 else 0,
        pre_effective_quote=body.get("shipping_quote"),
    )
    if days is None:
        withdraw = {
            "total": None,
            "reason": "Initial vault date required for early withdrawal determination",
        }
    consignment = (
        psa_consignment_net(value, fee_pct=body.get("psa_fee_pct"))
        if value is not None
        else {"net": None, "reason": "Sale estimate required"}
    )
    offer = partner_offer_net(
        body.get("offer_amount") or "0",
        actual_active_offer=body.get("offer_amount") not in (None, "")
        and bool(body.get("offer_evidence"))
        and bool(body.get("offer_expires"))
        and date.fromisoformat(body["offer_expires"]) >= asof,
        card_listed=body.get("card_listed") is True,
    )
    tax = money(body.get("tax"), required=False)

    def own_net(regrade=False):
        fields = ["own_fee_pct", "sale_shipping", "contingency"] + (
            ["grading", "grading_shipping", "insurance", "upcharge"] if regrade else []
        )
        vals = {k: money(body.get(k), required=False) for k in fields}
        exit_value = (
            money(body.get("regrade_exit"), required=False) if regrade else value
        )
        if (
            exit_value is None
            or withdraw.get("total") is None
            or tax is None
            or any(v is None for v in vals.values())
        ):
            return None
        if vals["own_fee_pct"] > 100:
            raise ValueError("Invalid own sale fee")
        return (
            exit_value * (1 - vals["own_fee_pct"] / 100)
            - sum(v for k, v in vals.items() if k != "own_fee_pct")
            - D(withdraw["total"])
            - tax
        )

    initial_costs = [
        money(body.get(k), required=False)
        for k in ("grading", "grading_shipping", "insurance", "upcharge")
    ]
    graded_exit = money(body.get("regrade_exit"), required=False)
    graded_consignment = (
        psa_consignment_net(graded_exit, fee_pct=body.get("psa_fee_pct"))
        if graded_exit is not None
        else {"net": None}
    )
    grade_to_vault = (
        D(graded_consignment["net"]) - sum(initial_costs) - tax
        if graded_consignment.get("net") is not None
        and tax is not None
        and all(v is not None for v in initial_costs)
        else None
    )
    transfer_amount = money(body.get("transfer_amount"), required=False)
    transfer_fee = money(body.get("transfer_fee"), required=False)
    transfer_net = (
        transfer_amount - transfer_fee - tax
        if transfer_amount is not None
        and transfer_fee is not None
        and tax is not None
        and body.get("transfer_evidence")
        else None
    )
    values = {
        "psa_auction": consignment.get("net"),
        "psa_bin": consignment.get("net"),
        "partner_offer": offer.get("net"),
        "withdraw_self_sell": own_net(),
        "withdraw_regrade": own_net(True),
        "hold": None,
        "vault_to_vault": transfer_net,
        "ship_to_owner": -D(withdraw["total"])
        if withdraw.get("total") is not None
        else None,
        "grade_to_vault": grade_to_vault,
    }
    rows = []
    baseline = D(consignment["net"]) if consignment.get("net") is not None else None
    for route, net in values.items():
        n = D(str(net)) if net is not None else None
        profit = (
            n - basis
            if n is not None
            and basis is not None
            and route not in ("ship_to_owner", "hold")
            else None
        )
        rows.append(
            {
                "route": route,
                "net_proceeds": str(n) if n is not None else None,
                "profit_if_sold": str(profit) if profit is not None else None,
                "incremental_vs_vault_sale": str(n - baseline)
                if n is not None
                and baseline is not None
                and route not in ("ship_to_owner", "hold")
                else None,
                "realized": False,
                "paper_value": str(value)
                if route == "hold" and value is not None
                else None,
                "route_kind": "COST_ONLY"
                if route == "ship_to_owner"
                else "HOLD_NO_CASH"
                if route == "hold"
                else "HYPOTHETICAL_EXIT",
                "external_action": "MANUAL_ONLY",
            }
        )
    return {
        "routes": rows,
        "withdrawal": withdraw,
        "consignment": consignment,
        "offer": offer,
        "vault_age_days": days,
        "tax_status": "MANUAL_QUOTE" if tax is not None else "UNKNOWN",
        "source_checked": "2026-10-28",
        "source": "https://www.psacard.com/info/psa-vault",
        "quote_warning": "Actual account quote controls; transfer proceeds require external payment evidence and are not guaranteed by PSA.",
    }


def record_grading_event(store, body):
    """Append an observed result and optional independently paid fee to the same copy."""
    from .inventory import InventoryLedger
    from .inventory import validate_grade

    holding = store.get("holding", body["holding_id"])
    if not holding:
        raise ValueError("Unknown owned physical copy")
    validate_grade(body.get("grader"), body.get("grade"))
    for key in ("event_id", "event_at", "source_ref"):
        if not body.get(key):
            raise ValueError("Unique event, actual date and grading evidence required")
    if body.get("outcome_verified") is not True:
        raise ValueError("Confirm actual observed grading result")
    ledger = InventoryLedger(store.path)
    try:
        exists = ledger.connection.execute(
            "SELECT 1 FROM specimen WHERE specimen_id=?", (holding["id"],)
        ).fetchone()
        if not exists:
            ledger.add_specimen(
                holding["id"],
                holding.get("name") or holding["item_id"],
                holding["source_url"],
                grader=holding.get("grader"),
                grade=holding.get("current_grade"),
                cert=holding.get("cert"),
            )
        if ledger.connection.execute(
            "SELECT 1 FROM event WHERE event_id=?", (body["event_id"],)
        ).fetchone():
            raise ValueError("Grading event already recorded")
        fee = money(body.get("paid_fee"), required=False)
        if fee is not None and body.get("fee_payment_verified") is not True:
            raise ValueError("Paid fee requires actual payment confirmation")
        ledger.grading_attempt(
            body["event_id"],
            holding["id"],
            body["source_ref"],
            event_at=body["event_at"],
            grader=body["grader"],
            grade=body["grade"],
            paid_fee=fee,
            notes=body.get("notes"),
        )
        return {
            "history": ledger.history(holding["id"]),
            "financials": ledger.financials(holding["id"]),
            "same_physical_copy": True,
        }
    finally:
        ledger.close()
