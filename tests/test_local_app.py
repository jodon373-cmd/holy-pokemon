import base64
import hashlib
import io
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from unittest.mock import patch
from holy_pokemon.dashboard import Handler, LOCAL_TOKEN
from holy_pokemon.store import Store
from holy_pokemon.app_service import command
from holy_pokemon.business_ops import retry_analysis, venue_comparison


class LocalApp(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)

        class TestHandler(Handler):
            database = self.path / "test.sqlite"

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), TestHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_address[1]}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def post(self, path, data, token=True, origin=None):
        headers = {"Content-Type": "application/json"}
        if token:
            headers["X-Holy-Local"] = LOCAL_TOKEN
        if origin:
            headers["Origin"] = origin
        with urlopen(
            Request(self.base + path, json.dumps(data).encode(), headers), timeout=5
        ) as r:
            return json.load(r)

    def test_cross_origin_and_missing_token_writes_rejected(self):
        with self.assertRaises(HTTPError) as x:
            self.post("/api/note", {"subject": "x", "text": "bad"}, False)
        self.assertEqual(x.exception.code, 403)
        with self.assertRaises(HTTPError) as x:
            self.post(
                "/api/note",
                {"subject": "x", "text": "bad"},
                origin="https://attacker.invalid",
            )
        self.assertEqual(x.exception.code, 403)

    def test_state_notes_and_formula_safe_export(self):
        result = self.post(
            "/api/note", {"subject": "test source", "text": '=HYPERLINK("example")'}
        )
        self.assertTrue(result["saved"])
        with urlopen(self.base + "/api/state") as r:
            state = json.load(r)
            self.assertEqual(state["counts"]["review"], 1)
            self.assertFalse(state["automatic_purchases"])
        with urlopen(self.base + "/api/export?kind=review") as r:
            self.assertIn("'=HYPERLINK", r.read().decode())

    def test_new_ui_and_classic_both_work(self):
        for endpoint in ("/", "/classic", "/static/app.js", "/static/style.css"):
            with urlopen(self.base + endpoint) as r:
                self.assertEqual(r.status, 200)

    def test_no_training_labels_is_actionable_error(self):
        with self.assertRaises(HTTPError) as x:
            self.post("/api/train", {"grader": "PSA", "epochs": 1})
        self.assertIn("No curated training labels", x.exception.read().decode())

    def test_missing_model_abstains(self):
        with patch("holy_pokemon.app_service.ROOT", self.path):
            r = self.post("/api/infer", {"id": "missing"})
        self.assertEqual(r["status"], "ABSTAIN")

    def test_original_image_crop_and_defect_append(self):
        try:
            from PIL import Image
        except ImportError:
            self.skipTest("Pillow optional local image runtime")
        im = Image.new("RGB", (600, 800), "grey")
        out = io.BytesIO()
        im.save(out, "PNG")
        raw = out.getvalue()
        with (
            Store(self.path / "images.sqlite") as store,
            patch("holy_pokemon.app_service.ROOT", self.path),
        ):
            result = command(
                store,
                "upload",
                {"name": "original.png", "base64": base64.b64encode(raw).decode()},
            )
            original = store.assets()[0]["path"]
            sha = hashlib.sha256(Path(original).read_bytes()).hexdigest()
            crop = command(
                store,
                "crop",
                {
                    "id": result["id"],
                    "box": [10, 100, 500, 700],
                    "card_only_verified": True,
                },
            )
            self.assertEqual(
                sha, hashlib.sha256(Path(original).read_bytes()).hexdigest()
            )
            self.assertNotEqual(crop["path"], original)
            command(
                store,
                "annotation",
                {
                    "id": result["id"],
                    "defect": "scratches",
                    "visibility": "unknown",
                    "region": "foil",
                    "severity": "unknown",
                },
            )
            self.assertEqual(len(store.rows("review")), 2)

    def test_unreviewed_crop_and_bad_images_rejected(self):
        with (
            Store(self.path / "images.sqlite") as store,
            patch("holy_pokemon.app_service.ROOT", self.path),
        ):
            with self.assertRaises(ValueError):
                command(
                    store,
                    "upload",
                    {
                        "name": "bad.jpg",
                        "base64": base64.b64encode(b"not an image").decode(),
                    },
                )

    def test_retry_and_venue_carry_cost(self):
        r = retry_analysis("200", "400", "150", "50")
        self.assertEqual(r["retry_failure_incremental"], "-100.00")
        self.assertIsNone(r["measured_success_probability"])
        body = {
            "basis": "100",
            "annual_capital_pct": "10",
            "venues": [
                {
                    "venue": "fanatics_collect",
                    "gross": "200",
                    "fee_pct": "10",
                    "fixed_fee": "0",
                    "shipping": "5",
                    "insurance": "0",
                    "tax": "0",
                    "days_to_cash": "365",
                    "source_url": "https://example.com/quoted-fees",
                    "effective_at": "2026-10-28",
                }
            ],
        }
        r = venue_comparison(body)["venues"][0]
        self.assertEqual(r["net_if_sold"], "175.00")
        self.assertEqual(r["capital_carry_cost"], "10.00")
        self.assertEqual(r["time_adjusted_profit"], "65.00")
