"""Source-traced PSA 9 -> CGC Gem Mint 10 *research* across Pokemon sets.

Never infer a same-card crossover probability from PSA/CGC population differences.
Never use Grade 9 blended guide values as real PSA9 sold transactions.
No network calls, bids, purchases or model promotion.
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parents[1] / "research" / "cross_set_gap_2026"
POP = ROOT / "populations_and_guide_references.csv"
SALES = ROOT / "dated_source_reported_sales.csv"
D = Decimal

def _rows(path):
    with Path(path).open(newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))

def _number(value):
    if value in ("", None):
        return None
    try:
        v = D(str(value))
    except (InvalidOperation, TypeError):
        return None
    return v if v.is_finite() and v >= 0 else None

def _median(values):
    return D(str(median(values))) if values else None

def _q(value):
    return str(value.quantize(D("0.01"))) if value is not None else None

def rank(populations=None, sales=None, *, fee_pct="13", grading="55",
         acquisition_cost_buffer="30", as_of="2026-10-29"):
    """Return transparent ranked research observations, NOT purchase recommendations.

    A hypothetical spread is given only when BOTH grade-specific, exact-edition
    dated sold cohorts exist. Separate guide values remain reference-only.
    """
    populations = _rows(POP) if populations is None else populations
    sales = _rows(SALES) if sales is None else sales
    fee = _number(fee_pct)
    grading_cost = _number(grading)
    buffer = _number(acquisition_cost_buffer)
    if fee is None or fee >= 100 or grading_cost is None or buffer is None:
        raise ValueError("Invalid monetary/fee parameters")
    groups = defaultdict(lambda: {"PSA_9": [], "CGC_GEM10": []})
    for s in sales:
        if not str(s.get("source_status", "")).startswith("PRICECHARTING_REPORTED_COMPLETED_SALE"):
            continue
        key=(s.get("set"),s.get("card"),str(s.get("card_number")),s.get("edition"))
        grade=None
        if s.get("grading_company")=="PSA" and s.get("grade_class")=="MINT_9":
            grade="PSA_9"
        elif s.get("grading_company")=="CGC" and s.get("grade_class")=="GEM_MINT_10":
            grade="CGC_GEM10"
        amount=_number(s.get("reported_price_usd"))
        date=s.get("reported_date","")
        if grade and amount is not None and amount>0 and len(date)==10 and date<=as_of:
            groups[key][grade].append((date,amount))
    result=[]
    for p in populations:
        key=(p.get("set"),p.get("card"),str(p.get("number")),p.get("edition"))
        cohorts=groups[key]
        psa=[v for _,v in cohorts["PSA_9"]]
        cgc=[v for _,v in cohorts["CGC_GEM10"]]
        psa_med=_median(psa)
        cgc_med=_median(cgc)
        cgc_lower_quartile=sorted(cgc)[(len(cgc)-1)//4] if cgc else None
        guide9=_number(p.get("grade9_blended_guide_usd_not_psa9_sold"))
        guide10=_number(p.get("cgc_gem10_guide_usd_not_sold"))
        psa_pop=int(p["psa_10_pop"])
        psa_total=int(p["psa_total"])
        cgc_pop=int(p["cgc_10_inclusive_pop"])
        cgc_total=int(p["cgc_total"])
        if min(psa_total,cgc_total)<=0:
            continue
        success_only = (cgc_lower_quartile*(1-fee/100)-psa_med-grading_cost-buffer
                        if cgc_lower_quartile is not None and psa_med is not None else None)
        # Monetary guide references are NOT PSA-specific completed sales.
        guide_reference_spread = (guide10*(1-fee/100)-guide9-grading_cost-buffer
                                  if guide10 is not None and guide9 is not None else None)
        reliability = ("HISTORICAL_SALES_SPREAD_RESEARCH_ONLY"
                       if len(psa)>=2 and len(cgc)>=3 else
                       "INSUFFICIENT_SAME_GRADE_SALES_DO_NOT_VALIDATE_TRADE")
        note = p.get("qualifiers") or ""
        result.append({
            "set":key[0],"card":key[1],"number":key[2],"edition":key[3],
            "tier":p.get("priority"),
            "psa_9_population":p.get("psa_9_pop") or None,
            "psa_10_pct":_q(D(100)*psa_pop/psa_total),
            "cgc_10_inclusive_pct":_q(D(100)*cgc_pop/cgc_total),
            "census_rate_ratio_descriptive":_q((D(cgc_pop)/cgc_total)/(D(psa_pop)/psa_total)) if psa_pop else None,
            "psa9_source_reported_sale_count":len(psa),
            "cgc_gem10_source_reported_sale_count":len(cgc),
            "psa9_source_reported_sale_median":_q(psa_med),
            "cgc10_source_reported_sale_median":_q(cgc_med),
            "cgc10_source_reported_sale_lower_quartile":_q(cgc_lower_quartile),
            "success_only_historical_sale_spread_net_assumptions":_q(success_only),
            "blended_grade9_guide":_q(guide9),
            "cgc10_guide":_q(guide10),
            "guide_only_spread_not_realized":_q(guide_reference_spread),
            "research_status":reliability,
            "no_calibrated_conversion_probability":True,
            "not_expected_profit":True,
            "cost_assumptions_usd":{"grading":_q(grading_cost),"additional_acquisition_buffer":_q(buffer),"selling_fee_pct":str(fee)},
            "not_current_active_listing":True,
            "purchase_approved":False,
            "population_url":p.get("population_url"),
            "source_price_url":p.get("price_guide_url"),
            "limitations":note,
        })
    result.sort(key=lambda x: (
        x["research_status"]=="HISTORICAL_SALES_SPREAD_RESEARCH_ONLY",
        _number(x["success_only_historical_sale_spread_net_assumptions"]) or D("-1000000"),
        _number(x["guide_only_spread_not_realized"]) or D("-1000000")
    ),reverse=True)
    return result

def main(argv=None):
    arg=argparse.ArgumentParser(description=__doc__)
    arg.add_argument("--top",type=int,default=25)
    arg.add_argument("--fee-pct",default="13")
    arg.add_argument("--grading",default="55")
    arg.add_argument("--acquisition-buffer",default="30")
    a=arg.parse_args(argv)
    if a.top < 1:
        arg.error("--top must be positive")
    data=rank(fee_pct=a.fee_pct,grading=a.grading,acquisition_cost_buffer=a.acquisition_buffer)
    print(json.dumps({
        "type":"CROSS_SET_GEM_GAP_EXPLORATORY_RESEARCH_NOT_PRODUCTION_BUY_SIGNAL",
        "generated_from":"pinned committed pricecharting populations and date-specific third-party reported sales",
        "no_actual_cross_grade_conversion_probability":True,
        "cgc10_pop_includes_pristine_or_uncertain_subclass":True,
        "grade9_guide_is_blended_not_psa9_sale":True,
        "ranked":data[:a.top]
    },indent=2))
if __name__=="__main__":
    main()
