import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from decimal import Decimal

from holy_pokemon.fredy_business import monthly_analysis, inspect_transport, operating_rules
from holy_pokemon.strategy_engine import (
    acquisition_total, outcome, compare, research_signal, budget_check, binary_break_even,
)

MONTH_FILE = Path(__file__).resolve().parents[1] / "research/fredy_monthly_2026.csv"
ZERO_ROUTE = dict(
    grading="0",grading_shipping="0",grading_insurance="0",upcharge="0",
    outbound_shipping="0",vault_withdrawal="0",vault_early_fee="0",
    vault_consignment_fixed="0",holding_cost="0",contingency="0",
)
BUY = dict(ask="100",buyer_shipping="5",purchase_tax="7",buyer_premium="0")

class BusinessTests(unittest.TestCase):
    def test_all_monthly_totals_reconcile(self):
        r=monthly_analysis(MONTH_FILE)
        self.assertEqual(r["totals"]["sold"],"506")
        self.assertEqual(r["totals"]["revenue"],"444671.20")
        self.assertEqual(r["totals"]["sold_basis"],"214077.66")
        self.assertEqual(r["totals"]["reported_profit"],"230593.54")
        self.assertEqual(r["totals"]["monthly_spending"],"342656.24")

    def test_monthly_conflicts_explicit(self):
        r=monthly_analysis(MONTH_FILE)
        self.assertIn("July",r["july_spend_disagreement"])
        self.assertIn("April",r["may_vs_april_disagreement"])

    def test_evidence_rules_have_workflows(self):
        rules=operating_rules()
        self.assertGreaterEqual(len(rules),10)
        self.assertIn("cash_cycle",{r["id"] for r in rules})

    def test_compact_transport_rejects_missing_entries(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"x.zip"
            with zipfile.ZipFile(p,"w") as z:z.writestr("README","invalid")
            with self.assertRaises(ValueError):inspect_transport(p)

    def test_compact_transport_does_not_label_unique_cards(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"x.zip"
            with zipfile.ZipFile(p,"w") as z:
                z.writestr("source_asset_inventory.json",json.dumps([{"source":"synthetic"}]*18))
                records=[]
                for i in range(250):
                    records.append(json.dumps({"source_archive":"synthetic","archive_sha256":"ab"*32,
                        "member_path":"cases.csv","row_number":i+1,"source_row":{"card":"TEST"},
                        "game":"pokemon","provenance_status":"synthetic"}))
                z.writestr("source_case_rows.jsonl","\n".join(records))
            result=inspect_transport(p)
            self.assertEqual(result["raw_case_rows"],250)
            self.assertIsNone(result["physical_unique"])
            self.assertEqual(result["training_images"],0)

class FinancialTests(unittest.TestCase):
    def test_costs_and_original_vs_regrade(self):
        baseline=dict(ZERO_ROUTE,route="sell_original",exit_price="160",fee_pct="10",exit_price_kind="manual_comp")
        upgrade=dict(ZERO_ROUTE,route="cgc_gem_10",exit_price="350",fee_pct="10",grading="35",grading_shipping="20")
        o=compare(BUY,[baseline,upgrade])
        self.assertEqual(o[0]["net_profit_if_sold"],"32.00")
        self.assertEqual(o[1]["net_profit_if_sold"],"148.00")
        self.assertEqual(o[1]["incremental_over_original"],"116.00")
        self.assertEqual(o[1]["sale_is_realized"],False)

    def test_missing_fees_do_not_turn_to_zero(self):
        r=outcome(BUY,dict(route="sell_original",exit_price="200",fee_pct="12"))
        self.assertFalse(r["data_complete"])
        self.assertIsNone(r["net_profit_if_sold"])

    def test_unknown_market_comps_keeps_research_visible(self):
        r=research_signal({"ask":"82.95","possible_best_exit":"420","exact_variant_verified":False})
        self.assertTrue(r["research_visible"])
        self.assertEqual(r["approval"],"NOT_READY")
        self.assertEqual(r["spread_type"],"hypothetical_grade_spread_not_profit")

    def test_break_even_sensitivity_not_probability(self):
        self.assertEqual(binary_break_even("200","-100"),"0.3333")

    def test_shared_budget_and_reserve(self):
        r=budget_check(["1800","300"])
        self.assertFalse(r["within_cap"])
        self.assertEqual(r["reserve_untouched"],"5000.00")
        self.assertFalse(r["automated_purchase_authorized"])

    def test_intact_failed_crossover_charges_full_fee(self):
        failed=dict(ZERO_ROUTE,route="psa_intact_crossover_rejected",exit_price="100",
            fee_pct="10",grading="75",grading_shipping="20")
        r=outcome(BUY,failed)
        self.assertEqual(r["net_profit_if_sold"],"-117.00")

    def test_invalid_fee_rejected(self):
        route=dict(ZERO_ROUTE,route="sell_original",exit_price="150",fee_pct="101")
        with self.assertRaises(ValueError):outcome(BUY,route)

if __name__ == "__main__":unittest.main()
