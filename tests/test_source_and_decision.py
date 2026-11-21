import csv
import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from holy_pokemon.store import Store, ROOT
from holy_pokemon.market import import_rows
from holy_pokemon.decision import review_candidate
from holy_pokemon.ingest import import_transport


class DecisionAndTransport(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.tmp.name) / "test.sqlite")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_nested_transport_provenance_and_idempotency(self):
        manifest = list(csv.DictReader((ROOT / "research/manifest.csv").open()))
        records = []
        for pack in manifest:
            for i in range(int(pack["structured_case_rows"])):
                records.append(
                    {
                        "source_archive": pack["canonical_zip_name"],
                        "archive_sha256": pack["sha256"],
                        "member_path": "card_cases.csv",
                        "row_number": i + 1,
                        "source_row": {"name": f"SYNTHETIC SCHEMA FIXTURE {i}"},
                    }
                )
        inner = io.BytesIO()
        with zipfile.ZipFile(inner, "w") as z:
            z.writestr(
                "source_case_rows.jsonl", "\n".join(json.dumps(r) for r in records)
            )
        path = Path(self.tmp.name) / "nested.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr("structured/canonical.zip", inner.getvalue())
        result = import_transport(self.store, path)
        self.assertEqual(result["added"], 250)
        self.assertEqual(import_transport(self.store, path)["added"], 0)
        self.assertEqual(
            sum(r["game"] == "one_piece" for r in self.store.rows("source_record")), 20
        )
        self.assertEqual(self.store.rows("specimen"), [])

    def test_full_manual_readiness_and_budget_recheck(self):
        identity = {
            "game": "pokemon",
            "set": "Expedition",
            "number": "62",
            "denominator": "165",
            "name": "Rapidash",
            "year": "2002",
            "language": "English",
            "edition": "unlimited",
            "finish": "nonholo",
        }
        import_rows(
            self.store,
            "lead",
            [
                {
                    **identity,
                    "title": "SYNTHETIC readiness fixture",
                    "listing_id": "lead1",
                    "source_url": "https://www.ebay.com/itm/12345",
                    "observed_at": "2026-10-28",
                    "ask": "100",
                }
            ],
        )
        lead = self.store.rows("lead")[0]
        for i, grade in enumerate(("10", "10", "10", "9")):
            r = {
                **identity,
                "transaction_id": f"fixture{i}",
                "price": "300",
                "currency": "USD",
                "grader": "PSA",
                "grade": grade,
                "sale_date": "2026-10-20",
                "observed_at": "2026-10-28",
                "source_url": f"https://www.ebay.com/itm/{12345 + i}",
                "evidence_kind": "completed_sale",
                "exact_variant_verified": True,
            }
            import_rows(self.store, "sale", [r])
        zeros = {
            k: "0"
            for k in (
                "grading",
                "grading_shipping",
                "grading_insurance",
                "upcharge",
                "outbound_shipping",
                "vault_withdrawal",
                "vault_early_fee",
                "vault_consignment_fixed",
                "holding_cost",
                "contingency",
            )
        }
        body = {
            "lead_id": lead["id"],
            "identity": identity,
            "identity_confirmed": True,
            "seller_verified": True,
            "photos_reviewed": True,
            "seller_evidence": "SYNTHETIC fixture source",
            "front_evidence": "fixture front",
            "back_evidence": "fixture back",
            "condition_notes": "fixture notes",
            "exit_grader": "PSA",
            "exit_grade": "10",
            "original_grader": "PSA",
            "original_grade": "9",
            "scenario": {
                "listing": {
                    "ask": "100",
                    "buyer_shipping": "0",
                    "purchase_tax": "0",
                    "buyer_premium": "0",
                },
                "routes": [
                    {**zeros, "route": name, "exit_price": value, "fee_pct": "10"}
                    for name, value in (
                        ("sell_original", "150"),
                        ("crack_psa_10", "300"),
                        ("crack_psa_8", "80"),
                    )
                ],
            },
        }
        result = review_candidate(self.store, body)
        self.assertEqual(result["approval"], "MANUAL_BUY_READY")
        self.assertFalse(result["purchase_authorized"])
        import_rows(
            self.store,
            "holding",
            [
                {
                    "item_id": "fixture-owned",
                    "state": "owner_possession",
                    "all_in_cost": "1950",
                    "source_url": "https://www.ebay.com/itm/12345",
                    "observed_at": "2026-10-28",
                }
            ],
        )
        result = review_candidate(self.store, body, persist=False)
        self.assertEqual(result["approval"], "NEED_MORE_EVIDENCE")

    def test_documented_spread_anchors_are_not_cash(self):
        # Contract anchors, not a claim that missing original packs were ingested.
        anchors = [
            ("15359", "27533", "12174"),
            ("7377", "10895", "3518"),
            ("7963", "12170", "4207"),
            ("11333", "15425", "4092"),
            ("2719", "6235", "3516"),
            ("12469", "19715", "7246"),
            ("11161", "19160", "7999"),
            ("6328", "12370", "6042"),
        ]
        from decimal import Decimal as D

        for cost, value, spread in anchors:
            self.assertEqual(D(value) - D(cost), D(spread))

    def test_real_may_sales_reconcile_and_distinct_reshiram(self):
        path = (
            Path.home() / "Downloads/Fredy_May_DIRECT_Research_Pack_V2_Recaptured.zip"
        )
        if not path.is_file():
            self.skipTest("Original private May source not mounted")
        from decimal import Decimal as D

        with zipfile.ZipFile(path) as z:
            rows = list(
                csv.DictReader(
                    io.StringIO(z.read("structured/card_cases.csv").decode("utf-8-sig"))
                )
            )
        sold = [r for r in rows if r["stage"] in ("sold", "sold_loss")]
        for row in sold:
            self.assertEqual(
                D(row["revenue"])
                - D(row["cost"])
                - D(row["fees"])
                - D(row["shipping"]),
                D(row["profit"]),
            )
        copies = [r for r in sold if r["name"].startswith("N's Reshiram")]
        self.assertEqual(len(copies), 2)
        self.assertNotEqual(copies[0]["final_cert"], copies[1]["final_cert"])
