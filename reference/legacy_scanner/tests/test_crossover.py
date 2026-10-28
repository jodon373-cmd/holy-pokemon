import unittest
from datetime import date
from decimal import Decimal
from scanner.crossover import administrative_reholder_grade,break_even,compare_all_paths,landed_cost
from scanner.strategy_common import CostQuote,allocate_shared

class CrossoverTests(unittest.TestCase):
    def test_legacy_mapping_is_administrative_and_explicit(self):
        r=dict(grader='CGC',grade='9.5',slab_generation='legacy_blue',slab_generation_confirmed=True,grade_designation='gem_mint')
        self.assertEqual(administrative_reholder_grade(r),'10')
        for patch in ({'grade':'9'},{'slab_generation':'current'},{'slab_generation_confirmed':False},{'grade_designation':'mint'}):
            self.assertIsNone(administrative_reholder_grade({**r,**patch}))
    def test_failed_intact_attempt_charged_and_upgrade_not_assumed(self):
        costs=CostQuote(*([Decimal(10)]*10),source_url='https://example.org/quote',observed_at=date(2026,10,23))
        row=dict(listing_id='x',grader='CGC',grade='9',asking_price=100,shipping=0,purchase_tax_pct=0,buyer_premium_pct=0)
        b={k:dict(lower_quartile=Decimal(100),count=6,links=[]) for k in ('original','cgc10','psa8','psa9','psa10')}
        paths={r['path']:r for r in compare_all_paths(row,b,costs)}
        self.assertEqual(paths['intact_min10_rejected']['processing_cost'],30)
        self.assertEqual(paths['intact_min10_success']['processing_cost'],40)
        self.assertIsNone(paths['keep']['probability_psa10'])
        self.assertLess(paths['intact_min10_rejected']['net_profit'],paths['keep']['net_profit'])
        self.assertIsNone(landed_cost({**row,'shipping':None}))
    def test_binary_threshold_is_not_prediction(self):
        self.assertEqual(break_even(100,-100),Decimal('.5'))
        self.assertIsNone(break_even(-1,-100))
    def test_shared_budget_deduplicates_across_lanes(self):
        rows=[dict(actionable=True,url='https://example.org/'+str(i),physical_identity=str(i),certification_number='same' if i<2 else str(i),landed=600,required_reserve=100,allocation_score=i) for i in range(4)]
        batch,total=allocate_shared(rows)
        self.assertEqual(len(batch),2);self.assertEqual(total,1400)
        with self.assertRaises(ValueError): allocate_shared(rows,2001)
