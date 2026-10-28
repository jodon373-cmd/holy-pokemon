"""PSA Vault workflow math: sourced dated fees, no account actions.

Source PSA info/psa-vault retrieved Oct 28 2026. No undocumented PSA Vault API.
"""
from __future__ import annotations
from datetime import date
from decimal import Decimal as D
from typing import Any

SCHEDULE_EFFECTIVE = date(2026,10,29)
SOURCE = "https://www.psacard.com/info/psa-vault"
STATUS_SEQUENCE = {
    "lead": {"acquired_pending","passed"},
    "acquired_pending": {"vaulted","owner_possession"},
    "vaulted": {"consigned","withdraw_requested","partner_offer_pending","held"},
    "held": {"consigned","withdraw_requested","partner_offer_pending"},
    "consigned": {"listed_auction","listed_bin","relisted","sold_unpaid"},
    "listed_auction": {"sold_unpaid","relisted"},
    "listed_bin": {"sold_unpaid","relisted"},
    "relisted": {"listed_auction","listed_bin"},
    "sold_unpaid": {"sold_paid","relisted"},
    "sold_paid": {"payout_pending","paid_out"},
    "payout_pending": {"paid_out"},
    "partner_offer_pending": {"sold_paid","vaulted"},
    "withdraw_requested": {"withdrawn"},
    "withdrawn": {"owner_possession","submitted_for_grading"},
    "owner_possession": {"submitted_for_grading","consigned","held"},
    "submitted_for_grading": {"vaulted","owner_possession"},
    "paid_out": set(),
    "passed": set(),
}

def transition(previous: str, next_status: str, *, user_confirmed: bool) -> dict[str,Any]:
    if not user_confirmed:
        raise PermissionError("No automatic Vault transactions, transfers or status assertions")
    if next_status not in STATUS_SEQUENCE.get(previous, set()):
        raise ValueError(f"Not allowed: {previous} -> {next_status}")
    return {"from":previous,"to":next_status,"user_confirmed":True,
        "remote_action_executed":False}

def withdrawal_quote(*, asof:date, declared_usd: Any, item_count:int,
                     recently_vaulted_count:int=0, country:str="US",
                     pre_effective_quote:Any=None) -> dict[str,Any]:
    if item_count<=0 or recently_vaulted_count<0 or recently_vaulted_count>item_count:
        raise ValueError("Invalid card counts")
    value=D(str(declared_usd))
    if not value.is_finite() or value<0:
        raise ValueError("Invalid declared shipment value")
    early=D("4.99")*recently_vaulted_count
    if asof<SCHEDULE_EFFECTIVE:
        if pre_effective_quote is None:
            return {"total":None,"early":str(early),"shipping":None,
                "source":SOURCE,"reason":"Request actual pre-2026-10-29 quote; do not apply future pricing early"}
        shipping=D(str(pre_effective_quote))
    elif value < 500: shipping=D("19.99")
    elif value < 5000: shipping=D("24.99")
    elif value < 25000: shipping=D("42.99")
    elif value < 75000: shipping=D("57.99")
    elif value < 300000: shipping=D("139.99")
    else:
        return {"total":None,"early":str(early),"shipping":None,"source":SOURCE,
            "reason":"PSA custom shipping quote required for $300,000+ declaration"}
    if asof>=SCHEDULE_EFFECTIVE:
        shipping+=D("0.99")*max(0,item_count-10)
        if country.upper() in ("CA","CANADA"):shipping+=D("24.99")
        elif country.upper() not in ("US","USA"):shipping+=D("31.99")
    elif country.upper() not in ("US","USA"):
        return {"total":None,"early":str(early),"shipping":None,"source":SOURCE,
            "reason":"International pre-effective quote required"}
    return {"total":str(shipping+early),"shipping":str(shipping),
        "early":str(early),"source":SOURCE,"effective":str(asof>=SCHEDULE_EFFECTIVE),
        "declared_usd":str(value),"item_count":item_count}

def psa_consignment_net(sale_price:Any, *, fee_pct:Any=None, non_usd_fx_fee_pct:Any=0) -> dict[str,Any]:
    gross=D(str(sale_price))
    if gross<0:raise ValueError("Invalid sale")
    if fee_pct is None:
        if D("100")<=gross<D("500"):fee=D("13")
        else:
            return {"net":None,"reason":"Fee tier quote required; 13% only known $100-$499 example"}
    else:fee=D(str(fee_pct))
    fx=D(str(non_usd_fx_fee_pct))
    if fee<0 or fx<0 or fee+fx>=100:raise ValueError("Invalid fees")
    return {"net":str((gross*(1-(fee+fx)/100)).quantize(D(".01"))),
        "psa_fee":str((gross*fee/100).quantize(D(".01"))),
        "additional_ebay_fee":"0","fee_pct":str(fee),
        "source":"https://www.psacard.com/info/consignment-rates"}

def partner_offer_net(offer:Any, *, actual_active_offer:bool, card_listed:bool=False) -> dict[str,Any]:
    if not actual_active_offer or card_listed:
        return {"net":None,"reason":"Must be a real active offer; offer unavailable while listed on eBay"}
    price=D(str(offer))
    if price<0:raise ValueError("Invalid offer")
    return {"net":str(price.quantize(D(".01"))),"psa_offer_fee":"0",
        "source":"https://www.psacard.com/info/psa-partner-offers",
        "note":"Original grading/shipping costs still apply; user must accept externally"}

def reconcile_payout(*, gross:Any, psa_fee:Any, actual_payout:Any|None,
                     card_id:str, payout_reference:str|None=None) -> dict[str,Any]:
    projected=D(str(gross))-D(str(psa_fee))
    if actual_payout is None:
        return {"card_id":card_id,"status":"AWAITING_PAYOUT","estimated_net":str(projected),
            "realized_cash":None}
    paid=D(str(actual_payout))
    return {"card_id":card_id,"status":"RECONCILED" if paid==projected else "EXCEPTION",
        "estimated_net":str(projected),"realized_cash":str(paid),
        "difference":str(paid-projected),"payout_reference":payout_reference,
        "actual_payout_verified":bool(payout_reference)}
