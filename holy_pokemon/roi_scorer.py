"""Conditional, costed research scenarios. Scores are not expected returns."""
from dataclasses import dataclass, replace
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from typing import Any, Mapping
from .comp_index import CompIndex
from .title_parser import parse_title

D = Decimal
CENT = D('0.01')

@dataclass(frozen=True)
class FeeSchedule:
    seller_fee_pct: Decimal = D('15')
    selling_fixed: Decimal = D('0.40')
    grading_fee: Decimal = D('20')
    grading_shipping: Decimal = D('35')
    grading_insurance: Decimal = D('0')  # Included in modeled round trip, not a quote.
    supplies: Decimal = D('5')
    upcharge: Decimal = D('0')
    outbound_shipping: Decimal = D('10')
    purchase_tax_pct: Decimal = D('8')

    def __post_init__(self):
        for name, value in vars(self).items():
            value = D(str(value))
            if not value.is_finite() or value < 0:
                raise ValueError('Fees must be finite and nonnegative')
            object.__setattr__(self, name, value)
        if self.seller_fee_pct >= 100 or self.purchase_tax_pct > 100:
            raise ValueError('Invalid fee/tax percentage')


def _q(value):
    return str(value.quantize(CENT)) if value is not None else None


def _money(value):
    if value is None or value == '':
        return None
    try:
        n = D(str(value))
        return n if n.is_finite() and n >= 0 else None
    except (InvalidOperation, ValueError):
        return None


def listing_ask(listing):
    """Use a BIN price when available, otherwise the observed USD auction bid."""
    ask = listing.get('asking_price', listing.get('ask'))
    if ask not in (None, '') or 'AUCTION' not in (listing.get('buying_options') or []):
        return ask
    bid = listing.get('current_bid')
    if isinstance(bid, Mapping):
        return bid.get('value') if bid.get('currency') == 'USD' else None
    return bid


def score_opportunity(*, listing: Mapping[str, Any], card: str, number: str,
                      comp_index: CompIndex, target_grader='CGC',
                      target_grade_bucket='GEM_MINT_10', set_name=None,
                      edition=None, centering_result=None, fees=None):
    target_grader = target_grader.upper()
    automatic_fees=fees is None
    fees = fees or FeeSchedule(grading_fee=D('39.99') if target_grader == 'PSA' else D('20'))
    parsed = parse_title(str(listing.get('title') or ''), expected_language=listing.get('expected_language'))
    result = dict(listing_id=listing.get('listing_id') or listing.get('id'), url=listing.get('url'),
                  title=parsed.raw_title, card=card, number=number, parsed=parsed.to_dict(),
                  target_route=f'{target_grader}_{target_grade_bucket}',
                  landed_cost_usd=None, total_investment_usd=None,
                  target_comp=None, fallback_comp=None, conservative_net_profit_usd=None,
                  upside_net_profit_usd=None, downside_net_profit_usd=None,
                  roi_if_upgraded_pct=None, break_even_upgrade_rate=None, opportunity_score=0.0,
                  max_offer_usd=None, max_bid_ceiling=None, original_grade_fallback=None,
                  incremental_over_original=None, source_urls=[], warnings=[],
                  expected_profit=None, grade_probability=None, trade_approved=False,
                  evidence_status='REPORTED_SALES_NOT_PHOTO_OR_SETTLEMENT_VERIFIED',
                  scenario_kind='CONDITIONAL_SUCCESS_NOT_EXPECTED_RETURN',
                  costs_are_assumptions=True, fee_assumptions={k: str(v) for k,v in vars(fees).items()},
                  income_tax_included=False)
    if 'PRISTINE' in target_grade_bucket.upper():
        result['warnings'].append('PRISTINE_OUTLIER_ONLY')
        target_grade_bucket = 'GEM_MINT_10'
        result['target_route'] = f'{target_grader}_{target_grade_bucket}'
    def stop(status):
        return dict(result, status=status)
    if parsed.disqualified:
        return stop('DISQUALIFIED')
    availability = listing.get('availability') or []
    if listing.get('ended') is True or any(x.get('estimatedAvailabilityStatus') == 'OUT_OF_STOCK' for x in availability):
        return stop('UNAVAILABLE')
    if listing.get('currency', 'USD') != 'USD':
        return stop('UNSUPPORTED_CURRENCY')
    raw_ask = listing_ask(listing)
    ask = _money(raw_ask)
    if not parsed.grader or not parsed.grade:
        return stop('MISSING_ORIGINAL_GRADE')
    if parsed.grader == target_grader and (parsed.cgc_sub_tier or parsed.grade) == target_grade_bucket:
        return stop('ALREADY_TARGET_GRADE')
    listing_tax = listing.get('purchase_tax_pct')
    if automatic_fees and listing_tax not in (None, ''):
        tax_pct = _money(listing_tax)
        if tax_pct is None or tax_pct > 100:
            return stop('INVALID_COST')
        fees = replace(fees, purchase_tax_pct=tax_pct)
    premium_quote = listing.get('buyer_premium_pct')
    premium_pct = _money('0' if premium_quote in (None, '') else premium_quote)
    result['buyer_premium_is_assumption'] = premium_quote in (None, '')
    if premium_pct is None:
        return stop('INVALID_COST')
    purchase_multiplier = 1 + fees.purchase_tax_pct / 100
    premium_multiplier = 1 + premium_pct / 100
    result['fee_assumptions'] = {k: str(v) for k, v in vars(fees).items()}
    result['buyer_premium_pct'] = str(premium_pct)
    result['observed_price_basis'] = ('AUCTION_BID' if listing.get('asking_price', listing.get('ask')) in (None, '')
                                      else 'LISTING_ASK')
    shipping = _money(listing.get('shipping', listing.get('buyer_shipping')))
    if ask is None:
        return stop('INVALID_COST' if raw_ask not in (None,'') else 'SKIPPED_NO_ASKING_PRICE')
    if shipping is None:
        return stop('INVALID_COST' if listing.get('shipping', listing.get('buyer_shipping')) not in (None,'') else 'MISSING_SHIPPING_COST')
    landed = ((ask * premium_multiplier + shipping) * purchase_multiplier).quantize(CENT)
    grading = fees.grading_fee + fees.grading_shipping + fees.grading_insurance + fees.upcharge + fees.supplies
    steps = listing.get('route_steps')
    if steps:
        if not isinstance(steps, list) or any(not isinstance(s, Mapping) for s in steps):
            raise ValueError('route_steps must be a list of grader/fee objects')
        grading = D('0')
        for step in steps:
            # Every attempt, including failures, has its own full charged cost.
            amount = _money(step.get('grading_fee'))
            if amount is None:
                return stop('MISSING_ROUTE_STEP_COST')
            extras = [_money(step.get(k, getattr(fees, k))) for k in
                      ('grading_shipping', 'grading_insurance', 'supplies', 'upcharge')]
            if any(v is None for v in extras):
                return stop('MISSING_ROUTE_STEP_COST')
            grading += amount + sum(extras, D('0'))
    investment = landed + grading
    result.update(landed_cost_usd=_q(landed), total_investment_usd=_q(investment))
    edition = edition or parsed.edition
    if not card or not number or not set_name or edition == 'Unspecified':
        return stop('MISSING_EXACT_IDENTITY')
    # Explicit annotations outrank title proposals, but do not imply photo verification.
    finish = listing.get('finish') or parsed.finish
    if finish == 'Unspecified':
        return stop('MISSING_FINISH')
    common = dict(card=card, number=number, set_name=set_name, edition=edition,
                  finish=finish, language=listing.get('language') or parsed.language,
                  as_of=listing.get('as_of'))
    from .comp_index import _norm_text, _norm_number
    if ((parsed.card_number and _norm_number(parsed.card_number)!=_norm_number(number)) or
        (' '+_norm_text(card)+' ') not in (' '+_norm_text(parsed.raw_title)+' ') or
        parsed.language!=common['language'] or
        (parsed.finish!='Unspecified' and parsed.finish!=finish)):
        return stop('IDENTITY_TITLE_CONFLICT')
    target = comp_index.summarize(grader=target_grader, grade_bucket=target_grade_bucket, **common)
    if target is None:
        return stop('MISSING_TARGET_COMPS')
    if automatic_fees and target_grader=='CGC' and not steps:
        # Declared value uses the contemplated graded card, not the lower-grade purchase price.
        declared=_money(listing.get('declared_value_usd',target.p25_usd))
        if declared is None:
            return stop('MISSING_DECLARED_VALUE')
        tier,amount = ('Economy','20') if declared<=1000 else ('Standard','55') if declared<=3000 else ('Express','100') if declared<=10000 else ('WalkThrough','300') if declared<=100000 else ('Unlimited',str(D('300')+declared*D('.01')))
        revised=replace(fees,grading_fee=D(amount))
        grading+=revised.grading_fee-fees.grading_fee
        investment=landed+grading
        fees=revised
        result.update(total_investment_usd=_q(investment),grading_tier=tier,
            modeled_declared_value_usd=_q(declared),
            grading_fee_source_url='https://www.cgccards.com/submit/services-fees/cgc-grading/',
            fee_assumptions={k:str(v) for k,v in vars(fees).items()})
    result['target_comp'] = target.to_dict()
    fee_mult = 1 - fees.seller_fee_pct / 100
    def profit(exit_price):
        return exit_price * fee_mult - fees.selling_fixed - fees.outbound_shipping - investment
    conservative = profit(target.p25_usd)
    result.update(conservative_net_profit_usd=_q(conservative), upside_net_profit_usd=_q(profit(target.median_usd)),
                  roi_if_upgraded_pct=_q(conservative / investment * 100) if investment else None)
    # Rejection preserves the source holder only for explicitly selected intact routes.
    # Never assume the original PSA9 value is a CGC9 resale value after cracking.
    if listing.get('failure_mode') == 'intact_rejected' and parsed.grader and parsed.grade:
        fallback = comp_index.summarize(grader=parsed.grader, grade_bucket=parsed.cgc_sub_tier or parsed.grade, **common)
        if fallback:
            loss = profit(fallback.p25_usd)
            result.update(fallback_comp=fallback.to_dict(), downside_net_profit_usd=_q(loss))
            if loss >= 0:
                result['break_even_upgrade_rate'] = '0.0000'
            elif conservative > 0:
                result['break_even_upgrade_rate'] = str((-loss/(conservative-loss)).quantize(D('0.0001')))
    # Transparent screening heuristic; no geometry bonus for unaccepted proposals.
    if conservative > 0:
        result['opportunity_score'] = round(min(100, min(60,float(conservative/investment*100)*.6)
                                               + min(30,target.count*5) + parsed.confidence*10),1)
    _fredy_economics(result, listing, parsed, comp_index, common, target, fees,
                     ask, shipping, landed, grading, investment, target_grader, premium_multiplier)
    if result['financial_gate']=='OVER_MAX_OFFER':
        result['opportunity_score']=0.0
    elif result['financial_gate']!='WITHIN_MODELED_CEILING':
        result['opportunity_score']=min(49.0,result['opportunity_score'])
    return stop('SCORED_LEAD')


def _minimum_success_rate(success, failure, hurdle):
    """Two-outcome sensitivity hurdle. This is a required rate, never a prediction."""
    if hurdle is None:
        return None
    if failure >= hurdle:
        return '0.0000'
    if success < hurdle or success <= failure:
        return None
    return str(((hurdle - failure) / (success - failure)).quantize(D('0.0001')))


def _fredy_economics(result, listing, parsed, idx, common, target, fees,
                     ask, shipping, landed, grading, investment, target_grader, premium_multiplier):
    """Fredy rules as explicit, costed scenarios; no selected-cohort success probabilities."""
    from .fredy_business import operating_rules
    result['fredy_rule_ids'] = [r['id'] for r in operating_rules()]
    result['route_steps'] = listing.get('route_steps') or [dict(
        grader=target_grader, grading_fee=_q(fees.grading_fee), full_cost_usd=_q(grading))]
    original = idx.summarize(grader=parsed.grader or '',
                            grade_bucket=parsed.cgc_sub_tier or parsed.grade or '', **common)
    pct = 1 - fees.seller_fee_pct / 100
    def net(price):
        return price * pct - fees.selling_fixed - fees.outbound_shipping
    original_net = net(original.p25_usd) if original else None
    result['original_grade_fallback'] = dict(
        comp=original.to_dict() if original else None,
        sale_net_usd=_q(original_net),
        net_profit_usd=_q(original_net-landed) if original_net is not None else None,
        basis='SELL_ORIGINAL_INTACT_TODAY_NOT_CRACKED_FAILURE')
    result['incremental_over_original'] = _q(net(target.p25_usd)-grading-original_net) if original_net is not None else None
    reserve = D('0')
    if parsed.grader == 'BGS' and parsed.grade == '9.5':
        import re
        result['warnings'].append('BGS_RISK')
        subgrades = dict(listing.get('subgrades') or {})
        for name in ('centering', 'corners', 'edges', 'surface'):
            m = re.search(r'\b'+name+r'\s*[:=-]?\s*(10|9\.5|9|8\.5|8)\b',
                          parsed.raw_title+' '+str(listing.get('description') or ''), re.I)
            if m:
                subgrades.setdefault(name, m.group(1))
        result['bgs_subgrades'] = subgrades
        if not all(_money(subgrades.get(k)) is not None and D('1') <= _money(subgrades[k]) <= 10
                   for k in ('centering', 'corners', 'edges', 'surface')):
            result['warnings'].append('UNVERIFIED_SUBGRADES')
        reserve = _money(listing.get('bgs_downside_reserve_usd'))
        reserve = max(D('150'), landed*D('.20')) if reserve is None else reserve
    result['downside_reserve_usd'] = _q(reserve)
    margin = _money(listing.get('required_margin_usd', '50'))
    roi = _money(listing.get('required_roi_pct', '20'))
    if margin is None or roi is None:
        raise ValueError('Nonnegative margin and ROI required')
    days = _money(listing.get('capital_lock_days', '90'))
    annual = _money(listing.get('annual_capital_cost_pct', '0'))
    if days is None or annual is None:
        raise ValueError('Invalid capital duration/cost')
    carry_rate = annual / 100 * days / 365
    capital_cost = investment * carry_rate
    if original_net is not None:
        result['incremental_over_original']=_q(net(target.p25_usd)-grading-capital_cost-original_net)
    proceeds = net(target.p25_usd)
    tax = 1 + fees.purchase_tax_pct/100
    # Evaluate financing at the proposed offer, rather than at the current ask.
    cost_multiplier = 1 + carry_rate
    allowed_cost = min(proceeds - margin - reserve, proceeds / (1 + roi / 100) - reserve)
    target_cap = ((allowed_cost / cost_multiplier - grading) / tax - shipping) / premium_multiplier
    fallback_cap = ((original_net-margin-reserve)/tax-shipping) / premium_multiplier if original_net is not None else None
    raw_ceiling = min(target_cap, fallback_cap) if fallback_cap is not None else target_cap
    ceiling = max(D('0'), raw_ceiling).quantize(CENT, rounding=ROUND_FLOOR)
    result.update(max_offer_usd=_q(ceiling), target_max_offer_usd=_q(max(D('0'), target_cap)),
                  original_fallback_max_offer_usd=_q(max(D('0'), fallback_cap)) if fallback_cap is not None else None,
                  required_margin_usd=_q(margin), required_roi_pct=_q(roi))
    auction = 'AUCTION' in (listing.get('buying_options') or [])
    result['max_bid_ceiling'] = _q(ceiling) if auction else None
    result['financial_gate'] = ('MISSING_ORIGINAL_FALLBACK' if original is None else
                                'OVER_MAX_OFFER' if raw_ceiling < 0 or ask > ceiling else
                                'BGS_SUBGRADE_REVIEW' if 'UNVERIFIED_SUBGRADES' in result['warnings'] else
                                'WITHIN_MODELED_CEILING')
    failures = []
    for grade in ('8', '8.5', '9', '9.5'):
        if target_grader == 'PSA' and '.' in grade:
            continue
        comp = idx.summarize(grader=target_grader, grade_bucket=grade, **common)
        if comp:
            failure_net = net(comp.p25_usd)
            target_net = proceeds - grading - capital_cost
            failure_net_after_grading = failure_net - grading - capital_cost
            failures.append(dict(
                grader=target_grader, grade=grade, comp=comp.to_dict(),
                net_profit_usd=_q(failure_net_after_grading - landed),
                minimum_upgrade_rate_to_break_even=_minimum_success_rate(
                    target_net, failure_net_after_grading, landed),
                minimum_upgrade_rate_to_beat_original=_minimum_success_rate(
                    target_net, failure_net_after_grading, original_net),
            ))
    result['failure_scenarios'] = failures
    if failures and listing.get('failure_mode') != 'intact_rejected':
        worst = min(failures, key=lambda scenario: D(scenario['net_profit_usd']))
        result['downside_net_profit_usd'] = worst['net_profit_usd']
        result['break_even_upgrade_rate'] = worst['minimum_upgrade_rate_to_break_even']
    result['maximum_capital_at_risk_usd'] = _q(investment)
    result['failure_scenarios_are_not_guaranteed_floor'] = True
    result['source_urls'] = list(dict.fromkeys([*target.source_urls,
        *(original.source_urls if original else []),
        *(u for f in failures for u in f['comp']['source_urls'])]))
    if target_grader == 'CGC':
        pristine = idx.summarize(grader='CGC', grade_bucket='PRISTINE_10', **common)
        result['pristine_upside_only'] = pristine.to_dict() if pristine else None
        result['pristine_score_bonus'] = 0
        result['pristine_exposure_cap_usd'] = _q(investment*D('.25'))
        if pristine and 'PRISTINE_OUTLIER_ONLY' not in result['warnings']:
            result['warnings'].append('PRISTINE_OUTLIER_ONLY')
    result['capital_lock_days'] = str(days)
    result['modeled_capital_cost_usd'] = _q(capital_cost)
    result['profit_after_capital_cost_usd'] = _q(proceeds-investment-capital_cost)
    result['aging_threshold_days'] = str(listing.get('aging_threshold_days', 90))
    channels = []
    for name in ('ebay', 'psa_vault', 'fanatics', 'direct_tcg'):
        config = (listing.get('exit_channels') or {}).get(name)
        if name == 'ebay' and config is None:
            config = dict(fee_pct=str(fees.seller_fee_pct), fixed=str(fees.selling_fixed),
                          shipping=str(fees.outbound_shipping), days_to_cash=None)
        if config is None:
            channels.append(dict(channel=name, status='NEEDS_CURRENT_FEE_QUOTE', net_proceeds_usd=None))
            continue
        values = [_money(config.get(k)) for k in ('fee_pct', 'fixed', 'shipping')]
        if any(v is None for v in values) or values[0] >= 100:
            raise ValueError('Channel needs valid fee_pct, fixed and shipping')
        sale_net = target.p25_usd*(1-values[0]/100)-values[1]-values[2]
        channels.append(dict(channel=name, status='MODELED_NOT_A_QUOTE',
            net_proceeds_usd=_q(sale_net), net_profit_usd=_q(sale_net-investment),
            days_to_cash=config.get('days_to_cash'), fee_source_url=config.get('source_url'),
            comp_count=target.count, latest_comp_date=target.latest_date))
    result['channel_comparison'] = channels
