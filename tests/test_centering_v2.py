import csv
import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np
from holy_pokemon.centering_v2 import measure_bgr
from holy_pokemon.centering_backtest import run


def specimen(side="front", left=40, right=32, top=38, bottom=38):
    h, w = 980, 700
    border = (25, 25, 220) if side == "front" else (180, 65, 20)
    interior = (180, 60, 40) if side == "front" else (10, 210, 235)
    card = np.full((h, w, 3), border, dtype=np.uint8)
    card[top:h-bottom, left:w-right] = interior
    cv2.rectangle(card, (left+40, top+40), (w-right-40, h-bottom-40), (0, 0, 0), 4)
    return card

QUAD = [[0, 0], [699, 0], [699, 979], [0, 979]]

class CenteringV2Tests(unittest.TestCase):
    def test_known_left_heavy_front_and_vertical_neutral(self):
        result = measure_bgr(specimen(), side="front", layout="yellow_border", outer_quad=QUAD)
        self.assertEqual(result["status"], "MEASURED_NEEDS_VALIDATION", result)
        self.assertGreater(result["ratios"]["left_pct"], 53)
        self.assertLess(result["ratios"]["left_pct"], 58)
        self.assertAlmostEqual(result["ratios"]["top_pct"], 50, delta=2)
        self.assertIsNone(result["psa_grade_prediction"])
        self.assertIsNone(result["validated_psa10_upgrade_probability"])

    def test_known_back_border_offsets(self):
        result = measure_bgr(specimen("back", 30, 30, 40, 30),
                             side="back", layout="blue_back", outer_quad=QUAD)
        self.assertEqual(result["status"], "MEASURED_NEEDS_VALIDATION", result)
        self.assertAlmostEqual(result["ratios"]["left_pct"], 50, delta=2)
        self.assertGreater(result["ratios"]["top_pct"], 55)

    def test_unmodeled_full_art_abstains_not_fake_5050(self):
        image = np.full((980, 700, 3), (100, 80, 95), dtype=np.uint8)
        result = measure_bgr(image, side="front", layout="auto", outer_quad=QUAD)
        self.assertEqual(result["status"], "ABSTAIN")
        self.assertEqual(result["reason"], "unsupported_layout_requires_reference")
        self.assertIsNone(result["ratios"])

    def test_no_card_and_low_resolution_abstain(self):
        self.assertEqual(measure_bgr(np.zeros((980, 700, 3), np.uint8),
                                     side="front")["status"], "ABSTAIN")
        image = cv2.resize(specimen(), (175, 245))
        self.assertEqual(measure_bgr(image, side="front")["reason"], "low_resolution")

    def test_saved_universe_and_resume_no_original_modification(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            images = root / "images"
            images.mkdir()
            original = []
            for name, side in [("a-front", "front"), ("a-back", "back"), ("b-front", "front")]:
                p = images / (name + ".png")
                cv2.imwrite(str(p), specimen(side))
                original.append((p, p.read_bytes()))
            audit = root / "audit.csv"
            with audit.open("w", newline="") as stream:
                writer = csv.DictWriter(stream, fieldnames=["listing_id", "recorded_ask"])
                writer.writeheader()
                for id, ask in [("a", "150"), ("b", "650"), ("c", "")]:
                    writer.writerow({"listing_id": id, "recorded_ask": ask})
            manifest = root / "photos.jsonl"
            with manifest.open("w") as stream:
                for name, side in [("a-front", "front"), ("a-back", "back"), ("b-front", "front")]:
                    stream.write(json.dumps({"listing_id": name[0], "side": side,
                        "path": name + ".png", "outer_quad": QUAD,
                        "layout": "yellow_border" if side == "front" else "blue_back"}) + "\n")
            output = root / "output"
            first = run(audit, images, output, photo_manifest=manifest, expected=3)
            self.assertEqual(first["listing_count"], 3)
            self.assertEqual(first["stats"]["DUAL_FACE_MEASURED_UNCALIBRATED"], 1)
            self.assertEqual(first["stats"]["REQUIRES_GEOMETRY_REVIEW"], 2)
            self.assertEqual(first["stats"]["BUDGET_UNDER_500"], 1)
            self.assertEqual(first["stats"]["PREMIUM_EXCEPTION_REQUIRES_INDEPENDENT_EVIDENCE"], 1)
            data = json.loads((output / "report.json").read_text())
            self.assertIsNone(data["records"]["a"]["risk_adjusted_roi"])
            self.assertFalse(data["records"]["a"]["trade_approved"])
            self.assertEqual(len(list((output / "measurement_cache").glob("*.json"))), 3)
            second = run(audit, images, output, photo_manifest=manifest, expected=3)
            self.assertEqual(first["stats"], second["stats"])
            self.assertEqual(len(list((output / "measurement_cache").glob("*.json"))), 3)
            for p, before in original:
                self.assertEqual(p.read_bytes(), before)
            with self.assertRaisesRegex(ValueError, "Expected 645"):
                run(audit, images, output, photo_manifest=manifest, expected=645)

    def test_manifest_prevents_path_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "images").mkdir()
            (root / "audit.csv").write_text("listing_id,recorded_ask\na,150\n")
            (root / "manifest.jsonl").write_text(
                json.dumps({"listing_id":"a","side":"front","path":"../outside.png"}) + "\n")
            with self.assertRaisesRegex(ValueError, "outside --image-root"):
                run(root / "audit.csv", root / "images", root / "out",
                    photo_manifest=root / "manifest.jsonl", expected=1)

if __name__ == "__main__":
    unittest.main()
