import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from holy_pokemon.compsniper import (
    CompSniperClient, normalize_psa_sales, normalize_research_history,
    money, psa_cert_url, safe_source_url, main
)


class CompSniperTests(unittest.TestCase):
    def setUp(self):
        self.response = {
            "card": {"specId": "525143", "year": "2001",
                     "setName": "WOTC Black Star Promos", "subject": "ENTEI", "cardNumber": "34"},
            "items": [
                {"gradingCompany": "PSA", "grade": "10", "saleDate": "2026-10-21T12:00:00Z",
                 "salePrice": "1825.00", "saleType": "Auction",
                 "url": "https://www.ebay.com/itm/307228435607"},
                {"gradingCompany": "PSA", "grade": "10", "saleDate": "2026-10-20T15:00:00Z",
                 "salePrice": "1995.60", "saleType": "Fixed Price",
                 "url": "https://www.ebay.com/itm/327406749204"},
                # PSA API provider docs show an UNGRADED row in one response example.
                {"gradingCompany": "UNGRADED", "grade": None, "saleDate": "2026-10-17T12:00:00Z",
                 "salePrice": "2.25", "saleType": "Auction",
                 "url": "https://www.ebay.com/itm/365490372146"},
                {"gradingCompany": "CGC", "grade": "10", "saleDate": "2026-10-17T12:00:00Z",
                 "salePrice": "1125", "url": "https://www.ebay.com/itm/111111111111"},
                {"gradingCompany": "PSA", "grade": "9", "saleDate": "2026-10-17T12:00:00Z",
                 "salePrice": "100.00", "url": "https://www.ebay.com/itm/222222222222"},
                {"gradingCompany": "PSA", "grade": "10", "saleDate": "2026-10-20T15:00:00Z",
                 "salePrice": "1995.60", "url": "https://www.ebay.com/itm/327406749204"},
                {"gradingCompany": "PSA", "grade": "10", "saleDate": "2026-10-17T12:00:00Z",
                 "salePrice": "1500.00", "url": "http://example.net/unsafe"},
            ],
            "population": {"gemRate": 10.0}
        }

    def test_exact_psa_grade_only_not_trusting_provider_filter(self):
        report = normalize_psa_sales(self.response, spec_id="525143", grade=10)
        self.assertEqual(len(report["sales"]), 2)
        self.assertEqual(report["rejection_counts"]["not_psa"], 2)
        self.assertEqual(report["rejection_counts"]["wrong_grade_or_ungraded"], 1)
        self.assertEqual(report["rejection_counts"]["duplicate_observation"], 1)
        self.assertEqual(report["rejection_counts"]["no_source_link"], 1)
        self.assertEqual(report["last_five_reported_median_usd"], "1910.30")
        self.assertIs(report["trade_approved"], False)
        self.assertEqual(report["sales"][0]["ebay_item_id"], "307228435607")

    def test_mismatched_psa_spec_rejected(self):
        with self.assertRaisesRegex(ValueError, "spec ID mismatch"):
            normalize_psa_sales(self.response, spec_id="999999", grade="10")

    def test_offer_not_assumed_to_be_final_accepted_price(self):
        self.response["items"][0]["saleType"] = "Best Offer"
        report = normalize_psa_sales(self.response, spec_id="525143", grade="10")
        self.assertEqual(report["sales"][0]["price_basis"], "BEST_OFFER_ACCEPTED_UNVERIFIED")

    def test_history_listing_aggregates_are_never_transactions(self):
        data = {"source": "ebay_product_research", "results": [
            {"recordType": "listing_aggregate", "soldUnits": 8, "soldPrice": None,
             "soldDate": None, "itemUrl": "https://www.ebay.com/itm/123456789000"},
            {"recordType": "single_unit_listing", "soldUnits": 1,
             "soldPrice": {"amount": "500.00"}, "soldDate": "2026-10-20",
             "title": "Entei PSA 10", "itemUrl": "https://www.ebay.com/itm/123456789001",
             "imageUrl": "https://i.ebayimg.com/example.jpg"}
        ]}
        report = normalize_research_history(data)
        self.assertEqual(report["rejection_counts"]["aggregate_not_individual_sale"], 1)
        self.assertEqual(len(report["sales_needing_identity_review"]), 1)
        self.assertIs(report["sales_needing_identity_review"][0]["grade_and_variant_verified"], False)
        self.assertEqual(report["sales_needing_identity_review"][0]["photo_quality"],
                         "UNVERIFIED_NOT_PSA_SECURESCAN")

    def test_no_key_required_for_offline_usage_and_dry_run(self):
        with patch("builtins.print") as output:
            self.assertEqual(main(["--search", "Entei #34"]), 0)
            self.assertIn("DRY_RUN_NO_API_REQUESTS", output.call_args[0][0])
        with tempfile.TemporaryDirectory() as temp:
            client = CompSniperClient(live=False, cache_dir=temp)
            with self.assertRaisesRegex(RuntimeError, "OFFLINE"):
                client.psa_search("Entei #34")
            self.assertEqual(client.calls, 0)

    def test_request_budget_before_network(self):
        with tempfile.TemporaryDirectory() as temp:
            client = CompSniperClient(live=True, key="cs_live_test", max_calls=0, cache_dir=temp)
            with self.assertRaisesRegex(RuntimeError, "budget exhausted"):
                client.psa_search("Entei #34")

    def test_cache_is_not_a_key_leak_and_offline_read(self):
        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def read(self, n): return json.dumps({"items": [], "marketplace": "psa"}).encode("utf-8")
        with tempfile.TemporaryDirectory() as temp:
            with patch("holy_pokemon.compsniper.urlopen", return_value=FakeResponse()):
                client = CompSniperClient(live=True, key="cs_live_TEST_SECRET", cache_dir=temp)
                first = client.psa_search("Entei #34")
                self.assertEqual(client.calls, 1)
            offline = CompSniperClient(live=False, cache_dir=temp)
            self.assertEqual(offline.psa_search("Entei #34"), first)
            self.assertEqual(offline.calls, 0)
            all_content = "".join(p.read_text() for p in Path(temp).glob("*.json"))
            self.assertNotIn("cs_live_TEST_SECRET", all_content)

    def test_input_validation(self):
        self.assertIsNone(money("NaN"))
        self.assertIsNone(money("-1"))
        self.assertIsNone(psa_cert_url("random"))
        self.assertEqual(psa_cert_url("108755543"), "https://www.psacard.com/cert/108755543")
        self.assertIsNone(safe_source_url("http://example.com"))
        self.assertIsNone(safe_source_url("https://example.com/?api_key=secret"))


if __name__ == "__main__":
    unittest.main()
