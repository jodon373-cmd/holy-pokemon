import json,sqlite3,tempfile,unittest
from datetime import datetime,timezone,timedelta
from pathlib import Path
from scanner.ebay_browse import EbayBrowse,EbayError,credentials,discovery_row,transport

class EbayBrowseTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.now=datetime(2026,10,23,tzinfo=timezone.utc);self.calls=[]
    def tearDown(self): self.db.close()
    def request(self,method,url,headers,data):
        self.calls.append((method,url,headers,data))
        if method=='POST': return 200,{},dict(access_token='unit-token',expires_in=7200)
        return 200,{},dict(itemSummaries=[dict(itemId='v1|123|0',title='Fixture card',itemWebUrl='https://www.ebay.com/itm/123',price={'value':'20','currency':'USD'},buyingOptions=['FIXED_PRICE'])])
    def client(self,**kwargs):
        return EbayBrowse(self.db,enabled=True,production_approved=True,client_id='test-id',client_secret='test-secret',request=self.request,sleep=lambda _:None,now=lambda:self.now,**kwargs)
    def test_disabled_without_explicit_access(self):
        with self.assertRaises(EbayError): EbayBrowse(self.db).search('Pokemon')
        self.assertFalse(self.calls)
    def test_minimum_scope_read_only_cache_and_no_valuation(self):
        client=self.client();rows=client.search('Pokemon PSA 8');client.search('Pokemon PSA 8')
        self.assertEqual(len(self.calls),2)
        self.assertIn(b'scope=https%3A%2F%2Fapi.ebay.com%2Foauth%2Fapi_scope',self.calls[0][3])
        self.assertIsNone(rows[0]['shipping']);self.assertFalse(rows[0]['actionable']);self.assertFalse(rows[0]['valuation_eligible'])
        cached=self.db.execute('SELECT payload FROM ebay_discovery_cache').fetchone()[0]
        for secret in ('unit-token','test-secret','test-id'): self.assertNotIn(secret,cached)
        self.assertTrue(all(c[0]=='GET' for c in self.calls[1:]))
    def test_stale_cache_refresh_and_dedupe(self):
        client=self.client();client.search('Pokemon');self.now+=timedelta(hours=6)
        rows=client.search('Pokemon');self.assertEqual(len(self.calls),4);self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['retrieved_at'],self.now.isoformat())
    def test_rate_limit_persists_and_never_retries(self):
        client=self.client();client._token()
        def limited(*args): self.calls.append(args);return 429,{'Retry-After':'120'},{}
        client.request=limited
        with self.assertRaises(EbayError): client.search('Pokemon')
        before=len(self.calls)
        with self.assertRaises(EbayError): client.search('Pokemon')
        self.assertEqual(len(self.calls),before)
        self.assertEqual(self.db.execute('SELECT count(*) FROM ebay_api_usage').fetchone()[0],2)
    def test_request_cap_counts_oauth(self):
        client=self.client(daily_limit=1)
        with self.assertRaises(EbayError): client.search('Pokemon')
        self.assertEqual(len(self.calls),1)
    def test_credentials_private_and_transport_host_locked(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'credentials.json';p.write_text(json.dumps(dict(client_id='id',client_secret='secret')));p.chmod(0o644)
            with self.assertRaises(EbayError): credentials(p)
            p.chmod(0o600);self.assertEqual(credentials(p),('id','secret'))
        with self.assertRaises(EbayError): transport('GET','https://example.org/',{})
    def test_multiple_shipping_options_stay_unknown(self):
        row=discovery_row(dict(itemId='x',itemWebUrl='https://www.ebay.com/itm/1',price={'value':'20','currency':'USD'},shippingOptions=[{'shippingCost':{'value':'2','currency':'USD'}},{'shippingCost':{'value':'5','currency':'USD'}}]),self.now.isoformat())
        self.assertIsNone(row['shipping']);self.assertIsNone(row['grade'])
