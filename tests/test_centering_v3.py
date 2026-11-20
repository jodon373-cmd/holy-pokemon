import unittest

from holy_pokemon.centering_v3 import (
    HAS_CV2,
    centering_eligibility,
    compute_ratios,
    keystone_distortion_score,
    quad_bbox_iou,
)

if HAS_CV2:
    import cv2
    import numpy as np
    from holy_pokemon.centering_v3 import measure_bgr


def _synthetic_card(side="front", border=(25, 215, 225), interior=(180, 60, 40), left=40, right=32, top=38, bottom=38):
    h, w = 980, 700
    card = np.full((h, w, 3), border, dtype=np.uint8)
    card[top:h - bottom, left:w - right] = interior
    cv2.rectangle(card, (left + 40, top + 40), (w - right - 40, h - bottom - 40), (0, 0, 0), 4)
    return card


class CenteringV3PureMathTests(unittest.TestCase):
    def test_compute_ratios_and_eligibility_bands(self):
        front = compute_ratios(52.0, 48.0, 51.0, 49.0)
        back = compute_ratios(60.0, 40.0, 55.0, 45.0)
        self.assertEqual(front["worst_pct"], 52.0)
        elig = centering_eligibility(front, back)
        self.assertIsNone(elig["grade_prediction"])
        self.assertTrue(elig["bands"]["psa_10_centering_band"])
        self.assertTrue(elig["bands"]["cgc_gem_10_centering_band"])
        self.assertTrue(elig["bands"]["bgs_9_5_centering_band"])
        self.assertFalse(elig["bands"]["cgc_pristine_10_centering_band"])
        self.assertGreater(elig["centering_score"], 80.0)

    def test_off_center_front_fails_psa10_band(self):
        front = compute_ratios(62.0, 38.0, 50.0, 50.0)
        elig = centering_eligibility(front, compute_ratios(50.0, 50.0, 50.0, 50.0))
        self.assertFalse(elig["bands"]["psa_10_centering_band"])
        self.assertFalse(elig["bands"]["psa_9_centering_band"])

    def test_keystone_distortion_and_quad_iou(self):
        rect = [[0, 0], [100, 0], [100, 140], [0, 140]]
        self.assertEqual(keystone_distortion_score(rect), 0.0)
        skewed = [[10, 0], [90, 0], [120, 140], [0, 140]]
        self.assertGreater(keystone_distortion_score(skewed), 0.30)
        self.assertEqual(quad_bbox_iou(rect, rect), 1.0)
        self.assertEqual(quad_bbox_iou(rect, [[200, 200], [300, 200], [300, 340], [200, 340]]), 0.0)


@unittest.skipUnless(HAS_CV2, "opencv-python-headless and numpy required for CV image tests")
class CenteringV3VisionTests(unittest.TestCase):
    QUAD = [[0, 0], [699, 0], [699, 979], [0, 979]]

    def test_silver_border_modern_card_measured(self):
        # Light-silver border (high V, low S) with dark interior
        img = _synthetic_card(border=(215, 215, 215), interior=(60, 40, 160), left=42, right=34, top=38, bottom=38)
        res = measure_bgr(img, side="front", layout="auto", outer_quad=self.QUAD)
        self.assertEqual(res["status"], "MEASURED_NEEDS_VALIDATION", res)
        self.assertEqual(res["layout"], "silver_border")
        self.assertGreater(res["ratios"]["left_pct"], 53.0)
        self.assertIsNone(res["psa_grade_prediction"])

    def test_blurry_image_abstains(self):
        img = _synthetic_card()
        blur = cv2.GaussianBlur(img, (35, 35), 15)
        res = measure_bgr(blur, side="front", outer_quad=self.QUAD)
        self.assertEqual(res["status"], "ABSTAIN")
        self.assertEqual(res["reason"], "image_too_blurry")

    def test_severe_keystone_abstains(self):
        img = _synthetic_card()
        skewed = [[120, 40], [560, 40], [680, 940], [20, 940]]
        res = measure_bgr(img, side="front", outer_quad=skewed)
        self.assertEqual(res["status"], "ABSTAIN")
        self.assertEqual(res["reason"], "severe_perspective_distortion")


if __name__ == "__main__":
    unittest.main()
