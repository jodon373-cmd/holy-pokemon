"""Research-only, source-grounded Jungle PSA9 -> CGC10 upside explorer.

Reads committed historic sales, without live browsing, invented conversion rates
or purchasing. A big success spread is NOT an expected profit or buy approval.
"""
from __future__ import annotations
import argparse
import csv
import json
from collections import defaultdict
from decimal import Decimal
from pathlib import Path
from statistics import median

BASE = Path(__file__).resolve().parents[1] / "research" / "jungle_2026"
SOLD = BASE / "dated_reported_sold_comps.csv"
POPS = BASE / "holo_variant_population_and_reference_prices.csv"

def read_csv(path):
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def rank_candidates(sales=None, populations=None, *, fee_pct="13", grading_cost="55"):
    """Compare only same exact set/number/edition and grade, with source-traced rows.

    This is a success-only hypothetical. It deliberately does NOT use creator
    upgrade rates or population ratios as conversion probabilities. No trade
    recommendation is returned. Values do not include sales-tax, shipping, slab
    loss, upcharge, holding costs or liquidity.
    """
    sales = read_csv(SOLD) if sales is None else sales
    populations = read_csv(POPS) if populations is None else populations
    buckets = defaultdict(lambda: {"psa9": [], "cgc10": []})
    for s in sales:
        if s.get("verification") not in {
            "REPORTED_COMPLETED_SALE", "DIRECT_MARKETPLACE_SALE_PAGE",
            "PSA_CARDFACTS_AUCTION_PRICES_REALIZED"
        }:
            continue
        key=(s.get("card"), str(s.get("number")), s.get("edition"))
        if s.get("grade_class") == "PSA_9":
            bucket="psa9"
        elif s.get("grade_class") == "CGC_GEM_MINT_10":
            bucket="cgc10"
        else:
            continue
        try:
            val=Decimal(str(s["reported_usd"]))
        except (ValueError, TypeError, ArithmeticError):
            continue
        if val > 0 and val.is_finite():
            buckets[key][bucket].append(val)
    fee=Decimal(str(fee_pct))/100
    cost=Decimal(str(grading_cost))
    if not 0 <= fee < 1 or cost < 0:
        raise ValueError("Invalid fee or grading cost")
    candidates=[]
    for p in populations:
        key=(p.get("name"),str(p.get("card_number")),p.get("variant"))
        groups=buckets[key]
        if not groups["psa9"] or not groups["cgc10"]:
            continue
        # Decimal median preserves exact cents.
        ask=median(groups["psa9"])
        exits=sorted(groups["cgc10"])
        low=exits[(len(exits)-1)//4]  # conservative observed lower-quartile order statistic
        peak=exits[-1]
        win=low*(1-fee)-ask-cost
        high=peak*(1-fee)-ask-cost
        candidates.append({
            "card": key[0], "number":key[1], "edition":key[2],
            "psa9_sale_observations":len(groups["psa9"]),
            "cgc10_sale_observations":len(groups["cgc10"]),
            "psa9_observed_median_usd":str(ask),
            "cgc10_observed_low_quartile_usd":str(low),
            "cgc10_observed_max_usd":str(peak),
            "success_only_spread_after_assumed_fee_grading_usd":str(win.quantize(Decimal(".01"))),
            "success_only_spread_using_max_sale_usd":str(high.quantize(Decimal(".01"))),
            "psa10_population_ratio_pct":p.get("psa_10_rate_pct") or None,
            "cgc10_population_ratio_pct":p.get("cgc_gem10_rate_pct") or None,
            "populations_not_crossover_probabilities":True,
            "missing_costs":"acquisition tax, shipping, handling, upcharges, grade loss, time",
            "purchase_approved":False,
            "source":"research/jungle_2026/dated_reported_sold_comps.csv",
        })
    return sorted(candidates,key=lambda x:Decimal(x["success_only_spread_after_assumed_fee_grading_usd"]),reverse=True)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--fee-pct",default="13")
    p.add_argument("--grading-cost",default="55")
    p.add_argument("--top",type=int,default=25)
    args=p.parse_args(argv)
    if args.top<1: p.error("--top must be positive")
    rows=rank_candidates(fee_pct=args.fee_pct,grading_cost=args.grading_cost)
    print(json.dumps({
        "type":"HISTORICAL_SUCCESS_ONLY_RESEARCH_NOT_INVESTMENT_APPROVAL",
        "assumed_selling_fee_percent":args.fee_pct,
        "assumed_grading_cost_usd":args.grading_cost,
        "ranked_candidates":rows[:args.top],
        "not_live_listings":True,
        "no_inferred_upgrade_probabilities":True,
    },indent=2))
if __name__=="__main__":
    main()
