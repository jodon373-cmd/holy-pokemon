import csv
import tempfile
import unittest
from pathlib import Path
from holy_pokemon.vision_training import read_manifest, split_by_video


class VisionManifestTests(unittest.TestCase):
    def write_manifest(self, path, rows):
        with path.open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)

    def test_leakage_and_permissions_block_training(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            image = d / "card.png"
            image.write_bytes(b"source bytes placeholder")
            rows = [
                {
                    "grader": "PSA",
                    "grade": "10",
                    "rights_basis": "self_photographed",
                    "rights_evidence": "photographer consent record",
                    "card_only_verified": "no",
                    "pre_decision_visible": "yes",
                    "source_video_id": "video1",
                    "physical_specimen_id": "copy1",
                    "image_path": str(image),
                }
            ]
            m = d / "m.csv"
            self.write_manifest(m, rows)
            accepted, rejected = read_manifest(m, "PSA")
            self.assertEqual(len(accepted), 0)
            self.assertIn(
                "unverified_card_only_crop_label_leakage_risk", rejected[0]["reasons"]
            )
            rows[0]["card_only_verified"] = "yes"
            rows[0]["rights_evidence"] = ""
            self.write_manifest(m, rows)
            self.assertEqual(len(read_manifest(m, "PSA")[0]), 0)

    def test_same_copy_across_videos_cannot_train(self):
        rows = [
            {"physical_specimen_id": "A", "source_video_id": f"v{i}"} for i in range(8)
        ]
        rows[0]["physical_specimen_id"] = "same"
        rows[7]["physical_specimen_id"] = "same"
        with self.assertRaises(ValueError):
            split_by_video(rows, seed=73)

    def test_requires_multiple_source_videos(self):
        with self.assertRaises(ValueError):
            split_by_video([{"physical_specimen_id": "A", "source_video_id": "v1"}])


if __name__ == "__main__":
    unittest.main()
