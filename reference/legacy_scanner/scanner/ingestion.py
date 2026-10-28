"""Auditable offline ingestion. Aggregate price points never become sales."""
from dataclasses import asdict
from datetime import date, datetime, timezone
from decimal import Decimal
import csv
import hashlib
import json
from pathlib import Path
import sqlite3
from urllib.parse import urlparse
from .model import Card, cash

KINDS = {'market_data_points', 'sales', 'listings', 'populations', 'checks'}
IDENTITY = ('set_name','card_number','card_name','edition','finish','language','grader','grade','year')

def timestamp(value):
    dt=datetime.fromisoformat(str(value).replace('Z','+00:00'))
    if dt.tzinfo is None: raise ValueError('Retrieval timestamp needs a timezone')
    return dt.astimezone(timezone.utc)

def public_url(value):
    value=str(value or '').strip()
    p=urlparse(value)
    if p.scheme!='https' or not p.netloc or p.username or p.password:
        raise ValueError('Public HTTPS provenance URL required')
    if any(token in (p.query.lower()) for token in ('key=', 'token=', 'secret=', 'authorization=')):
        raise ValueError('Credential-bearing provenance URL rejected')
    return value

def boolean(value):
    if str(value).lower() in ('true','1','yes'): return True
    if str(value).lower() in ('false','0','no'): return False
    raise ValueError('Explicit true/false required')

def count(value):
    if value in ('',None): return None
    n=int(value)
    if n<0: raise ValueError('Negative count')
    return n

def parse_record(kind, row):
    if kind not in KINDS: raise ValueError('Unknown record kind')
    c=Card.parse(row)
    if c.year is None: raise ValueError('Exact year required')
    dataset=row.get('dataset','real')
    if dataset not in ('real','mock'): raise ValueError('Unknown dataset')
    source=str(row.get('source','')).strip()
    if not source: raise ValueError('Source required')
    retrieved=timestamp(row['retrieved_at'])
    record={**{k:getattr(c,k) for k in IDENTITY},'identity_key':c.exact_key,'dataset':dataset,'source':source,
            'source_url':public_url(row['source_url']),'retrieved_at':retrieved.isoformat(),
            'evidence_method':str(row.get('evidence_method','manual_import')),
            'evidence_note':str(row.get('evidence_note',''))}
    for field in ('slab_generation','grade_designation','photo_quality','return_policy','title',
                  'front_photo_url','back_photo_url','surface_macro_url','inspection_source_url'):
        if row.get(field): record[field]=str(row[field])
    for field in ('slab_generation_confirmed','cert_verified','subgrades_verified','identity_verified'):
        if row.get(field) not in ('',None): record[field]=boolean(row[field])
    for field in ('centering','corners','edges','surface'):
        key='subgrade_'+field
        if row.get(key) not in ('',None):
            value=Decimal(row[key])
            if not value.is_finite() or not 1<=value<=10: raise ValueError('Invalid subgrade')
            record[key]=str(value)
    for field in ('front_lr','front_tb','back_lr','back_tb','measurement_error'):
        if row.get(field) not in ('',None):
            value=Decimal(row[field])
            if not value.is_finite() or not 0<=value<=100: raise ValueError('Invalid centering measurement')
            record[field]=str(value)
    for field in ('scratches','print_lines','whitening','corner_wear','dents','creases','stains','gloss_loss','trimming'):
        value=row.get('defect_'+field)
        if value:
            if value not in ('seen','not_visible','unknown'): raise ValueError('Invalid defect state')
            record['defect_'+field]=value
    def day(field): return date.fromisoformat(row[field])
    def money(field): return str(cash(row[field]))
    if kind=='market_data_points':
        snap=day('snapshot_date')
        window=int(row['sample_window_days'])
        if window<=0: raise ValueError('Positive sample window required')
        ck=row['count_kind']
        n=count(row.get('sale_count'))
        if ck not in ('exact','approx','unknown') or (ck=='unknown') != (n is None):
            raise ValueError('Count kind and sale count must agree')
        record.update(snapshot_date=str(snap),rolling_median=money('rolling_median'),sale_count=n,
                      count_kind=ck,sample_window_days=window,count_window_days=count(row.get('count_window_days')))
        natural=(c.exact_key,source,str(snap),window,row.get('price_basis'))
        observed=snap
    elif kind=='sales':
        sid=str(row['sale_id']).strip()
        if not sid: raise ValueError('Sale ID required')
        method=row['sale_type']
        if method not in ('auction','fixed','best_offer'): raise ValueError('Unknown sale type')
        status=row['verification_status']
        if status not in ('verified','reported','ambiguous'): raise ValueError('Unknown verification status')
        confirmed=boolean(row['price_confirmed'])
        if status=='verified' and not confirmed: raise ValueError('Verified sale requires confirmed transaction price')
        record.update(sale_id=sid,transaction_source=str(row.get('transaction_source') or source),sold_at=str(day('sold_at')),price=money('price'),sale_type=method,
                      price_confirmed=confirmed,verification_status=status,
                      certification_number=str(row.get('certification_number','')))
        natural=(source,sid);observed=day('sold_at')
    elif kind=='listings':
        lid=str(row['listing_id']).strip()
        if not lid: raise ValueError('Listing ID required')
        record.update(listing_id=lid,url=public_url(row['url']) if row.get('url') else '',observed_at=str(day('observed_at')),
                      asking_price=money('asking_price'),status=row['status'],buying_format=row['buying_format'],
                      certification_number=str(row.get('certification_number','')),
                      auction_deadline=str(row.get('auction_deadline','')))
        if not record['url'] and record['status']!='unknown': raise ValueError('Live listing needs purchase URL')
        if record['status'] not in ('active','sold','ended','unknown'): raise ValueError('Unknown listing status')
        if record['buying_format'] not in ('fixed','auction'): raise ValueError('Unknown buying format')
        for field in ('shipping','purchase_tax_pct','buyer_premium_pct'):
            record[field]=money(field) if row.get(field) not in ('',None) else None
        if record['auction_deadline']: timestamp(record['auction_deadline'])
        natural=(source,lid,record['observed_at'],record['retrieved_at']);observed=day('observed_at')
    elif kind=='populations':
        observed=day('asof')
        record.update(asof=str(observed),current_population=count(row['current_population']))
        if record['current_population'] is None: raise ValueError('Population required')
        natural=(c.exact_key,source,str(observed))
    else:
        # An independent check is an observation, not another sale.
        observed=day('checked_at')
        record.update(checked_at=str(observed),sale_id=str(row['sale_id']),sale_source=str(row['sale_source']),
                      independent_url=public_url(row['independent_url']),independent_price=money('independent_price'),
                      independent_sold_at=str(day('independent_sold_at')),independent_price_basis=row['independent_price_basis'],notes=str(row.get('notes','')))
        if day('independent_sold_at')>observed:
            raise ValueError('Independent sale occurs after check date')
        if urlparse(record['independent_url']).hostname.removeprefix('www.')==urlparse(record['source_url']).hostname.removeprefix('www.'):
            raise ValueError('Independent check must use a different domain')
        natural=(c.exact_key,record['sale_source'],record['sale_id'],record['independent_url'])
    if observed>retrieved.date(): raise ValueError('Observation occurs after retrieval')
    if kind in ('market_data_points','sales'):
        record['currency']=row['currency']
        record['price_basis']=row['price_basis']
        if row['currency']!='USD': raise ValueError('Only USD supported; no implicit FX conversion')
        if row['price_basis'] not in ('item_only','incl_buyer_premium'):
            raise ValueError('Explicit price basis required')
    record['record_id']=hashlib.sha256(json.dumps(natural).encode()).hexdigest()
    return record

def connect(path):
    db=sqlite3.connect(path)
    for table in KINDS:
        db.execute(f'CREATE TABLE IF NOT EXISTS {table} (record_id TEXT PRIMARY KEY, identity_key TEXT NOT NULL, source TEXT NOT NULL, observed_at TEXT NOT NULL, retrieved_at TEXT NOT NULL, dataset TEXT NOT NULL, payload TEXT NOT NULL)')
    db.execute('CREATE TABLE IF NOT EXISTS source_audit (audit_id INTEGER PRIMARY KEY, input_hash TEXT, input_file TEXT, row_number INTEGER, kind TEXT, status TEXT, reason TEXT, source TEXT, source_url TEXT, retrieved_at TEXT, record_id TEXT)')
    db.execute('CREATE TABLE IF NOT EXISTS raw_payloads (sha256 TEXT PRIMARY KEY, payload TEXT NOT NULL, retrieved_at TEXT NOT NULL)')
    columns={
        'market_data_points': {'snapshot_date':'TEXT','rolling_median':'TEXT','sale_count':'INTEGER','count_kind':'TEXT','sample_window_days':'INTEGER','count_window_days':'INTEGER','source_url':'TEXT','currency':'TEXT','price_basis':'TEXT'},
        'sales': {'sale_id':'TEXT','sold_at':'TEXT','price':'TEXT','source_url':'TEXT','verification_status':'TEXT','price_confirmed':'INTEGER','price_basis':'TEXT'},
        'listings': {'listing_id':'TEXT','url':'TEXT','status':'TEXT','asking_price':'TEXT','shipping':'TEXT','purchase_tax_pct':'TEXT','buyer_premium_pct':'TEXT'},
        'populations': {'asof':'TEXT','current_population':'INTEGER','source_url':'TEXT'},
        'checks': {'sale_id':'TEXT','sale_source':'TEXT','independent_url':'TEXT'}
    }
    for table, fields in columns.items():
        existing={r[1] for r in db.execute(f'PRAGMA table_info({table})')}
        for field, sql_type in fields.items():
            if field not in existing: db.execute(f'ALTER TABLE {table} ADD COLUMN {field} {sql_type}')
    return db

def ingest(db, path, kind, allow_mock=False):
    if kind not in KINDS: raise ValueError('Unknown record kind')
    raw=Path(path).read_bytes()
    digest=hashlib.sha256(raw).hexdigest()
    result={'accepted':0,'duplicate':0,'rejected':0}
    with Path(path).open(encoding='utf-8-sig',newline='') as f, db:
        reader=csv.DictReader(f,delimiter='\t' if Path(path).suffix.lower()=='.txt' else ',')
        for line,row in enumerate(reader,2):
            record=None
            try:
                record=parse_record(kind,row)
                if record['dataset']=='mock' and not allow_mock: raise ValueError('Mock evidence rejected in real mode')
                existing=db.execute(f'SELECT payload FROM {kind} WHERE record_id=?',(record['record_id'],)).fetchone()
                payload=json.dumps(record,sort_keys=True)
                if existing and existing[0]!=payload:
                    raise ValueError('Conflicting duplicate; existing observation preserved')
                status='duplicate' if existing else 'accepted'
                observed=next(record[k] for k in ('snapshot_date','sold_at','observed_at','asof','checked_at') if k in record)
                db.execute(f'INSERT OR IGNORE INTO {kind} (record_id,identity_key,source,observed_at,retrieved_at,dataset,payload) VALUES (?,?,?,?,?,?,?)',
                           (record['record_id'],record['identity_key'],record['source'],observed,record['retrieved_at'],record['dataset'],payload))
                fields={r[1] for r in db.execute(f'PRAGMA table_info({kind})')} - {'record_id','identity_key','source','observed_at','retrieved_at','dataset','payload'}
                for field in fields:
                    db.execute(f'UPDATE {kind} SET {field}=? WHERE record_id=?',(record.get(field),record['record_id']))
                reason=''
            except (ValueError,KeyError,TypeError) as exc:
                status='rejected';reason=str(exc)
            result[status]+=1
            # Audit only normalized provenance, never raw key-bearing URLs or arbitrary row text.
            db.execute('INSERT INTO source_audit(input_hash,input_file,row_number,kind,status,reason,source,source_url,retrieved_at,record_id) VALUES (?,?,?,?,?,?,?,?,?,?)',
                       (digest,Path(path).name,line,kind,status,reason,record['source'] if record else '',record['source_url'] if record else '',record['retrieved_at'] if record else '',record['record_id'] if record else ''))
    return result

def records(db, kind, asof, knowledge_at=None, dataset='real'):
    if kind not in KINDS: raise ValueError('Unknown record kind')
    cutoff=timestamp(knowledge_at) if knowledge_at else datetime.now(timezone.utc)
    return [json.loads(r[0]) for r in db.execute(f'SELECT payload FROM {kind} WHERE dataset=? AND observed_at<=?',(dataset,str(asof)))
            if timestamp(json.loads(r[0])['retrieved_at'])<=cutoff]
