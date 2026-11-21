import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from holy_pokemon.dataset_intake import audit, export_training_manifest, inventory
from holy_pokemon.vision_training import read_manifest


class DatasetIntakeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        for name, color in (("front.jpg", (80, 40, 20)), ("back.jpg", (20, 40, 80))):
            Image.new("RGB", (650, 890), color).save(self.root / name)

    def row(self, **kwargs):
        result = dict(
            specimen_id="cert-10000001", source_id="source-1",
            grader="PSA", grade="8", label_kind="observed_professional_grade",
            outcome_verified="true", outcome_evidence="verified cert record",
            year="1999", game="pokemon", front_path="front.jpg", back_path="back.jpg",
            card_only_verified="true", same_specimen_pair_verified="true",
            pre_buy_visible="true", rights_basis="explicit_permission",
            rights_evidence="recorded permission", exact_card_identity_verified="true"
        )
        result.update(kwargs)
        return result

    def manifest(self, rows):
        path = self.root / "reviewed.csv"
        with path.open("w", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        return path

    def test_valid_pair_bridges_to_existing_trainer(self):
        report = audit(self.manifest([self.row()]), self.root)
        self.assertEqual(report["counts"]["eligible_rows"], 1)
        self.assertEqual(report["eligible"][0]["category"], "primary_vintage")
        self.assertEqual(report["eligible"][0]["image_pair"]["front"]["width"], 650)
        export = export_training_manifest(report, self.root / "train.csv")
        self.assertEqual(export["image_rows"], 2)
        rows, rejected = read_manifest(self.root / "train.csv", "PSA")
        self.assertEqual(len(rows), 2)
        self.assertEqual(rejected, [])
        self.assertEqual({r["physical_specimen_id"] for r in rows}, {"cert-10000001"})

    def test_expected_labels_and_unknown_rights_do_not_enter_training(self):
        report = audit(self.manifest([self.row(
            label_kind="expected_psa_grade", rights_basis="public_website",
            rights_evidence="", pre_buy_visible="false"
        )]), self.root)
        self.assertEqual(report["counts"]["eligible_rows"] if "eligible_rows" in report["counts"] else 0, 0)
        reasons = report["blocked"][0]["reasons"]
        self.assertIn("EXPECTED_OR_UNVERIFIED_GRADE", reasons)
        self.assertIn("TRAINING_RIGHTS_NOT_VERIFIED", reasons)
        self.assertIn("POST_GRADE_OR_NOT_PREBUY_VISIBLE", reasons)
        export = export_training_manifest(report, self.root / "empty.csv")
        self.assertEqual(export["image_rows"], 0)

    def test_path_traversal_blocked(self):
        report = audit(self.manifest([self.row(front_path="../notallowed.jpg")]), self.root)
        self.assertIn("MISSING_OR_UNSAFE_FRONT_FILE", report["blocked"][0]["reasons"])

    def test_identical_front_and_back_blocked(self):
        report = audit(self.manifest([self.row(back_path="front.jpg")]), self.root)
        self.assertIn("DUPLICATE_IMAGE_ACROSS_SPECIMENS_OR_SIDES", report["blocked"][0]["reasons"])

    def test_no_cross_grader_leakage_from_paco_inventory(self):
        path = self.root / "paco.csv"
        path.write_text(
            "filename,overall_grade,surface,corners,edges,centering,source\n"
            "psa8.jpg,8.0,9.4,9.5,9.0,9.8,ebay_psa\n"
            "cgc10.jpg,10.0,9.9,9.8,9.5,9.9,ebay_cgc\n"
            "psa9.jpg,9.0,9.3,9.5,9.4,9.8,ebay_psa\n",
            encoding="utf-8"
        )
        result = inventory("paco", path)
        self.assertEqual(result["counts"]["psa_8_9_10_claim_rows"], 2)
        self.assertEqual(result["eligible_training_rows"], 0)
        self.assertTrue(all(x["authorization"] == "UNVERIFIED" for x in result["candidate_metadata_only"]))

    def test_expected_psa_grades_are_not_ground_truth(self):
        path = self.root / "metadata.csv"
        path.write_text("image_id,expected_psa_grade\n1,10\n2,8\n", encoding="utf-8")
        report = inventory("jyesr", path)
        self.assertEqual(report["rows"], 2)
        self.assertEqual(report["eligible_training_rows"], 0)
        self.assertIn("EXPECTED_PSA_GRADES_ARE_NOT_OBSERVED_PSA_OUTCOMES", report["blocked_reasons"])


if __name__ == "__main__":
    unittest.main()
