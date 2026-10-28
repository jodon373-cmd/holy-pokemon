"""Read-only eBay Browse discovery; isolated from valuation and execution."""
import base64
from datetime import datetime,timezone,timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
import time
from urllib.parse import urlencode,urlparse
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError
from .ingestion import public_url,timestamp

class EbayError(RuntimeError): pass

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs): return None


def transport(method,url,headers,data=None):
    """Only official API host; never follow a credential-bearing redirect."""
    p=urlparse(url)
    if p.scheme!='https' or p.netloc!='api.ebay.com': raise EbayError('Unsupported API endpoint')
    if method not in ('GET','POST') or method=='POST' and p.path!='/identity/v1/oauth2/token':
        raise EbayError('Only token creation and read-only discovery requests allowed')
    from .ebay_network import context,failure,NetworkProblem
    from urllib.request import HTTPSHandler
    request=Request(url,data=data,headers=headers,method=method)
    try:
        with build_opener(NoRedirect,HTTPSHandler(context=context())).open(request,timeout=20) as response:
            return response.status,dict(response.headers),json.load(response)
    except HTTPError as exc:
        return exc.code,dict(exc.headers),{}  # never disclose response bodies/credentials
    except (OSError,__import__('urllib.error',fromlist=['URLError']).URLError) as exc:
        raise failure(exc) from None
    except (ValueError,UnicodeError):
        raise NetworkProblem('RESPONSE') from None


def credentials(path=None):
    if path:
        p=Path(path)
        if p.is_symlink() or stat.S_IMODE(p.stat().st_mode)&0o077:
            raise EbayError('Credential file must be private (chmod 600), not a symlink')
        values=json.loads(p.read_text())
        cid,secret=values.get('client_id'),values.get('client_secret')
    else:
        cid,secret=os.environ.get('EBAY_CLIENT_ID'),os.environ.get('EBAY_CLIENT_SECRET')
    if not cid or not secret: raise EbayError('Production credentials unavailable; account approval/setup required')
    return cid,secret


def discovery_row(item,retrieved):
    url=public_url(item['itemWebUrl'])
    if urlparse(url).hostname not in ('ebay.com','www.ebay.com'): raise EbayError('Unexpected listing link host')
    price=item.get('price') or {};currency=price.get('currency')
    options=item.get('shippingOptions') or []
    shipping=options[0].get('shippingCost',{}) if len(options)==1 else {}
    # An ambiguous selection or currency is not free shipping.
    ship=shipping.get('value') if shipping.get('currency')==currency else None
    images=[x['imageUrl'] for x in [item.get('image',{}),*(item.get('additionalImages') or [])] if x.get('imageUrl')]
    aspects={str(a.get('name','')).casefold():a.get('value') for a in item.get('localizedAspects',[]) if isinstance(a,dict)}
    certificate=aspects.get('certification number') or aspects.get('certification_number')
    auction='AUCTION' in item.get('buyingOptions',[])
    return dict(listing_id=item['itemId'],title=item.get('title',''),url=url,
                asking_price=price.get('value') if not auction or 'FIXED_PRICE' in item.get('buyingOptions',[]) else None,currency=currency,shipping=ship,
                shipping_options=options,buying_options=item.get('buyingOptions',[]),
                auction_deadline=item.get('itemEndDate'),bid_count=item.get('bidCount'),
                current_bid=item.get('currentBidPrice'),image_urls=images,
                source='ebay_browse',retrieved_at=retrieved,observed_at=retrieved[:10],
                dataset='real',evidence_kind='active_listing_discovery_only',
                exact_identity_verified=False,certification_number=certificate,grade=None,
                slab_generation='unknown',purchase_tax_pct=None,buyer_premium_pct=None,
                actionable=False,valuation_eligible=False,probability_psa10=None)


class EbayBrowse:
    def __init__(self,db,*,enabled=False,production_approved=False,client_id=None,client_secret=None,
                 request=transport,daily_limit=30,max_pages=3,sleep=time.sleep,now=None):
        if not 1<=daily_limit<=100 or not 1<=max_pages<=5: raise ValueError('Invalid request/page limit')
        self.db,self.enabled,self.approved=db,enabled,production_approved
        self.cid,self.secret=client_id,client_secret
        self.request,self.daily_limit,self.max_pages,self.sleep=request,daily_limit,max_pages,sleep
        self.now=now or (lambda:datetime.now(timezone.utc));self.token=None;self.expires=None
        db.execute('CREATE TABLE IF NOT EXISTS ebay_api_usage (requested_at TEXT,status INTEGER,cooldown_until TEXT)')
        db.execute('CREATE TABLE IF NOT EXISTS ebay_discovery_cache (cache_key TEXT PRIMARY KEY,retrieved_at TEXT,payload TEXT)')

    def _call(self,method,url,headers,data=None):
        now=self.now()
        used=self.db.execute('SELECT count(*) FROM ebay_api_usage WHERE substr(requested_at,1,10)=?',(now.date().isoformat(),)).fetchone()[0]
        cooldown=self.db.execute('SELECT max(cooldown_until) FROM ebay_api_usage').fetchone()[0]
        if used>=self.daily_limit: raise EbayError('Local daily request cap reached')
        if cooldown and timestamp(cooldown)>now: raise EbayError('eBay rate-limit cooldown remains active')
        self.sleep(1)
        try: status,headers,payload=self.request(method,url,headers,data)
        except Exception as exc:
            with self.db: self.db.execute('INSERT INTO ebay_api_usage VALUES (?,?,?)',(now.isoformat(),0,None))
            from .ebay_network import NetworkProblem
            if isinstance(exc,NetworkProblem):raise
            raise EbayError('eBay request failed; response and credentials omitted') from None
        until=None
        if status==429:
            retry=headers.get('Retry-After') or headers.get('retry-after')
            try: delay=max(1,int(retry))
            except (ValueError,TypeError): delay=3600
            until=(now+timedelta(seconds=delay)).isoformat()
        with self.db: self.db.execute('INSERT INTO ebay_api_usage VALUES (?,?,?)',(now.isoformat(),status,until))
        if status!=200: raise EbayError(f'eBay stopped: HTTP {status}; no automatic retry')
        return payload

    def _token(self):
        if not self.token or self.expires<=self.now()+timedelta(seconds=60):
            auth=base64.b64encode((self.cid+':'+self.secret).encode()).decode()
            result=self._call('POST','https://api.ebay.com/identity/v1/oauth2/token',
                              {'Authorization':'Basic '+auth,'Content-Type':'application/x-www-form-urlencoded'},
                              urlencode({'grant_type':'client_credentials','scope':'https://api.ebay.com/oauth/api_scope'}).encode())
            if not result.get('access_token') or int(result.get('expires_in',0))<=60: raise EbayError('Invalid token response')
            self.token=result['access_token'];self.expires=self.now()+timedelta(seconds=int(result['expires_in']))
        return self.token

    def search(self,query):
        if not self.enabled or not self.approved or not self.cid or not self.secret:
            raise EbayError('Live Browse requires explicit enablement, approved Production access and local credentials')
        if not query.strip() or len(query)>100: raise ValueError('Query must contain 1..100 characters')
        output=[];seen=set()
        for page in range(self.max_pages):
            url='https://api.ebay.com/buy/browse/v1/item_summary/search?'+urlencode({'q':query,'category_ids':'183454','limit':50,'offset':page*50})
            cache_key=hashlib.sha256((self.cid+url).encode()).hexdigest()
            cached=self.db.execute('SELECT retrieved_at,payload FROM ebay_discovery_cache WHERE cache_key=?',(cache_key,)).fetchone()
            # Expired cache is removed, never shown as a current listing.
            now=self.now()
            if cached and 0<=(now-timestamp(cached[0])).total_seconds()<5*3600:
                retrieved,rows=cached[0],json.loads(cached[1])
            else:
                with self.db: self.db.execute('DELETE FROM ebay_discovery_cache WHERE cache_key=?',(cache_key,))
                result=self._call('GET',url,{'Authorization':'Bearer '+self._token(),'X-EBAY-C-MARKETPLACE-ID':'EBAY_US'})
                retrieved=self.now().isoformat();items=result.get('itemSummaries',[])
                if not isinstance(items,list): raise EbayError('Invalid listing response')
                rows=[discovery_row(item,retrieved) for item in items]
                with self.db: self.db.execute('INSERT OR REPLACE INTO ebay_discovery_cache VALUES (?,?,?)',(cache_key,retrieved,json.dumps(rows)))
            for row in rows:
                if row['listing_id'] not in seen: output.append(row);seen.add(row['listing_id'])
            if len(rows)<50: break
        return output


def main(argv=None):
    import argparse
    from contextlib import closing
    from .ingestion import connect
    from .strategy_common import export_csv
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--query',action='append',default=[])
    p.add_argument('--database',default='outputs/ebay_discovery.sqlite')
    p.add_argument('--output',default='outputs/ebay_discovery.csv')
    p.add_argument('--credentials-file')
    p.add_argument('--live',action='store_true');p.add_argument('--production-approved',action='store_true')
    p.add_argument('--status',action='store_true');p.add_argument('--max-pages',type=int,default=1)
    a=p.parse_args(argv)
    if a.status:
        try: credentials(a.credentials_file);ready=True
        except (EbayError,FileNotFoundError): ready=False
        print(json.dumps({'credentials_available':ready,'live_requested':a.live,'production_approval_confirmed':a.production_approved,
                          'mode':'listing_discovery_only','pricing_integration':False,'buying_enabled':False}))
        return
    if not a.live or not a.production_approved: p.error('Live and approved Production access must be explicitly confirmed')
    if not a.query: p.error('At least one query required')
    try:
        cid,secret=credentials(a.credentials_file)
        Path(a.database).parent.mkdir(parents=True,exist_ok=True)
        with closing(connect(a.database)) as db:
            client=EbayBrowse(db,enabled=True,production_approved=True,client_id=cid,client_secret=secret,max_pages=a.max_pages)
            rows={}
            for query in a.query:
                for row in client.search(query): rows[row['listing_id']]=row
            export_csv(a.output,list(rows.values()),('listing_id','title','url','asking_price','shipping','currency','retrieved_at','valuation_eligible'))
        print(f'Discovery listings: {len(rows)}. Valuation/execution disabled.')
    except EbayError as exc: p.exit(1,str(exc)+'\n')

if __name__=='__main__': main()
