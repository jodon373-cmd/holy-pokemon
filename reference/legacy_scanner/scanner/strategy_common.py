"""Shared exact-variant, money, provenance and portfolio helpers."""
import csv
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from .ingestion import public_url, timestamp

D=lambda value: Decimal(str(value))
PHYSICAL_FIELDS=('year','set_name','card_number','card_name','edition','finish','language')

def physical_key(row):
    return tuple(str(row.get(k,'')).strip().lower() for k in PHYSICAL_FIELDS)

def slab_key(row):
    return (str(row['grader']).upper(),str(row['grade']),row.get('slab_generation','unknown'),row.get('grade_designation','unknown'))

def export_csv(path, rows, fields=()):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    columns=list(dict.fromkeys([*fields,*(key for row in rows for key in row)]))
    if not columns: columns=['status','data_requirement']
    with path.open('w',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=columns,lineterminator='\n')
        writer.writeheader()
        for row in rows:
            writer.writerow({k:json.dumps(v,sort_keys=True) if isinstance(v,(list,dict,tuple)) else v for k,v in row.items()})

@dataclass(frozen=True)
class CostQuote:
    seller_fee_pct: Decimal
    outbound_shipping: Decimal
    grading_fee: Decimal
    grading_shipping: Decimal
    grading_insurance: Decimal
    psa10_upcharge: Decimal
    reholder_fee: Decimal
    reholder_shipping: Decimal
    holding_cost: Decimal
    contingency: Decimal
    source_url: str
    observed_at: date

    @classmethod
    def parse(cls,row,asof):
        url=public_url(row['source_url'])
        observed=date.fromisoformat(row['observed_at'])
        if not 0<=(asof-observed).days<=30: raise ValueError('Cost quote is stale or future-dated')
        values={k:D(row[k]) for k in cls.__dataclass_fields__ if k not in ('source_url','observed_at')}
        if any(not v.is_finite() or v<0 for v in values.values()) or values['seller_fee_pct']>=100:
            raise ValueError('Invalid cost quote')
        return cls(**values,source_url=url,observed_at=observed)

    def proceeds(self,price):
        return D(price)*(1-self.seller_fee_pct/100)-self.outbound_shipping-self.holding_cost-self.contingency


def allocate_shared(rows,budget=2000,limit=5):
    """Single cap across all research lanes; no execution capabilities."""
    budget=D(budget)
    if not budget.is_finite() or not 0<=budget<=2000: raise ValueError('Shared budget must be 0..2000')
    chosen=[];spent=D(0);certs=set();links=set();identities=set()
    for row in sorted(rows,key=lambda r:float(r.get('allocation_score') or 0),reverse=True):
        if not row.get('actionable') or not row.get('url'): continue
        cert=str(row.get('certification_number') or '')
        link=row['url'].split('?')[0].rstrip('/')
        identity=row.get('physical_identity') or row.get('identity_key')
        # Unknown identifiers cannot bypass deduplication with a second source.
        if not identity or cert and cert in certs or link in links or identity in identities: continue
        total=D(row['landed'])+D(row.get('required_reserve',100))
        if not total.is_finite() or total<0: raise ValueError('Invalid portfolio commitment')
        if len(chosen)<min(limit,5) and spent+total<=budget:
            chosen.append({**row,'commitment':str(total.quantize(D('.01')))});spent+=total
            if cert: certs.add(cert)
            links.add(link);identities.add(identity)
    return chosen,spent
