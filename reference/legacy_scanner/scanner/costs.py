"""Explicit regrade scenarios, isolated from purchase rankings."""
from decimal import Decimal

def regrade_scenarios(acquisition, outcomes, grading_fee, grading_shipping,
                      insurance, seller_fee_pct=13, sale_shipping=12,
                      contingency=10):
    """Outcomes map labels (including unchanged and lower) to resale prices.

    No upgrade probability or expected profit is inferred. All inputs must be
    nonnegative finite values. Shipping is the full round trip to the grader.
    """
    def amount(v):
        d=Decimal(str(v))
        if not d.is_finite() or d<0: raise ValueError('Invalid scenario cost')
        return d
    if not {'unchanged','lower'} <= outcomes.keys():
        raise ValueError('Include unchanged and lower grade outcomes')
    fee=amount(seller_fee_pct)
    if fee>100: raise ValueError('Invalid selling fee')
    committed=sum((amount(v) for v in (acquisition,grading_fee,grading_shipping,insurance,contingency)),Decimal(0))
    return {label: {'total_cost':committed,'net_profit':amount(price)*(1-fee/100)-amount(sale_shipping)-committed}
            for label,price in outcomes.items()}
