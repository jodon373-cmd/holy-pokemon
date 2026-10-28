"""Legacy CGC 9/9.5 fallback-first research. No upgrade odds are assumed."""
from datetime import date, timedelta
from decimal import Decimal, ROUND_DOWN
from statistics import median
from .strategy_common import D, physical_key, export_csv
from .research import deduplicate_sales, latest_listings


def administrative_reholder_grade(row):
    if row.get('slab_generation')=='legacy_blue' and row.get('slab_generation_confirmed') and row['grader']=='CGC' and row['grade']=='9.5' and row.get('grade_designation')=='gem_mint':
        return '10'
    return None


def sold_benchmark(candidate,sales,grader,grade,asof,slab_generation=None,designation=None):
    eligible=[]
    for s in deduplicate_sales(sales):
        if physical_key(s)!=physical_key(candidate) or s['grader']!=grader or s['grade']!=grade: continue
        if s.get('dataset','real')!='real' or s['verification_status']!='verified' or not s['price_confirmed'] or not s.get('source_url'): continue
        if s['price_basis']!='item_only' or not 0<=(asof-date.fromisoformat(s['sold_at'])).days<90 or D(s['price'])<=0: continue
        if grader=='CGC' and (s.get('slab_generation')!=slab_generation or s.get('grade_designation')!=designation): continue
        eligible.append(s)
    values=sorted(D(s['price']) for s in eligible)
    dates={s['sold_at'] for s in eligible}
    periods={int((asof-date.fromisoformat(s['sold_at'])).days)//30 for s in eligible}
    return dict(count=len(values),liquid=len(values)>=6 and len(dates)>=3 and len(periods)==3,
                median=median(values) if values else None,
                lower_quartile=values[(len(values)-1)//4] if values else None,
                links=sorted({s['source_url'] for s in eligible}))


def landed_cost(row):
    fields=('asking_price','shipping','purchase_tax_pct','buyer_premium_pct')
    if any(row.get(k) in ('',None) for k in fields): return None
    amount=D(row['asking_price'])
    return amount*(1+(D(row['purchase_tax_pct'])+D(row['buyer_premium_pct']))/100)+D(row['shipping'])


def break_even(success_profit,failure_profit):
    """Binary sensitivity threshold only, never an estimated success rate."""
    if success_profit is None or failure_profit is None: return None
    success_profit,failure_profit=D(success_profit),D(failure_profit)
    if failure_profit>=0: return D(0)
    if success_profit<=0 or success_profit<=failure_profit: return None
    return -failure_profit/(success_profit-failure_profit)


def compare_all_paths(row,benchmarks,costs):
    landed=landed_cost(row)
    fallback=benchmarks['original']['lower_quartile']
    branches=[('keep','original',D(0),False),
              ('intact_min10_rejected','original',None,False),
              ('intact_min10_success','psa10',None,True),
              ('crack_psa8','psa8',None,False),('crack_psa9','psa9',None,False),('crack_psa10','psa10',None,True)]
    if administrative_reholder_grade(row): branches.append(('cgc_administrative_reholder','cgc10',None,False))
    result=[]
    for path,target,extra,upgrade in branches:
        if costs:
            extra=(D(0) if path=='keep' else costs.reholder_fee+costs.reholder_shipping if path=='cgc_administrative_reholder'
                   else costs.grading_fee+costs.grading_shipping+costs.grading_insurance+(costs.psa10_upcharge if upgrade else D(0)))
        price=benchmarks[target]['lower_quartile']
        net=costs.proceeds(price) if costs and price is not None else None
        committed=landed+extra if landed is not None and costs else None
        profit=net-committed if net is not None and committed is not None else None
        ceiling=max(D(0),min(net-extra-25,(net-extra)/D('1.15'))) if net is not None and extra is not None and costs else None
        result.append(dict(listing_id=row['listing_id'],path=path,outcome=target,
                           sale_benchmark=price,benchmark_n=benchmarks[target]['count'],proceeds_after_exit_costs=net,
                           acquisition=landed,processing_cost=extra if costs else None,total_committed=committed,net_profit=profit,
                           maximum_all_in_acquisition=ceiling,failure_loss=max(D(0),-profit) if profit is not None else None,
                           probability_psa10=None,expected_roi=None,price_basis='verified_sold_lower_quartile',
                           source_urls=benchmarks[target]['links'],cost_quote_url=costs.source_url if costs else None))
    profits={r['path']:r['net_profit'] for r in result}
    for r in result:
        failure='intact_min10_rejected' if r['path'].startswith('intact') else 'crack_psa9'
        r['binary_break_even_psa10_sensitivity']=break_even(profits.get('intact_min10_success' if failure.startswith('intact') else 'crack_psa10'),profits.get(failure)) if 'success' in r['path'] or r['path']=='crack_psa10' else None
        r['sensitivity_label']='illustrative binary outcome mix, not observed probability'
    return result


def scan_cgc(listings,sales,asof,costs=None):
    watch=[];scenarios=[]
    for row in latest_listings(listings):
        if row['grader']!='CGC' or row['grade'] not in ('9','9.5') or row.get('slab_generation')!='legacy_blue': continue
        if not row.get('year') or not 1999<=int(row['year'])<=2007: continue
        benchmarks={'original':sold_benchmark(row,sales,'CGC',row['grade'],asof,'legacy_blue',row.get('grade_designation')),
                    'cgc10':sold_benchmark(row,sales,'CGC','10',asof,'current','gem_mint')}
        for grade in ('8','9','10'): benchmarks['psa'+grade]=sold_benchmark(row,sales,'PSA',grade,asof)
        paths=compare_all_paths(row,benchmarks,costs);scenarios+=paths
        keep=next(p for p in paths if p['path']=='keep')
        fallback=benchmarks['original'];landed=landed_cost(row)
        from .subgrades import screen
        inspection=screen(row)
        reasons=[]
        if inspection['screen_status']!='inspection_shortlist': reasons.append('inspection did not clear triage')
        if not row.get('return_policy'): reasons.append('return policy unknown')
        if row.get('status')!='active': reasons.append('listing availability unverified or inactive')
        if not row.get('url') or not 0<=(asof-date.fromisoformat(row['observed_at'])).days<=2: reasons.append('no fresh purchase URL')
        if not row.get('certification_number') or not row.get('cert_verified'): reasons.append('certificate unverified')
        if not row.get('slab_generation_confirmed'): reasons.append('label generation unconfirmed')
        if not row.get('front_photo_url') or not row.get('back_photo_url') or row.get('photo_quality')!='high': reasons.append('inspection photos incomplete')
        if any(row.get('subgrade_'+k) is None for k in ('centering','corners','edges','surface')) or not row.get('subgrades_verified'): reasons.append('subgrades incomplete or unverified')
        if not fallback['liquid']: reasons.append('fallback sales insufficient')
        if costs is None: reasons.append('dated cost quote required')
        if landed is None: reasons.append('acquisition costs incomplete')
        if keep['net_profit'] is None or keep['net_profit']<25 or landed is None or keep['net_profit']<landed*D('.15'): reasons.append('no-upgrade fallback does not support purchase')
        if row.get('buying_format')!='fixed': reasons.append('auction price is conditional')
        ceiling=keep['maximum_all_in_acquisition']
        max_price=(max(D(0),(ceiling-D(row['shipping']))/(1+(D(row['purchase_tax_pct'])+D(row['buyer_premium_pct']))/100)).quantize(D('.01'),rounding=ROUND_DOWN)
                   if ceiling is not None and landed is not None else None)
        watch.append({**row,'lane':'blue_cgc9' if row['grade']=='9' else 'blue_cgc95',
                      'physical_identity':'|'.join(physical_key(row)),'landed':landed,
                      'fallback_median':fallback['median'],'fallback_lower_quartile':fallback['lower_quartile'],
                      'fallback_sale_count':fallback['count'],'fallback_liquid':fallback['liquid'],
                      'max_all_in_acquisition':ceiling,'max_purchase_price':max_price,
                      'no_upgrade_profit':keep['net_profit'],'reholder_result_cgc_grade':administrative_reholder_grade(row),
                      'actionable':not reasons,'status':'opportunity' if not reasons else 'review',
                      'risk_reasons':reasons,'probability_psa10':None,'allocation_score':float(keep['net_profit']) if keep['net_profit'] is not None else None,
                      'required_reserve':costs.contingency+costs.outbound_shipping+costs.holding_cost+max(costs.grading_fee+costs.grading_shipping+costs.grading_insurance+costs.psa10_upcharge,costs.reholder_fee+costs.reholder_shipping) if costs else None,
                      'sold_comp_links':fallback['links']})
    watch.sort(key=lambda r:r['allocation_score'] if r['allocation_score'] is not None else -1e9,reverse=True)
    return watch,scenarios


def write_cgc_reports(output,watch,scenarios):
    from pathlib import Path
    output=Path(output)
    fields=('listing_id','url','grade','status','max_purchase_price','max_all_in_acquisition','no_upgrade_profit','risk_reasons')
    for grade,label in (('9','blue_cgc9'),('9.5','blue_cgc95')):
        group=[r for r in watch if r['grade']==grade]
        export_csv(output/(label+'_watchlist.csv'),group,fields)
        export_csv(output/(label+'_active_deals.csv'),[r for r in group if r['actionable']],fields)
        export_csv(output/(label+'_scenarios.csv'),[s for s in scenarios if s['listing_id'] in {r['listing_id'] for r in group}],('listing_id','path','net_profit','failure_loss'))
    export_csv(output/'cgc_crossover_scenarios.csv',scenarios,('listing_id','path','net_profit','failure_loss','probability_psa10'))
    export_csv(output/'cgc_blue_candidates.csv',watch,fields)


def main(argv=None):
    import argparse,json
    from pathlib import Path
    from contextlib import closing
    from .ingestion import connect,records
    from .strategy_common import CostQuote
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--database',required=True);p.add_argument('--asof',required=True)
    p.add_argument('--output',required=True);p.add_argument('--cost-quote');p.add_argument('--knowledge-at')
    a=p.parse_args(argv);asof=date.fromisoformat(a.asof)
    costs=CostQuote.parse(json.loads(Path(a.cost_quote).read_text()),asof) if a.cost_quote else None
    with closing(connect(a.database)) as db:
        watch,scenarios=scan_cgc(records(db,'listings',asof,a.knowledge_at),records(db,'sales',asof,a.knowledge_at),asof,costs)
    write_cgc_reports(a.output,watch,scenarios)

if __name__=='__main__': main()
