import unittest
from holy_pokemon.video_evidence import clock_points, interpolate
from holy_pokemon.market import sales_summary
from holy_pokemon.vault_workflow import compare_exits
from holy_pokemon.vault_engine import reconcile_payout, psa_consignment_net


class VideoAndGuards(unittest.TestCase):
    def test_recorder_clock_interpolates_pauses_not_assumed_three_x(self):
        m = {
            "captureStartMs": 1000,
            "clockSync": [
                {"wallMs": 1000, "videoTime": 0},
                {"wallMs": 11000, "videoTime": 30},
                {"wallMs": 21000, "videoTime": 30},
                {"wallMs": 31000, "videoTime": 60},
            ],
        }
        points = clock_points(m)
        self.assertEqual(interpolate(points, 25), 45)
        self.assertEqual(interpolate(points, 45, reverse=True), 25)

    def test_timestamp_outside_capture_is_rejected(self):
        with self.assertRaises(ValueError):
            interpolate([(0, 0), (10, 30)], 60, reverse=True)

    def test_no_sync_no_temporal_claim(self):
        with self.assertRaises(ValueError):
            clock_points({"captureStartMs": 0, "clockSync": []})

    def test_pristine_and_legacy_label_cannot_mix(self):
        identity = {
            "game": "pokemon",
            "set": "Neo",
            "number": "1",
            "name": "Card",
            "language": "English",
            "edition": "unlimited",
            "finish": "holo",
        }
        self.assertEqual(
            sales_summary([], identity, grader="CGC", grade="10")["status"],
            "DESIGNATION_REQUIRED",
        )
        self.assertEqual(
            sales_summary([], identity, grader="CGC", grade="9.5")["status"],
            "CGC_LABEL_ERA_REQUIRED",
        )

    def test_no_receipt_no_realized_cash_and_nonfinite_fee(self):
        self.assertIsNone(
            reconcile_payout(
                gross="200", psa_fee="26", actual_payout="174", card_id="fixture"
            )["realized_cash"]
        )
        with self.assertRaises(ValueError):
            psa_consignment_net("NaN")

    def test_offer_amount_is_required_and_grade_to_vault_is_costed(self):
        b = {
            "asof": "2026-10-29",
            "vaulted_at": "2026-01-01",
            "basis": "100",
            "sale_price": "200",
            "psa_fee_pct": "13",
            "tax": "0",
            "grading": "20",
            "grading_shipping": "10",
            "insurance": "0",
            "upcharge": "0",
            "regrade_exit": "300",
            "offer_evidence": "private quote",
            "offer_expires": "2026-10-30",
        }
        r = compare_exits(b)
        self.assertIsNone(r["offer"]["net"])
        grade = next(x for x in r["routes"] if x["route"] == "grade_to_vault")
        self.assertEqual(grade["net_proceeds"], "231.00")
