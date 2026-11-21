"""Pure local dashboard integration; no network or API credentials."""

from pathlib import Path
import sqlite3
import tempfile
import unittest

from holy_pokemon.automated_discovery import initialize, store_leads
from holy_pokemon.discovery_service import discovery_snapshot


class DashboardFeedTests(unittest.TestCase):
    def test_not_started_state(self):
        with tempfile.TemporaryDirectory() as t:
            r = discovery_snapshot(Path(t) / "missing.sqlite")
            self.assertEqual(r["status"], "NOT_STARTED")
            self.assertEqual(r["count"], 0)

    def test_synthetic_listing_feed_for_dashboard(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "research.sqlite"
            with sqlite3.connect(p) as db:
                initialize(db)
                store_leads(
                    db,
                    [
                        {
                            "listing_id": "v1|123456|0",
                            "url": "https://www.ebay.com/itm/123456",
                            "title": "SYNTHETIC vintage PSA 9 sample",
                            "asking_price": "125",
                            "currency": "USD",
                        }
                    ],
                    query_id="offline_fixture",
                )
            r = discovery_snapshot(p)
            self.assertEqual(r["status"], "READY")
            self.assertEqual(r["count"], 1)
            self.assertEqual(r["leads"][0]["approval"], "NEED_MORE_EVIDENCE")
            self.assertFalse(r["live_verified"])
            self.assertEqual(
                r["leads"][0]["source_url"], "https://www.ebay.com/itm/123456"
            )


if __name__ == "__main__":
    unittest.main()
