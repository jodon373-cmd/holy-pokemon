"""SQLite inventory and source-event book with physical specimen identity.

Never convert creator paper value into realized revenue. No transactions executed.
"""

from __future__ import annotations
import json
import sqlite3
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path

EVENTS = {
    "purchase_quote",
    "purchase_confirmed",
    "buyer_shipping",
    "buyer_tax",
    "grading_shipped",
    "grading_fee_paid",
    "grading_result",
    "received_from_grader",
    "listed",
    "sale_reported",
    "sale_payment_confirmed",
    "selling_fee_paid",
    "shipping_paid",
    "payout_received",
    "held",
    "regrade_resubmitted",
    "vault_received",
    "vault_withdrawn",
    "cost_adjustment",
    "inspection_rejected",
}
CASH_SPEND = {
    "purchase_confirmed",
    "buyer_shipping",
    "buyer_tax",
    "grading_fee_paid",
    "selling_fee_paid",
    "shipping_paid",
}
CASH_RECEIPT = {"payout_received"}
ESTIMATES = {"purchase_quote", "sale_reported", "listed", "held"}


def dollars(amount):
    if amount is None:
        return None
    v = D(str(amount))
    if not v.is_finite() or v < 0:
        raise ValueError("Nonnegative finite money required")
    return str(v.quantize(D(".01")))


def validate_grade(grader, grade):
    if grader not in ("PSA", "CGC", "BGS", "SGC"):
        raise ValueError("Unsupported observed grading company")
    if grade == "Pristine 10" and grader == "CGC":
        return
    try:
        value = D(str(grade))
    except Exception:
        raise ValueError(
            "Numeric observed grade required; retain non-numeric outcomes separately"
        ) from None
    if (
        not value.is_finite()
        or not 1 <= value <= 10
        or value * 2 != int(value * 2)
        or grader == "PSA"
        and value != int(value)
    ):
        raise ValueError("Invalid observed grade; Pristine is never grade 11")


class InventoryLedger:
    def __init__(self, path):
        self.path = str(Path(path))
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.execute("PRAGMA foreign_keys=ON")
        self.connection.executescript("""
            CREATE TABLE IF NOT EXISTS specimen(
                specimen_id TEXT PRIMARY KEY, card_identity TEXT NOT NULL,
                source_ref TEXT NOT NULL, acquired_at TEXT,
                original_grader TEXT, original_grade TEXT, cert TEXT);
            CREATE TABLE IF NOT EXISTS event(
                event_id TEXT PRIMARY KEY,
                specimen_id TEXT NOT NULL REFERENCES specimen(specimen_id),
                type TEXT NOT NULL, amount TEXT,
                currency TEXT NOT NULL DEFAULT 'USD',
                event_at TEXT NOT NULL, source_ref TEXT NOT NULL,
                grade_company TEXT, grade TEXT, details TEXT NOT NULL DEFAULT '{}');
            CREATE INDEX IF NOT EXISTS idx_event_copy ON event(specimen_id,event_at);
        """)
        self.connection.commit()

    def add_specimen(
        self,
        specimen_id,
        card_identity,
        source_ref,
        *,
        grader=None,
        grade=None,
        cert=None,
    ):
        if not specimen_id or not card_identity or not source_ref:
            raise ValueError("Missing specimen, card identity or evidence")
        self.connection.execute(
            "INSERT INTO specimen(specimen_id,card_identity,source_ref,original_grader,original_grade,cert) VALUES(?,?,?,?,?,?)",
            (specimen_id, card_identity, source_ref, grader, grade, cert),
        )
        self.connection.commit()

    def event(
        self,
        event_id,
        specimen_id,
        type,
        source_ref,
        *,
        amount=None,
        event_at=None,
        grader=None,
        grade=None,
        details=None,
    ):
        if type not in EVENTS:
            raise ValueError("Unknown business event")
        if not event_id or not source_ref:
            raise ValueError("Evidence and unique event id required")
        if type == "grading_result" and (not grader or not grade):
            raise ValueError("Grading outcome requires actual grader and grade")
        if type in CASH_SPEND | CASH_RECEIPT and amount is None:
            raise ValueError("Actual cash movement needs verified amount")
        if type == "payout_received" and not (details or {}).get("receipt_verified"):
            raise ValueError("Payout cannot become cash without receipt evidence")
        if type == "grading_result":
            validate_grade(grader, grade)
        timestamp = event_at or datetime.now(timezone.utc).isoformat()
        self.connection.execute(
            """INSERT INTO event
            (event_id,specimen_id,type,amount,event_at,source_ref,grade_company,grade,details)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (
                event_id,
                specimen_id,
                type,
                dollars(amount),
                timestamp,
                source_ref,
                grader,
                grade,
                json.dumps(details or {}),
            ),
        )
        self.connection.commit()

    def grading_attempt(
        self,
        event_id,
        specimen_id,
        source_ref,
        *,
        event_at,
        grader,
        grade,
        paid_fee=None,
        notes=None,
    ):
        """Atomically append one result and its separately paid grading fee."""
        validate_grade(grader, grade)
        fee = dollars(paid_fee)
        result = (
            event_id,
            specimen_id,
            "grading_result",
            None,
            event_at,
            source_ref,
            grader,
            grade,
            json.dumps({"observed_outcome": True, "notes": notes}),
        )
        fee_row = (
            event_id + ":fee",
            specimen_id,
            "grading_fee_paid",
            fee,
            event_at,
            source_ref,
            None,
            None,
            json.dumps({"separate_paid_cash": True}),
        )
        try:
            with self.connection:
                sql = "INSERT INTO event(event_id,specimen_id,type,amount,event_at,source_ref,grade_company,grade,details) VALUES(?,?,?,?,?,?,?,?,?)"
                self.connection.execute(sql, result)
                if fee is not None:
                    self.connection.execute(sql, fee_row)
        except sqlite3.IntegrityError:
            raise ValueError(
                "Grading event ID conflict; attempt was not appended"
            ) from None

    def history(self, specimen_id):
        rows = self.connection.execute(
            """SELECT event_id,type,amount,event_at,source_ref,grade_company,grade,details
            FROM event WHERE specimen_id=? ORDER BY event_at,event_id""",
            (specimen_id,),
        ).fetchall()
        return [
            {
                "id": a,
                "type": b,
                "amount": c,
                "at": d,
                "source": e,
                "grader": f,
                "grade": g,
                "details": json.loads(h),
            }
            for a, b, c, d, e, f, g, h in rows
        ]

    def financials(self, specimen_id):
        events = self.history(specimen_id)
        cash_spent = sum(
            (
                D(e["amount"])
                for e in events
                if e["type"] in CASH_SPEND and e["amount"] is not None
            ),
            D(0),
        )
        cash_in = sum(
            (
                D(e["amount"])
                for e in events
                if e["type"] in CASH_RECEIPT and e["amount"] is not None
            ),
            D(0),
        )
        reported = sum(1 for e in events if e["type"] == "sale_reported")
        return {
            "specimen_id": specimen_id,
            "cash_spent": str(cash_spent),
            "receipt_verified_cash_in": str(cash_in),
            "actual_cash_net": str(cash_in - cash_spent),
            "sale_claims_not_proof_of_cash": reported,
            "grading_events": sum(1 for e in events if e["type"] == "grading_result"),
            "latest_grade": next(
                (
                    {"grader": e["grader"], "grade": e["grade"]}
                    for e in reversed(events)
                    if e["type"] == "grading_result"
                ),
                None,
            ),
        }

    def close(self):
        self.connection.close()

    def cash_cycle(self, specimen_id, *, as_of=None, aging_threshold_days=90):
        """Age, locked cash and paid repeat costs; reported sales are never settlement."""
        if aging_threshold_days < 1:
            raise ValueError('Positive aging threshold required')
        clock = as_of or datetime.now(timezone.utc)
        if isinstance(clock, str):
            clock = datetime.fromisoformat(clock.replace('Z', '+00:00'))
        if clock.tzinfo is None:
            clock = clock.replace(tzinfo=timezone.utc)
        history = self.history(specimen_id)
        dated = []
        for event in history:
            at = datetime.fromisoformat(event['at'].replace('Z','+00:00'))
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            if at <= clock:
                dated.append((at,event))
        dated.sort(key=lambda pair: pair[0])
        age = max(0,(clock-dated[0][0]).days) if dated else None
        events = [e for _,e in dated]
        spend = sum((D(e['amount']) for e in events if e['type'] in CASH_SPEND and e['amount'] is not None),D(0))
        received = sum((D(e['amount']) for e in events if e['type'] in CASH_RECEIPT and e['amount'] is not None),D(0))
        paid_grading = [e for e in events if e['type']=='grading_fee_paid' and e['amount'] is not None]
        settled = any(e['type']=='payout_received' for e in events)
        latest = events[-1]['type'] if events else 'NO_EVENTS'
        return dict(specimen_id=specimen_id, age_days=age, latest_event=latest,
            capital_locked_usd=str(max(D(0),spend-received)), settlement_received=settled,
            paid_grading_attempts=len(paid_grading),
            repeat_grading_cost_usd=str(sum((D(e['amount']) for e in paid_grading[1:]),D(0))),
            aging_threshold_days=aging_threshold_days,
            aging_warning=bool(age is not None and age>=aging_threshold_days and not settled),
            suggested_action='REVIEW_EXIT_CHANNELS' if age is not None and age>=aging_threshold_days and not settled else 'MONITOR',
            trade_approved=False)
