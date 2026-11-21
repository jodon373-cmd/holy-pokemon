import tempfile
import unittest
from pathlib import Path
from holy_pokemon.inventory import InventoryLedger


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = InventoryLedger(Path(self.tmp.name) / "ledger.sqlite")
        self.db.add_specimen(
            "copy1",
            "Fossil Articuno 1st Ed holo",
            "source:video1",
            grader="PSA",
            grade="9",
            cert="cert1",
        )

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_two_grades_one_physical_copy(self):
        self.db.event(
            "grade1",
            "copy1",
            "grading_result",
            "source:result1",
            grader="CGC",
            grade="9",
        )
        self.db.event(
            "grade2",
            "copy1",
            "grading_result",
            "source:result2",
            grader="CGC",
            grade="9",
        )
        out = self.db.financials("copy1")
        self.assertEqual(out["grading_events"], 2)
        self.assertEqual(out["latest_grade"], {"grader": "CGC", "grade": "9"})

    def test_creator_sale_claim_not_cash(self):
        self.db.event(
            "sale1", "copy1", "sale_reported", "video:timestamp", amount="500"
        )
        self.assertEqual(self.db.financials("copy1")["receipt_verified_cash_in"], "0")

    def test_cash_needs_receipt_and_dedup(self):
        self.db.event(
            "buy1", "copy1", "purchase_confirmed", "seller_invoice", amount="250"
        )
        with self.assertRaises(ValueError):
            self.db.event(
                "paid", "copy1", "payout_received", "creator_says_paid", amount="300"
            )
        self.db.event(
            "paid",
            "copy1",
            "payout_received",
            "bank_receipt",
            amount="300",
            details={"receipt_verified": True},
        )
        self.assertEqual(self.db.financials("copy1")["actual_cash_net"], "50.00")
        with self.assertRaises(Exception):
            self.db.event(
                "paid",
                "copy1",
                "payout_received",
                "bank_receipt",
                amount="300",
                details={"receipt_verified": True},
            )

    def test_reject_unknown_grade_and_no_real_knowledge(self):
        with self.assertRaises(ValueError):
            self.db.event("grading", "copy1", "grading_result", "video1")
        with self.assertRaises(ValueError):
            self.db.event(
                "weird", "copy1", "automated_purchase", "source1", amount="50"
            )


if __name__ == "__main__":
    unittest.main()
