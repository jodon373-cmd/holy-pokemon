"""Offline fixtures: does not contact eBay, PSA, or incur paid usage."""

import csv
from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock

from holy_pokemon.automated_discovery import (
    csv_cell,
    direct_search,
    export,
    initialize,
    next_queries,
    rank_for_research,
    record_query,
    store_leads,
    valid_ebay_link,
)
from holy_pokemon.psa_cert_check import check


class DiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = sqlite3.connect(":memory:")
        initialize(self.db)
        self.raw = {
            "listing_id": "v1|123456|0",
            "url": "https://www.ebay.com/itm/123456",
            "title": "2002 Expedition Pokemon PSA 9 card",
            "asking_price": "250",
            "currency": "USD",
            "image_urls": ["https://i.ebayimg.com/images/fake/s-l1600.jpg"],
        }

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_spreadsheet_formula_is_escaped(self):
        self.assertEqual(csv_cell('=HYPERLINK("evil")'), '\'=HYPERLINK("evil")')
        self.assertEqual(csv_cell("Safe listing"), "Safe listing")

    def test_exact_and_fake_urls(self):
        self.assertEqual(valid_ebay_link(self.raw["url"]), self.raw["url"])
        for bad in (
            "http://www.ebay.com/itm/123",
            "https://ebay.com.evil.org/itm/1",
            "https://www.ebay.com@evil.org/itm/1",
            "https://www.ebay.com/signin",
        ):
            with self.assertRaises(ValueError):
                valid_ebay_link(bad)

    def test_ranks_vintage_psa9_for_research_not_profit(self):
        result = rank_for_research(self.raw | {"ask": "250"})
        self.assertGreater(result["research_score"], 50)
        self.assertIsNone(result["economic_profit"])
        self.assertEqual(result["approval"], "NEED_MORE_EVIDENCE")

    def test_accessory_suppression(self):
        result = rank_for_research(
            {"title": "PSA 9 1st edition slab protector case only", "ask": "20"}
        )
        self.assertLess(result["research_score"], 50)

    def test_import_dedup_and_changed_price(self):
        first = store_leads(self.db, [self.raw], query_id="psa-vintage")
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0]["event"], "NEW_LISTING")
        self.assertEqual(store_leads(self.db, [self.raw], query_id="psa-vintage"), [])
        changed = store_leads(
            self.db, [{**self.raw, "asking_price": "200"}], query_id="psa-vintage"
        )
        self.assertEqual(len(changed), 1)
        self.assertEqual(changed[0]["event"], "LISTING_CHANGED")
        out = export(self.db, Path(self.tmp.name), first + changed)
        self.assertEqual(out["stored_leads"], 1)
        with open(out["csv"], newline="") as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(rows[0]["ask"], "200")
        self.assertEqual(rows[0]["approval"], "NEED_MORE_EVIDENCE")

    def test_round_robin_due_only(self):
        first = next_queries(self.db, 2, min_gap_hours=6)
        self.assertEqual(len(first), 2)
        record_query(self.db, first[0][0])
        second = next_queries(self.db, 2, min_gap_hours=6)
        self.assertNotEqual(first[0][0], second[0][0])

    def test_invalid_source_row_dropped(self):
        events = store_leads(
            self.db,
            [self.raw, {**self.raw, "url": "https://attacker.invalid/itm/1"}],
            query_id="operator_import",
        )
        self.assertEqual(len(events), 1)

    def test_direct_search_cached_and_uses_official_filters(self):
        now = datetime(2026, 10, 28, tzinfo=timezone.utc)
        self.db.execute(
            "CREATE TABLE ebay_discovery_cache(cache_key TEXT PRIMARY KEY,retrieved_at TEXT,payload TEXT)"
        )
        client = Mock()
        client.db = self.db
        client.cid = "test-id"
        client.secret = "test-secret"
        client.enabled = True
        client.approved = True
        client.now = lambda: now
        client._token.return_value = "fake-token"
        client._call.return_value = {
            "itemSummaries": [
                {
                    "itemId": "v1|123456|0",
                    "itemWebUrl": "https://www.ebay.com/itm/123456",
                    "title": "Pokemon",
                    "price": {"value": "100", "currency": "USD"},
                    "image": {"imageUrl": "https://i.ebayimg.com/fake.jpg"},
                }
            ]
        }
        rows, cached = direct_search(
            client, "Pokemon PSA", "newlyListed", "FIXED_PRICE"
        )
        self.assertFalse(cached)
        self.assertEqual(len(rows), 1)
        url = client._call.call_args[0][1]
        self.assertIn("sort=newlyListed", url)
        self.assertIn("buyingOptions", url)
        rows2, cached2 = direct_search(
            client, "Pokemon PSA", "newlyListed", "FIXED_PRICE"
        )
        self.assertTrue(cached2)
        self.assertEqual(rows, rows2)
        self.assertEqual(client._call.call_count, 1)

    def test_no_live_without_authorization(self):
        client = Mock(enabled=True, approved=False, cid="id", secret="secret")
        with self.assertRaises(Exception):
            direct_search(client, "Pokemon", "newlyListed", "FIXED_PRICE")

    def test_psa_cert_response_semantics(self):
        fake = lambda url, headers: {
            "IsValidRequest": True,
            "ServerMessage": "No data found",
        }
        result = check("12345678", token="placeholder", request=fake)
        self.assertFalse(result["verified"])
        success = check(
            "12345678",
            token="placeholder",
            request=lambda url, headers: {
                "IsValidRequest": True,
                "ServerMessage": "Request successful",
                "PSACert": {"CertNumber": "12345678", "Grade": "9"},
            },
        )
        self.assertTrue(success["verified"])
        with self.assertRaises(ValueError):
            check("not-a-cert", token="placeholder", request=fake)


if __name__ == "__main__":
    unittest.main()
