"""Regression checks for reviewed upgrade failure cases; fixtures are synthetic."""
import csv
from decimal import Decimal as D
from pathlib import Path
import tempfile
import unittest

from holy_pokemon.comp_index import CompIndex, CompRecord, _norm_grade_bucket
from holy_pokemon.open_strategy_discovery import Identity
from holy_pokemon.query_planner import build_ebay_query
from holy_pokemon.roi_scorer import score_opportunity
from holy_pokemon.strategy_common import export_csv
from holy_pokemon.title_parser import parse_title


class UpgradeRegressionTests(unittest.TestCase):
    def record(self, edition='unlimited', finish='Holo', grade='GEM_MINT_10', price='500', company='CGC'):
        return CompRecord('Jungle', 'Vaporeon', '12', edition, company, grade,
                          '2026-10-01', D(price), 'https://example.com/sale', '', finish)

    def summary(self, records, **kwargs):
        return CompIndex(records).summarize(card='Vaporeon', number='12', grader='CGC',
                                           grade_bucket='GEM_MINT_10', **kwargs)

    def score(self, **changes):
        listing = dict(title='Jungle Vaporeon 12/64 Holo PSA 9', asking_price='100', shipping='0')
        listing.update(changes)
        return score_opportunity(listing=listing, card='Vaporeon', number='12',
                                 set_name='Jungle', comp_index=CompIndex([self.record(), self.record(company='PSA', grade='9')]))

    def test_edition_mismatch_has_no_fallback(self):
        self.assertIsNone(self.summary([self.record()], edition='1st Edition'))

    def test_underspecified_finish_does_not_mix_variants(self):
        self.assertIsNone(self.summary([self.record(), self.record(finish='Non-Holo')]))

    def test_set_filter_applies_without_edition(self):
        self.assertIsNone(self.summary([self.record()], set_name='Fossil'))

    def test_decimal_grades_not_coerced(self):
        self.assertEqual(_norm_grade_bucket('PSA', '9.5'), ('PSA', '9.5'))
        self.assertIsNone(_norm_grade_bucket('PSA', 'Grade 9 guide'))

    def test_trimmed_outlier_does_not_affect_weighted_price(self):
        summary = self.summary([self.record(price=p) for p in ['100', '100', '100', '100', '10000']])
        self.assertEqual(summary.count, 4)
        self.assertEqual(summary.recency_weighted_usd, D('100'))

    def test_missing_shipping_stays_unknown(self):
        self.assertEqual(self.score(shipping=None)['status'], 'MISSING_SHIPPING_COST')

    def test_invalid_costs_and_currency(self):
        for price in ['NaN', 'Infinity', '-1', 'oops']:
            self.assertEqual(self.score(asking_price=price)['status'], 'INVALID_COST')
        self.assertEqual(self.score(currency='CAD')['status'], 'UNSUPPORTED_CURRENCY')

    def test_original_holder_not_a_regrade_fallback(self):
        self.assertIsNone(self.score()['downside_net_profit_usd'])
        self.assertIsNone(self.score()['break_even_upgrade_rate'])

    def test_qualified_listing_disqualified(self):
        self.assertTrue(parse_title('Jungle Vaporeon PSA 9 OC').disqualified)

    def test_long_identity_fails_explicitly(self):
        with self.assertRaises(ValueError):
            build_ebay_query(Identity('Very long set ' * 20, 'Vaporeon', '12', 'unlimited'))

    def test_csv_formula_is_escaped(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = export_csv(Path(tmp) / 'leads.csv', [{'title': '=1+1'}])
            with p.open() as f:
                self.assertEqual(next(csv.DictReader(f))['title'], "'=1+1")
