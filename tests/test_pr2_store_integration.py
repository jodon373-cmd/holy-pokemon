"""PR #2 integration against the actual Store/dashboard, always offline fixtures."""

import csv
from contextlib import redirect_stdout
import io
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch
from holy_pokemon.automated_discovery import (
    initialize,
    store_leads,
    sync_into_holy_pokemon,
    scan_once,
    main,
)
from holy_pokemon.discovery_service import discovery_snapshot
from holy_pokemon.ebay_browse import EbayBrowse
from holy_pokemon.store import Store
from holy_pokemon.app_service import state, command
from holy_pokemon.market import rank_leads
from holy_pokemon.psa_cert_check import check


class PR2StoreIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "app.sqlite")
        self.collector = self.root / "collector.sqlite"
        self.row = {
            "listing_id": "v1|123456789|0",
            "title": "SYNTHETIC vintage Expedition PSA 9 fixture",
            "url": "https://www.ebay.com/itm/123456789",
            "asking_price": "125",
            "currency": "USD",
            "shipping": "7",
            "image_urls": ["https://i.ebayimg.com/SYNTHETIC.jpg"],
            "observed_at": "2026-10-28",
            "retrieved_at": "2026-10-28T12:00:00+00:00",
            "source": "operator_import",
        }

    def tearDown(self):
        self.store.close()
        self.temp.cleanup()

    def collect(self, row=None):
        with sqlite3.connect(self.collector) as db:
            initialize(db)
            store_leads(db, [row or self.row], query_id="SYNTHETIC_FIXTURE")
        return discovery_snapshot(self.collector)

    def test_full_collector_store_dashboard_path_and_repeat_sync(self):
        feed = self.collect()
        self.store.put("review", "preserve-me", {"text": "Existing newer local work"})
        result = sync_into_holy_pokemon(feed["leads"], store=self.store)
        self.assertEqual(result["accepted"], 1)
        self.assertEqual(
            sync_into_holy_pokemon(feed["leads"], store=self.store)["duplicates"], 1
        )
        self.assertEqual(
            self.store.get("review", "preserve-me")["text"], "Existing newer local work"
        )
        with patch(
            "holy_pokemon.app_service.discovery_database", return_value=self.collector
        ):
            s = state(self.store)
        self.assertEqual(s["discovery"]["count"], 1)
        self.assertEqual(len(s["leads"]), 1)
        self.assertEqual(s["discovery"]["leads"][0]["app_lead_id"], s["leads"][0]["id"])
        lead = s["leads"][0]
        self.assertEqual(lead["source_url"], self.row["url"])
        self.assertEqual(lead["buyer_shipping"], "7")
        self.assertEqual(lead["image_urls"], self.row["image_urls"])
        self.assertEqual(lead["retrieved_at"], self.row["retrieved_at"])
        self.assertEqual(lead["source_type"], "DISCOVERY_PIPELINE")
        self.assertEqual(lead["approval"], "NEED_MORE_EVIDENCE")
        self.assertFalse(lead["purchase_authorized"])
        self.assertEqual(self.store.rows("sale"), [])

    def test_same_day_price_change_updates_latest_queue_without_duplicate_card(self):
        feed = self.collect()
        sync_into_holy_pokemon(feed["leads"], store=self.store)
        feed = self.collect({**self.row, "asking_price": "100"})
        result = sync_into_holy_pokemon(feed["leads"], store=self.store)
        self.assertEqual(result["accepted"], 1)
        self.assertEqual(len(self.store.rows("lead")), 2)
        queue = rank_leads(self.store)
        self.assertEqual(len(queue), 1)
        self.assertEqual(queue[0]["ask"], "100")

    def test_unknown_currency_shipping_and_auction_ask_stay_unknown(self):
        row = {
            **self.row,
            "currency": None,
            "shipping": None,
            "asking_price": None,
            "current_bid": {"value": "90", "currency": "USD"},
            "buying_options": ["AUCTION"],
        }
        result = sync_into_holy_pokemon(self.collect(row)["leads"], store=self.store)
        self.assertEqual(result["accepted"], 1)
        lead = self.store.rows("lead")[0]
        self.assertIsNone(lead["currency"])
        self.assertIsNone(lead["ask"])
        self.assertIsNone(lead["buyer_shipping"])
        self.assertEqual(lead["current_bid"]["value"], "90")

    def test_actual_browse_adapter_shared_quota_scan_to_store_with_mock_transport(self):
        calls = []

        def request(method, url, headers, data):
            calls.append((method, url))
            if method == "POST":
                return 200, {}, {"access_token": "SYNTHETIC-token", "expires_in": 7200}
            return (
                200,
                {},
                {
                    "itemSummaries": [
                        {
                            "itemId": self.row["listing_id"],
                            "itemWebUrl": self.row["url"],
                            "title": self.row["title"],
                            "price": {"value": "125", "currency": "USD"},
                            "buyingOptions": ["FIXED_PRICE"],
                        }
                    ]
                },
            )

        client = EbayBrowse(
            self.store.db,
            enabled=True,
            production_approved=True,
            client_id="SYNTHETIC-id",
            client_secret="SYNTHETIC-secret",
            request=request,
            sleep=lambda _: None,
        )
        with sqlite3.connect(self.collector) as db:
            status, alerts = scan_once(
                db,
                client,
                maximum_queries=1,
                plans=[("fixture", "Pokemon PSA 9", "newlyListed", "FIXED_PRICE")],
            )
        self.assertFalse(status["errors"])
        self.assertEqual(len(alerts), 1)
        self.assertEqual(len(calls), 2)
        self.assertTrue(
            all(url.startswith("https://api.ebay.com/") for _, url in calls)
        )
        self.assertEqual(
            self.store.db.execute("SELECT count(*) FROM ebay_api_usage").fetchone()[0],
            2,
        )
        self.assertEqual(
            sync_into_holy_pokemon(
                discovery_snapshot(self.collector)["leads"], store=self.store
            )["accepted"],
            1,
        )
        with patch(
            "holy_pokemon.app_service.discovery_database", return_value=self.collector
        ):
            state(self.store)
            state(self.store)
        self.assertEqual(
            len(calls), 2, "Dashboard refresh must never request marketplace data"
        )

    def test_cli_sync_uses_selected_app_store_and_preserves_existing_records(self):
        path = self.root / "listings.csv"
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(self.row))
            w.writeheader()
            w.writerow(self.row)
        self.store.put("review", "existing", {"text": "Do not overwrite"})
        with redirect_stdout(io.StringIO()):
            rc = main(
                [
                    "--import-csv",
                    str(path),
                    "--database",
                    str(self.collector),
                    "--app-database",
                    str(self.store.path),
                    "--output",
                    str(self.root / "out"),
                    "--sync-app",
                    "--once",
                ]
            )
        self.assertEqual(rc, 0)
        self.assertEqual(len(self.store.rows("lead")), 1)
        self.assertIsNotNone(self.store.get("review", "existing"))

    def test_api_import_and_sync_actions_work_without_keys(self):
        with patch(
            "holy_pokemon.app_service.discovery_database", return_value=self.collector
        ):
            result = command(self.store, "discovery-import", {"rows": [self.row]})
            self.assertEqual(result["app_sync"]["accepted"], 1)
            self.assertEqual(command(self.store, "discovery-sync", {})["accepted"], 0)

    def test_missing_credentials_never_start_live_job(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaisesRegex(ValueError, "No request was made"):
                command(self.store, "discovery-scan", {})

    def test_feed_path_with_spaces_and_read_only_no_creation(self):
        self.assertEqual(
            discovery_snapshot(self.root / "missing # query.sqlite")["status"],
            "NOT_STARTED",
        )
        self.assertFalse((self.root / "missing # query.sqlite").exists())
        with self.assertRaises(ValueError):
            discovery_snapshot(self.collector, limit=0)

    def test_psa_mismatched_cert_is_not_verified(self):
        r = check(
            "12345678",
            token="SYNTHETIC-token",
            request=lambda *_: {
                "IsValidRequest": True,
                "ServerMessage": "Request successful",
                "PSACert": {"CertNumber": "87654321"},
            },
        )
        self.assertFalse(r["verified"])
