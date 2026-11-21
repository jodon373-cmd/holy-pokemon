"""Synthetic contract tests: no marketplace, paid-provider or purchase calls."""
import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from decimal import Decimal as D
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlparse, parse_qs

from holy_pokemon.ebay_browse import EbayBrowse, EbayError
from holy_pokemon.comp_index import CompIndex, CompRecord
from holy_pokemon.ingestion import SeenListingStore
from holy_pokemon.inventory import InventoryLedger
from holy_pokemon.query_planner import four_lane_plan
from holy_pokemon.open_strategy_discovery import Identity
from holy_pokemon.roi_scorer import FeeSchedule, score_opportunity
from holy_pokemon.scan_pipeline import scan_listings, dedupe_listings, inspect_listing_images, main, discover_listings
from holy_pokemon.compsniper import enrich_comp_index


def index():
    records=[]
    for company,grade,price in [('PSA','9','200'),('CGC','GEM_MINT_10','1000'),
                                ('CGC','PRISTINE_10','9000'),('CGC','8','60'),('BGS','9.5','200')]:
        for i in range(3):
            records.append(CompRecord('Jungle','Vaporeon','12','Unlimited',company,grade,
                f'2026-11-{10+i}',D(price),f'https://example.org/{company}/{grade}/{i}',
                '', 'Holo','English'))
    return CompIndex(records)


def listing(**changes):
    row=dict(listing_id='v1|123456789012|0',title='1999 Pokemon Jungle Vaporeon 12/64 Unlimited Holo PSA 9',
             card='Vaporeon',number='12',set_name='Jungle',edition='Unlimited',finish='Holo',language='English',
             asking_price='100',shipping='0',currency='USD',as_of='2026-11-21',buying_options=['FIXED_PRICE'])
    row.update(changes)
    return row


FEES=FeeSchedule(seller_fee_pct=10,selling_fixed=0,grading_fee=20,grading_shipping=0,
                 supplies=0,outbound_shipping=0,purchase_tax_pct=0)


class BrowsePrecision(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:');self.calls=[]
        self.clock=datetime(2026,11,21,tzinfo=timezone.utc)
        self.rows=[dict(itemId='v1|123456789012|0',title='Vaporeon Holo PSA 9',
                       itemWebUrl='https://www.ebay.com/itm/123456789012',price=dict(value='20',currency='USD'),
                       buyingOptions=['FIXED_PRICE'])]
        def request(method,url,headers,data):
            self.calls.append((method,url))
            return (200,{},dict(access_token='fixture',expires_in=86400)) if method=='POST' else (200,{},dict(itemSummaries=self.rows,total=len(self.rows)))
        self.client=EbayBrowse(self.db,enabled=True,production_approved=True,client_id='synthetic',
            client_secret='synthetic',request=request,sleep=lambda _:None,now=lambda:self.clock,page_size=100)

    def tearDown(self):
        self.db.close()

    def test_separate_passes_sorts_and_no_offer_bug(self):
        self.client.search_passes('(Vaporeon,Vaporean) PSA 9',max_price=100)
        params=[parse_qs(urlparse(url).query) for method,url in self.calls if method=='GET']
        self.assertEqual([p['sort'][0] for p in params],['newlyListed','endingSoonest'])
        self.assertTrue(all('BEST_OFFER' not in p['filter'][0] for p in params))
        with self.assertRaises(ValueError):
            self.client.search_page('Pokemon',filters={'buyingOptions':'{FIXED_PRICE|AUCTION|BEST_OFFER}'})

    def test_descriptor_aspect_extended_and_local_cap_on_cache(self):
        self.rows.append(dict(self.rows[0],itemId='v1|999999999999|0',price=dict(value='999',currency='USD')))
        kwargs=dict(max_price=50,condition_ids=[2750],aspect_filter={'Grade':'9'},fieldgroups='EXTENDED',
                    expected_grader='PSA',expected_grade='9',condition_descriptors={'27501':'PSA','27502':'9'})
        first=self.client.search_page('Vaporeon PSA 9',**kwargs)
        self.assertEqual(len(first['rows']),1)
        self.assertEqual(first['local_precision_rejections'],1)
        self.assertEqual(first['rows'][0]['condition_descriptor_check'],'UNVERIFIED_OR_MISMATCH')
        p=parse_qs(urlparse(self.calls[-1][1]).query)
        self.assertIn('categoryId:183454',p['aspect_filter'][0])
        self.assertIn('conditionIds:{2750}',p['filter'][0])
        self.clock+=timedelta(hours=4)
        self.assertTrue(self.client.search_page('Vaporeon PSA 9',**kwargs)['cache_hit'])
        self.clock+=timedelta(hours=2)
        self.assertFalse(self.client.search_page('Vaporeon PSA 9',**kwargs)['cache_hit'])

    def test_wrong_grade_and_wildcards_rejected(self):
        self.rows[0]['title']='Vaporeon Holo PSA 8'
        self.assertEqual(self.client.search_page('Vaporeon PSA 9',expected_grade=9)['rows'],[])
        with self.assertRaises(ValueError):
            self.client.search_page('Vaporeon*')

    def test_run_budget_counts_oauth_and_stops_get(self):
        self.client.run_limit=1
        with self.assertRaises(EbayError):
            self.client.search_page('Pokemon')
        self.assertEqual([c[0] for c in self.calls],['POST'])

    def test_http_date_cooldown_no_retry(self):
        self.client._token()
        def request(*args):
            self.calls.append(args[:2]);return 429,{'Retry-After':'Sat, 21 Nov 2026 00:02:00 GMT'},{}
        self.client.request=request
        with self.assertRaises(EbayError):self.client.search_page('Pokemon')
        count=len(self.calls)
        with self.assertRaises(EbayError):self.client.search_page('Pokemon')
        self.assertEqual(count,len(self.calls))


class FredyEconomics(unittest.TestCase):
    def score(self,row=None,**kwargs):
        return score_opportunity(listing=row or listing(),card='Vaporeon',number='12',
            set_name='Jungle',edition='Unlimited',comp_index=index(),fees=FEES,**kwargs)

    def test_original_discount_and_incremental_no_market_rescue(self):
        r=self.score()
        self.assertEqual(r['original_grade_fallback']['net_profit_usd'],'80.00')
        self.assertEqual(r['incremental_over_original'],'700.00')
        self.assertEqual(r['max_offer_usd'],'130.00')
        self.assertEqual(r['financial_gate'],'WITHIN_MODELED_CEILING')
        self.assertIsNone(r['grade_probability']);self.assertFalse(r['trade_approved'])
        overpriced=self.score(listing(asking_price='150'))
        self.assertEqual(overpriced['financial_gate'],'OVER_MAX_OFFER')
        self.assertEqual(overpriced['opportunity_score'],0)

    def test_auction_bid_and_buyer_premium_are_costed(self):
        row = listing(asking_price=None, current_bid={'value': '100', 'currency': 'USD'},
                      buying_options=['AUCTION'], buyer_premium_pct='10')
        scored = self.score(row)
        self.assertEqual(scored['landed_cost_usd'], '110.00')
        self.assertEqual(scored['max_bid_ceiling'], '118.18')
        self.assertEqual(scored['observed_price_basis'], 'AUCTION_BID')
        self.assertEqual(self.score(dict(row, current_bid={'value': '100', 'currency': 'GBP'}))
                         ['status'], 'SKIPPED_NO_ASKING_PRICE')

    def test_every_failed_attempt_is_charged(self):
        r=self.score(listing(route_steps=[dict(grader='CGC',grading_fee='20'),dict(grader='CGC',grading_fee='30')]))
        self.assertEqual(r['total_investment_usd'],'150.00')
        self.assertEqual(r['incremental_over_original'],'670.00')
        self.assertEqual(self.score(listing(route_steps=[dict(grader='CGC')]))['status'],'MISSING_ROUTE_STEP_COST')

    def test_pristine_never_sets_baseline_and_no_original_failure_floor(self):
        r=self.score(target_grade_bucket='PRISTINE_10')
        self.assertEqual(r['target_comp']['grade_bucket'],'GEM_MINT_10')
        self.assertEqual(r['max_offer_usd'],'130.00')
        self.assertIn('PRISTINE_OUTLIER_ONLY',r['warnings'])
        self.assertEqual(r['pristine_score_bonus'],0)
        self.assertEqual(r['downside_net_profit_usd'], '-66.00')
        self.assertEqual(r['break_even_upgrade_rate'], '0.0780')
        self.assertEqual(r['failure_scenarios'][0]['minimum_upgrade_rate_to_beat_original'], '0.1726')
        self.assertEqual(r['failure_scenarios'][0]['grade'],'8')

    def test_bgs_missing_subgrades_reserve_and_channels(self):
        r=self.score(listing(title='1999 Jungle Vaporeon 12/64 Unlimited Holo BGS 9.5',
            exit_channels={'direct_tcg':dict(fee_pct='0',fixed='0',shipping='0',days_to_cash=10)}))
        self.assertIn('UNVERIFIED_SUBGRADES',r['warnings'])
        self.assertEqual(r['downside_reserve_usd'],'150.00')
        self.assertEqual(r['max_offer_usd'],'0.00')
        self.assertEqual(r['channel_comparison'][-1]['net_proceeds_usd'],'1000.00')
        self.assertEqual(r['channel_comparison'][1]['net_proceeds_usd'],None)

    def test_identity_substitution_cannot_score(self):
        self.assertEqual(self.score(listing(title='Jungle Vaporeon 32/64 Unlimited Holo PSA 9'))['status'],'IDENTITY_TITLE_CONFLICT')

    def test_declared_value_tier_and_capital_cost_reduce_margin(self):
        from dataclasses import replace
        idx=CompIndex([replace(r,price_usd=D('2000')) if r.grade_bucket=='GEM_MINT_10' else r for r in index().records])
        r=score_opportunity(listing=listing(),card='Vaporeon',number='12',set_name='Jungle',edition='Unlimited',comp_index=idx)
        self.assertEqual(r['grading_tier'],'Standard')
        self.assertEqual(r['fee_assumptions']['grading_fee'],'55')
        capital=self.score(listing(annual_capital_cost_pct='20',capital_lock_days='365'))
        self.assertEqual(capital['modeled_capital_cost_usd'],'24.00')
        self.assertLess(D(capital['target_max_offer_usd']),D(self.score()['target_max_offer_usd']))


class PipelineContracts(unittest.TestCase):
    def test_four_lanes_promo_merge_routes_and_auction_depth(self):
        plan=four_lane_plan([Identity('Jungle','Vaporeon','12','Unlimited holo')],index(),limit=100,
                            now=datetime(2026,11,21,tzinfo=timezone.utc))
        self.assertEqual({p['lane'] for p in plan},{'high_spread','auction_sniper','poor_title','promo_priority'})
        self.assertTrue(all(p['target_comp_count']>=3 for p in plan if p['lane']=='auction_sniper'))
        self.assertTrue(all(len(p['ebay_query'])<=100 for p in plan))
        self.assertTrue(any(p.get('expected_grader')=='BGS' for p in plan))
        self.assertTrue(any('-shadowless' in p['ebay_query'] for p in plan if p['lane']=='high_spread'))

    def test_persistent_only_new_and_bridge_dedupe(self):
        a=listing(certification_number='12345678')
        b=listing(listing_id='v1|888888888888|0',certification_number='12345678')
        c=listing(listing_id='v1|888888888888|0',certification_number=None)
        self.assertEqual(len(dedupe_listings([a,b,c])),1)
        with tempfile.TemporaryDirectory() as tmp:
            seen=SeenListingStore(Path(tmp)/'seen.db')
            r=scan_listings([a,b,c],comp_index=index(),fees=FEES,seen_store=seen,only_new=True)
            self.assertEqual(r['returned_count'],1);self.assertEqual(r['cross_query_duplicates'],2)
            seen.close();seen=SeenListingStore(Path(tmp)/'seen.db')
            self.assertEqual(scan_listings([a],comp_index=index(),seen_store=seen,only_new=True)['returned_count'],0)
            seen.close()

    def test_dedupe_retains_multiple_routes(self):
        first=listing(proposed_target_grader='CGC',proposed_target_grade='GEM_MINT_10')
        second=listing(proposed_target_grader='PSA',proposed_target_grade='10')
        r=scan_listings([first,second],comp_index=index(),fees=FEES)['ranked_leads'][0]
        self.assertEqual({x['target_route'] for x in r['route_comparison']},{'CGC_GEM_MINT_10','PSA_10'})

    def test_best_route_wins_regardless_of_discovery_order_and_veto_drops_priority(self):
        cgc = listing(proposed_target_grader='CGC', proposed_target_grade='GEM_MINT_10')
        psa = listing(proposed_target_grader='PSA', proposed_target_grade='10')
        for rows in ([cgc, psa], [psa, cgc]):
            lead = scan_listings(rows, comp_index=index(), fees=FEES)['ranked_leads'][0]
            self.assertEqual(lead['target_route'], 'CGC_GEM_MINT_10')
            self.assertEqual(lead['review_queue'], 'PRIORITY_REVIEW')
        damaged = dict(cgc, condition_review={'visible_defect': True})
        lead = scan_listings([damaged], comp_index=index(), fees=FEES)['ranked_leads'][0]
        self.assertEqual(lead['review_queue'], 'REJECTED_CONDITION')

    def test_misspelling_is_a_review_proposal_and_language_conflicts_stop_scoring(self):
        from dataclasses import replace
        from holy_pokemon.title_parser import parse_title

        catalog = CompIndex([replace(index().records[0], card='Pikachu', number='60')])
        row = listing(title='Pokemon Jungle Pickachu #60 Unlimited Holo PSA 9', lane='poor_title')
        for field in ('card', 'number', 'set_name', 'edition', 'finish', 'language'):
            row.pop(field)
        scored = scan_listings([row], comp_index=catalog, fees=FEES)['ranked_leads'][0]
        self.assertEqual(scored['identity_review_proposal']['card'], 'Pikachu')
        self.assertEqual(scored['status'], 'MISSING_EXACT_IDENTITY')
        title = listing()['title'].replace('Pokemon', 'Dutch Pokemon')
        self.assertEqual(parse_title(title).language, 'Dutch')
        scored = scan_listings([listing(title=title)], comp_index=index(), fees=FEES)['ranked_leads'][0]
        self.assertEqual(scored['status'], 'IDENTITY_TITLE_CONFLICT')

    def test_same_sale_aliases_count_once_and_conflicts_exclude_transaction(self):
        from dataclasses import replace

        record = replace(index().records[0], source_url='https://www.ebay.com/itm/123456789012')
        alternate = replace(record, source_url='https://www.ebay.com/itm/Vaporeon/123456789012?tracking=test')
        self.assertEqual(len(CompIndex([record, alternate]).records), 1)
        conflict = CompIndex([record, alternate, replace(alternate, price_usd=D('400'))])
        self.assertEqual(conflict.records, [])
        self.assertEqual(conflict.conflicting_ebay_item_ids, {'123456789012'})

    def test_enrichment_repairs_missing_original_comps_once_for_multiple_copies(self):
        complete = index()
        thin = CompIndex(r for r in complete.records if r.grader != 'PSA')
        rows = [listing(), listing(listing_id='v1|222222222222|0')]

        class Client:
            calls = 0
            max_calls = 3

        with patch('holy_pokemon.compsniper.enrich_comp_index',
                   return_value=(complete, {'added': 3})) as enrich:
            report = scan_listings(rows, comp_index=thin, fees=FEES, live=True, comp_client=Client())
        enrich.assert_called_once()
        self.assertEqual(enrich.call_args.kwargs, {'target_grader': 'PSA', 'target_grade': '9'})
        self.assertEqual([row['review_queue'] for row in report['ranked_leads']],
                         ['PRIORITY_REVIEW', 'PRIORITY_REVIEW'])

    def test_queries_share_page_requests_and_paginate_round_robin(self):
        class Client:
            page_size = 100

            def __init__(self):
                self.calls = []

            def search_page(self, query, *, offset, **kwargs):
                self.calls.append((query, offset))
                return {'rows': [listing()], 'has_more': offset == 0}

        query = dict(ebay_query='Vaporeon', lane='high_spread', buying_option='FIXED_PRICE',
                     sort='newlyListed', target_grader='PSA', target_grade_bucket='10')
        client = Client()
        rows, errors = discover_listings(client, [
            query, dict(query, target_grader='CGC', target_grade_bucket='GEM_MINT_10'),
            dict(query, ebay_query='Jolteon'),
        ], pages_per_query=2)
        self.assertFalse(errors)
        self.assertEqual(client.calls, [('Vaporeon', 0), ('Jolteon', 0),
                                        ('Vaporeon', 100), ('Jolteon', 100)])
        self.assertEqual(len(rows), 6)

    def test_saved_cache_loaded_read_only(self):
        from holy_pokemon.scan_pipeline import load_saved_listings
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'cache.sqlite3';db=sqlite3.connect(p)
            db.execute('CREATE TABLE record(kind TEXT,payload TEXT,created_at TEXT)')
            db.execute('INSERT INTO record VALUES(?,?,?)',('lead',json.dumps(listing()),'2026-11-21'))
            db.commit();db.close();before=p.read_bytes()
            self.assertEqual(len(load_saved_listings(p)),1)
            self.assertEqual(before,p.read_bytes())

    def test_blur_missing_back_glare_never_grade(self):
        with patch('holy_pokemon.centering_v3.measure_file',return_value=dict(status='ABSTAIN',reason='image_too_blurry')):
            r=inspect_listing_images(dict(image_path='/missing',condition_review={'slab_glare':True}))
            self.assertIn('MISSING_BACK_PHOTO',r['warnings']);self.assertIn('SLAB_GLARE',r['warnings'])
            self.assertIsNone(r['grade_prediction'])

    def test_unlabeled_downloads_get_diagnostics_not_back_assumption(self):
        with patch('holy_pokemon.centering_v3.measure_file',return_value=dict(status='ABSTAIN')) as measure:
            r=inspect_listing_images(dict(photo_paths=[dict(path='/fixture',side=None)]))
            self.assertEqual(measure.call_count,2)
            self.assertIn('MISSING_BACK_PHOTO',r['warnings'])

    def test_discovery_stops_on_provider_failure(self):
        class Client:
            calls=0
            def search_page(self,*args,**kwargs):
                self.calls+=1;raise EbayError('fixture')
        client=Client();plan=[dict(ebay_query='Pokemon',lane='high_spread',buying_option='FIXED_PRICE',sort='newlyListed')]*5
        rows,errors=discover_listings(client,plan)
        self.assertEqual(client.calls,1);self.assertFalse(rows);self.assertEqual(len(errors),1)

    def test_cli_no_arguments_is_offline_and_exports_contract(self):
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(main([]),0)
        self.assertFalse(json.loads(stdout.getvalue())['trade_approved'])
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp);(p/'in.json').write_text(json.dumps([listing()]))
            with contextlib.redirect_stdout(io.StringIO()):
                main(['--input',str(p/'in.json'),'--output-json',str(p/'out.json'),'--output-csv',str(p/'out.csv')])
            r=json.loads((p/'out.json').read_text())['ranked_leads'][0]
            for field in ('trade_approved','max_offer_usd','incremental_over_original','source_urls'):
                self.assertIn(field,r);self.assertIn(field,(p/'out.csv').read_text())

    def test_live_enrichment_discards_unresolved_offer(self):
        class Client:
            def recent_sold(self,keyword):
                return dict(items=[dict(url='https://www.ebay.com/itm/123456789123',
                    title='Jungle Vaporeon 12/64 Unlimited Holo CGC 10 Gem Mint',
                    endedAt='2026-11-20T00:00:00Z',soldCurrency='USD',soldPrice=900,
                    bestOfferAccepted=True,acceptedOfferPriceStatus='pending')])
        idx=index();after,report=enrich_comp_index(Client(),idx,listing())
        self.assertEqual(len(after.records),len(idx.records));self.assertEqual(report['added'],0)

    def test_inventory_aging_retry_and_future_cash_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger=InventoryLedger(Path(tmp)/'inventory.db');ledger.add_specimen('copy','fixture','fixture')
            ledger.event('buy','copy','purchase_confirmed','fixture',amount='100',event_at='2026-01-01T00:00:00Z')
            ledger.grading_attempt('one','copy','fixture',event_at='2026-02-01T00:00:00Z',grader='CGC',grade='9',paid_fee='20')
            ledger.grading_attempt('two','copy','fixture',event_at='2026-03-01T00:00:00Z',grader='CGC',grade='10',paid_fee='20')
            ledger.event('payout','copy','payout_received','fixture',amount='300',event_at='2027-01-01T00:00:00Z',details={'receipt_verified':True})
            r=ledger.cash_cycle('copy',as_of='2026-11-21T00:00:00Z')
            self.assertTrue(r['aging_warning']);self.assertEqual(r['capital_locked_usd'],'140.00')
            self.assertEqual(r['repeat_grading_cost_usd'],'20.00');ledger.close()
