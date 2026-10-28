"""SQLite inventory and source-event book with physical specimen identity.

Never convert creator paper value into realized revenue. No transactions executed.
"""
from __future__ import annotations
import json
import sqlite3
from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path

EVENTS = {
    "purchase_quote","purchase_confirmed","buyer_shipping","buyer_tax","grading_shipped",
    "grading_fee_paid","grading_result","received_from_grader","listed",
    "sale_reported","sale_payment_confirmed","selling_fee_paid","shipping_paid",
    "payout_received","held","regrade_resubmitted","vault_received","vault_withdrawn",
    "cost_adjustment","inspection_rejected",
}
CASH_SPEND = {"purchase_confirmed","buyer_shipping","buyer_tax",
    "grading_fee_paid","selling_fee_paid","shipping_paid"}
CASH_RECEIPT = {"payout_received"}
ESTIMATES = {"purchase_quote","sale_reported","listed","held"}

def dollars(amount):
    if amount is None:return None
    v=D(str(amount))
    if not v.is_finite() or v<0:raise ValueError("Nonnegative finite money required")
    return str(v.quantize(D(".01")))

class InventoryLedger:
    def __init__(self,path):
        self.path=str(Path(path))
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.connection=sqlite3.connect(self.path)
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

    def add_specimen(self,specimen_id,card_identity,source_ref,*,grader=None,grade=None,cert=None):
        if not specimen_id or not card_identity or not source_ref:
            raise ValueError("Missing specimen, card identity or evidence")
        self.connection.execute("INSERT INTO specimen(specimen_id,card_identity,source_ref,original_grader,original_grade,cert) VALUES(?,?,?,?,?,?)",
            (specimen_id,card_identity,source_ref,grader,grade,cert))
        self.connection.commit()

    def event(self,event_id,specimen_id,type,source_ref,*,amount=None,event_at=None,grader=None,grade=None,details=None):
        if type not in EVENTS:raise ValueError("Unknown business event")
        if not event_id or not source_ref:raise ValueError("Evidence and unique event id required")
        if type=="grading_result" and (not grader or not grade):
            raise ValueError("Grading outcome requires actual grader and grade")
        if type in CASH_SPEND|CASH_RECEIPT and amount is None:
            raise ValueError("Actual cash movement needs verified amount")
        if type=="payout_received" and not (details or {}).get("receipt_verified"):
            raise ValueError("Payout cannot become cash without receipt evidence")
        timestamp=event_at or datetime.now(timezone.utc).isoformat()
        self.connection.execute("""INSERT INTO event
            (event_id,specimen_id,type,amount,event_at,source_ref,grade_company,grade,details)
            VALUES(?,?,?,?,?,?,?,?,?)""",
            (event_id,specimen_id,type,dollars(amount),timestamp,source_ref,grader,grade,json.dumps(details or {})))
        self.connection.commit()

    def history(self,specimen_id):
        rows=self.connection.execute("""SELECT event_id,type,amount,event_at,source_ref,grade_company,grade,details
            FROM event WHERE specimen_id=? ORDER BY event_at,event_id""",(specimen_id,)).fetchall()
        return [{"id":a,"type":b,"amount":c,"at":d,"source":e,"grader":f,"grade":g,"details":json.loads(h)} for a,b,c,d,e,f,g,h in rows]

    def financials(self,specimen_id):
        events=self.history(specimen_id)
        cash_spent=sum((D(e["amount"]) for e in events if e["type"] in CASH_SPEND and e["amount"] is not None),D(0))
        cash_in=sum((D(e["amount"]) for e in events if e["type"] in CASH_RECEIPT and e["amount"] is not None),D(0))
        reported=sum(1 for e in events if e["type"]=="sale_reported")
        return {"specimen_id":specimen_id,"cash_spent":str(cash_spent),
            "receipt_verified_cash_in":str(cash_in),
            "actual_cash_net":str(cash_in-cash_spent),
            "sale_claims_not_proof_of_cash":reported,
            "grading_events":sum(1 for e in events if e["type"]=="grading_result"),
            "latest_grade":next(({"grader":e["grader"],"grade":e["grade"]}
                for e in reversed(events) if e["type"]=="grading_result"),None)}

    def close(self):self.connection.close()
