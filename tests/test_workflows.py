"""Regression tests for source integrity, exact comps and full manual Vault lifecycle."""

import io
import tempfile
import unittest
import zipfile
from datetime import date
from pathlib import Path
from holy_pokemon.store import Store
from holy_pokemon.ingest import safe_members, normalize
from holy_pokemon.market import import_rows, sales_summary, csv_export, rank_leads
from holy_pokemon.vault_workflow import (
    collection,
    record_transition,
    record_payout,
    compare_exits,
)
from holy_pokemon.psa_cert import PSACertificateAdapter
from holy_pokemon.evaluation import connected_split, metrics


class Workflows(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.sqlite")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def holding(self):
        r = {
            "item_id": "owned-1",
            "name": "Example owned copy",
            "grader": "PSA",
            "cert": "12345678",
            "state": "vaulted",
            "source_url": "https://www.psacard.com/info/psa-vault",
            "observed_at": "2026-10-28",
            "ebay_item_id": "listing-1",
            "provider": "psa_vault",
        }
        self.assertEqual(import_rows(self.store, "holding", [r])["accepted"], 1)
        return self.store.rows("holding")[0]

    def sale(self):
        return {
            "transaction_id": "sale1",
            "evidence_kind": "completed_sale",
            "source_url": "https://www.ebay.com/itm/123",
            "observed_at": "2026-10-28",
            "sale_date": "2026-10-01",
            "price": "200",
            "currency": "USD",
            "provider": "ebay",
            "game": "pokemon",
            "set": "Expedition",
            "number": "62",
            "denominator": "165",
            "name": "Rapidash",
            "year": "2002",
            "language": "English",
            "edition": "unlimited",
            "finish": "nonholo",
            "grader": "PSA",
            "grade": "10",
            "exact_variant_verified": "true",
        }

    def test_store_immutable_append_only(self):
        self.store.put("review", "a", {"text": "first"})
        with self.assertRaises(ValueError):
            self.store.put("review", "a", {"text": "changed"})

    def test_sales_idempotent_and_mirror_dedup(self):
        r = self.sale()
        self.assertEqual(import_rows(self.store, "sale", [r, r])["accepted"], 1)
        r = {**r, "transaction_id": "mirror", "cert": "cert1"}
        self.assertEqual(import_rows(self.store, "sale", [r])["accepted"], 1)
        r["transaction_id"] = "mirror2"
        self.assertEqual(import_rows(self.store, "sale", [r])["duplicates"], 1)

    def test_active_ask_cannot_enter_sold(self):
        r = self.sale()
        r["evidence_kind"] = "active_ask"
        self.assertEqual(import_rows(self.store, "sale", [r])["accepted"], 0)

    def test_rapidash_exact_finish_and_time(self):
        r = self.sale()
        import_rows(self.store, "sale", [r])
        sales = self.store.rows("sale")
        self.assertEqual(
            sales_summary(sales, r, asof=date(2026, 10, 28), grader="PSA", grade="10")[
                "count"
            ],
            1,
        )
        self.assertEqual(
            sales_summary(sales, {**r, "finish": "reverse"}, asof=date(2026, 10, 28))[
                "count"
            ],
            0,
        )
        self.assertEqual(
            sales_summary(sales, {**r, "number": "26"}, asof=date(2026, 10, 28))[
                "count"
            ],
            0,
        )
        self.assertEqual(sales_summary(sales, r, asof=date(2026, 9, 30))["count"], 0)

    def test_missing_comp_keeps_research_visible(self):
        r = {
            "listing_id": "rapidash",
            "title": "Rapidash #62 nonholo blue CGC 9.5",
            "source_url": "https://www.ebay.com/itm/123",
            "observed_at": "2026-10-28",
            "ask": "82.95",
            "possible_best_exit": "500",
            "exact_variant_verified": "false",
        }
        import_rows(self.store, "lead", [r])
        leads = rank_leads(self.store)
        self.assertTrue(leads[0]["research_visible"])
        self.assertEqual(leads[0]["approval"], "NEED_MORE_EVIDENCE")

    def test_csv_formula_injection_escaped(self):
        self.assertIn("'=HYPERLINK", csv_export([{"name": '=HYPERLINK("x")'}]))

    def test_zip_traversal_rejected(self):
        b = io.BytesIO()
        with zipfile.ZipFile(b, "w") as z:
            z.writestr("../escape.txt", "bad")
        with zipfile.ZipFile(b) as z:
            with self.assertRaises(ValueError):
                safe_members(z)

    def test_independent_same_name_certs_not_merged(self):
        a = self.holding()
        r = {**a, "item_id": "owned2", "cert": "87654321"}
        r.pop("id")
        self.assertEqual(import_rows(self.store, "holding", [r])["accepted"], 1)
        self.assertEqual(len(collection(self.store)), 2)

    def test_full_vault_owner_lifecycle_no_remote_action(self):
        h = self.holding()
        for n, status in enumerate(
            (
                "consigned",
                "listed_auction",
                "sold_unpaid",
                "sold_paid",
                "payout_pending",
            )
        ):
            result = record_transition(
                self.store,
                {
                    "holding_id": h["id"],
                    "to": status,
                    "user_confirmed": True,
                    "source_ref": "official-account-evidence",
                    "event_at": f"2026-10-28T{n:02}:00:00",
                },
            )
            self.assertFalse(result["remote_action_executed"])
        self.assertTrue(collection(self.store)[0]["unpaid"])
        result = record_payout(
            self.store,
            {
                "holding_id": h["id"],
                "receipt_ref": "stripe1",
                "listing_id": "listing-1",
                "paid_at": "2026-10-28",
                "gross": "200",
                "psa_fee": "26",
                "actual_payout": "174",
                "receipt_verified": True,
            },
        )
        self.assertEqual(result["status"], "RECONCILED")
        self.assertEqual(collection(self.store)[0]["realized_cash"], "174")

    def test_receipt_duplicate_and_listing_mismatch(self):
        h = self.holding()
        p = {
            "holding_id": h["id"],
            "receipt_ref": "stripe1",
            "listing_id": "wrong",
            "paid_at": "2026-10-28",
            "gross": "200",
            "psa_fee": "26",
            "actual_payout": "174",
            "receipt_verified": True,
        }
        with self.assertRaises(ValueError):
            record_payout(self.store, p)
        p["listing_id"] = "listing-1"
        record_payout(self.store, p)
        with self.assertRaises(ValueError):
            record_payout(self.store, p)

    def test_vault_status_requires_human_evidence(self):
        h = self.holding()
        with self.assertRaises(PermissionError):
            record_transition(
                self.store,
                {
                    "holding_id": h["id"],
                    "to": "consigned",
                    "source_ref": "x",
                    "event_at": "2026-10-28",
                    "user_confirmed": False,
                },
            )

    def test_compare_withdrawal_precedes_regrade(self):
        b = {
            "asof": "2026-10-29",
            "vaulted_at": "2026-10-01",
            "basis": "100",
            "sale_price": "200",
            "psa_fee_pct": "13",
            "tax": "0",
            "own_fee_pct": "10",
            "sale_shipping": "5",
            "contingency": "0",
            "grading": "20",
            "grading_shipping": "10",
            "insurance": "0",
            "upcharge": "0",
            "regrade_exit": "300",
        }
        r = compare_exits(b)
        self.assertEqual(r["withdrawal"]["total"], "24.98")
        routes = {x["route"]: x for x in r["routes"]}
        self.assertEqual(routes["psa_bin"]["net_proceeds"], "174.00")
        self.assertEqual(routes["withdraw_regrade"]["net_proceeds"], "210.02")
        self.assertIsNone(routes["hold"]["profit_if_sold"])
        b["asof"] = "2026-10-28"
        self.assertIsNone(compare_exits(b)["withdrawal"]["total"])

    def test_partner_offer_expiry_and_no_hypothetical_offer(self):
        b = {
            "asof": "2026-10-29",
            "vaulted_at": "2026-01-01",
            "sale_price": "200",
            "offer_amount": "180",
        }
        self.assertIsNone(compare_exits(b)["offer"]["net"])
        b.update(offer_expires="2026-10-28", offer_evidence="actual-owner-offer")
        self.assertIsNone(compare_exits(b)["offer"]["net"])
        b["offer_expires"] = "2026-10-30"
        self.assertEqual(compare_exits(b)["offer"]["net"], "180.00")

    def test_no_cert_token_never_verified(self):
        self.assertFalse(
            PSACertificateAdapter(self.store, token="").verify("12345678")[
                "cert_verified"
            ]
        )

    def test_cert_mock_identity_and_cached(self):
        calls = []

        def request(cert):
            calls.append(cert)
            return {
                "ServerMessage": "Request successful",
                "PSACert": {"CertNumber": cert, "CardGrade": "9"},
            }

        adapter = PSACertificateAdapter(
            self.store, token="fixture-not-real", request=request
        )
        self.assertTrue(adapter.verify("12345678")["cert_verified"])
        adapter.verify("12345678")
        self.assertEqual(len(calls), 1)

    def test_connected_video_card_and_swapped_photo_groups(self):
        rows = [
            {
                "physical_specimen_id": f"card{i}",
                "source_video_id": f"v{i}",
                "sha256": f"img{i}",
            }
            for i in range(10)
        ]
        rows[0]["back_sha256"] = "img9"
        rows[1]["cert"] = "same"
        rows[8]["cert"] = "same"
        parts = connected_split(rows)
        assignment = {
            r["physical_specimen_id"]: k for k, rr in parts.items() for r in rr
        }
        self.assertEqual(assignment["card0"], assignment["card9"])
        self.assertEqual(assignment["card1"], assignment["card8"])

    def test_metrics_psa10_false_positive_and_severity(self):
        r = metrics([0, 1, 2], [2, 1, 2], ["8", "9", "10"], "PSA")
        self.assertEqual(r["psa10_false_positives"], 1)
        self.assertEqual(r["psa10_false_positive_rate"], 0.5)
        self.assertEqual(r["grade_mae"], 2 / 3)
        self.assertIsNone(r["financial_backtest"]["net"])

    def test_unknown_fields_and_pristine_preserved(self):
        r = normalize({"name": "Azumarill", "final_grade": "CGC Pristine 10"})
        self.assertEqual(r["reported_final_grade"], "CGC Pristine 10")
        self.assertIsNone(r["specimen_id"])


class RepeatedGradingRegression(unittest.TestCase):
    def test_same_owned_copy_keeps_both_attempts_and_actual_costs(self):
        from holy_pokemon.vault_workflow import record_grading_event

        with (
            tempfile.TemporaryDirectory() as d,
            Store(Path(d) / "test.sqlite") as store,
        ):
            import_rows(
                store,
                "holding",
                [
                    {
                        "item_id": "same-copy",
                        "name": "SYNTHETIC fixture",
                        "state": "owner_possession",
                        "all_in_cost": "100",
                        "source_url": "https://example.com/receipt",
                        "observed_at": "2026-10-28",
                    }
                ],
            )
            h = store.rows("holding")[0]
            for n, grade in enumerate(("9", "Pristine 10")):
                record_grading_event(
                    store,
                    {
                        "holding_id": h["id"],
                        "event_id": f"fixture-attempt-{n}",
                        "grader": "CGC",
                        "grade": grade,
                        "event_at": "2026-10-28",
                        "source_ref": "SYNTHETIC outcome receipt",
                        "outcome_verified": True,
                        "paid_fee": "25",
                        "fee_payment_verified": True,
                    },
                )
            rows = collection(store)
            self.assertEqual(len(rows), 1)
            self.assertEqual(
                sum(e["type"] == "grading_result" for e in rows[0]["grading_history"]),
                2,
            )
            self.assertEqual(rows[0]["additional_recorded_cash_spent"], "50.00")
            self.assertEqual(rows[0]["latest_observed_grade"]["grade"], "Pristine 10")

    def test_grade_eleven_and_unverified_result_are_rejected(self):
        from holy_pokemon.vault_workflow import record_grading_event

        with (
            tempfile.TemporaryDirectory() as d,
            Store(Path(d) / "test.sqlite") as store,
        ):
            import_rows(
                store,
                "holding",
                [
                    {
                        "item_id": "same-copy",
                        "state": "owner_possession",
                        "source_url": "https://example.com/receipt",
                        "observed_at": "2026-10-28",
                    }
                ],
            )
            h = store.rows("holding")[0]
            with self.assertRaises(ValueError):
                record_grading_event(
                    store,
                    {
                        "holding_id": h["id"],
                        "grader": "CGC",
                        "grade": "11",
                        "event_id": "bad",
                        "event_at": "2026-10-28",
                        "source_ref": "fixture",
                        "outcome_verified": True,
                    },
                )


class ConcurrentStoreRegression(unittest.TestCase):
    def test_concurrent_identical_import_has_one_observation(self):
        from concurrent.futures import ThreadPoolExecutor

        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "shared.sqlite"
            with Store(path):
                pass

            def write(_):
                with Store(path) as store:
                    return store.put(
                        "review", "shared", {"text": "SYNTHETIC concurrent fixture"}
                    )

            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(write, range(4)))
            self.assertEqual(sum(results), 1)
            with Store(path) as store:
                self.assertEqual(len(store.rows("review")), 1)
