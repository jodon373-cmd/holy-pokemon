import json
import tempfile
import unittest
from pathlib import Path

from holy_pokemon.comp_index import CompIndex
from holy_pokemon.ebay_browse import transport
from holy_pokemon.ingestion import connect
from holy_pokemon.query_planner import plan_default_universe
from holy_pokemon.scan_pipeline import main as scan_main, scan_listings
from holy_pokemon.strategy_common import export_csv
from holy_pokemon.title_parser import parse_title


class LiveImportAndHelpersTests(unittest.TestCase):
    def test_live_path_imports_and_csv_export(self):
        self.assertTrue(callable(transport))
        db = connect(":memory:")
        db.close()
        with tempfile.TemporaryDirectory() as tmp:
            out = export_csv(Path(tmp) / "out.csv", [{"a": 1, "b": [1, 2]}])
            self.assertTrue(out.is_file())


class TitleParserTests(unittest.TestCase):
    def test_parses_psa9_holo_with_number_and_year(self):
        p = parse_title("1999 Pokemon Jungle Vaporeon #12/64 Holo PSA 9 Mint Unlimited")
        self.assertEqual(p.grader, "PSA")
        self.assertEqual(p.grade, "9")
        self.assertEqual(p.card_number, "12")
        self.assertEqual(p.set_size, "64")
        self.assertEqual(p.year, "1999")
        self.assertEqual(p.finish, "Holo")
        self.assertFalse(p.disqualified)
        self.assertGreaterEqual(p.confidence, 0.9)

    def test_parses_cgc_pristine_and_gem_mint_separately(self):
        pristine = parse_title("Pokemon Lapras 10/62 Fossil Holo CGC Pristine 10")
        gem = parse_title("Pokemon Lapras 10/62 Fossil Holo CGC Gem Mint 10")
        self.assertEqual(pristine.cgc_sub_tier, "PRISTINE_10")
        self.assertEqual(gem.cgc_sub_tier, "GEM_MINT_10")

    def test_disqualifies_lots_proxies_and_wrong_language(self):
        self.assertTrue(parse_title("Pokemon Lot of 5 PSA 9 Jungle Holos").disqualified)
        self.assertTrue(parse_title("Custom Proxy Orica Charizard PSA 10").disqualified)
        self.assertTrue(parse_title("Japanese Pokemon Jungle Vaporeon 12/64 PSA 9", expected_language='English').disqualified)
        self.assertFalse(parse_title("Japanese Pokemon Jungle Vaporeon 12/64 PSA 9").disqualified)
        q = parse_title("Pokemon Vaporeon 12/64 PSA 9 OC")
        self.assertIn("OC", q.qualifiers)
        self.assertIn("graded_qualifier", q.red_flags)


class CompIndexAndSearchPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = CompIndex.from_csvs()

    def test_indexes_committed_datasets(self):
        self.assertGreaterEqual(len(self.index.records), 100)
        summary = self.index.summarize(
            card="Vaporeon", number="12", grader="CGC", grade_bucket="GEM_MINT_10", set_name="Jungle", edition='unlimited',finish='Holo'
        )
        self.assertIsNotNone(summary)
        self.assertGreaterEqual(summary.count, 1)
        self.assertGreater(summary.median_usd, 0)

    def test_roi_scorer_and_scan_pipeline_rank_leads(self):
        listings = [
            {
                "listing_id": "1",
                "title": "1999 Pokemon Jungle Vaporeon 12/64 Holo PSA 9",
                "card": "Vaporeon",
                "number": "12",
                "set_name": "Jungle",
                "edition": "unlimited",
                "asking_price": "150.00",
                "shipping": "5.00",
                "url": "https://www.ebay.com/itm/123",
            },
            {
                "listing_id": "2",
                "title": "Pokemon Lot of 10 Jungle Vaporeon 12/64",
                "card": "Vaporeon",
                "number": "12",
                "set_name": "Jungle",
                "asking_price": "50.00",
                "url": "https://www.ebay.com/itm/456",
            },
        ]
        report = scan_listings(listings, comp_index=self.index)
        self.assertEqual(report["disqualified_filtered"], 1)
        self.assertEqual(report["returned_count"], 1)
        top = report["ranked_leads"][0]
        self.assertFalse(top["trade_approved"])
        self.assertEqual(top["status"], "SCORED_LEAD")
        self.assertGreater(float(top["conservative_net_profit_usd"]), 0)
        self.assertGreater(top["opportunity_score"], 0)

    def test_query_planner_prioritizes_comp_backed_cards(self):
        planned = plan_default_universe(limit=10)
        self.assertEqual(len(planned), 10)
        self.assertLessEqual(len(planned[0]["ebay_query"]), 100)
        self.assertIn("-lot", planned[0]["ebay_query"])

    def test_scan_pipeline_cli_exports_json_and_csv(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            inp = tmp_dir / "in.json"
            inp.write_text(
                json.dumps([
                    {
                        "listing_id": "1",
                        "title": "1999 Pokemon Jungle Vaporeon 12/64 Holo PSA 9",
                        "card": "Vaporeon",
                        "number": "12",
                        "set_name": "Jungle",
                        "asking_price": "150.00",
                    }
                ]),
                encoding="utf-8",
            )
            out_json = tmp_dir / "out.json"
            out_csv = tmp_dir / "out.csv"
            rc = scan_main(["--input", str(inp), "--output-json", str(out_json), "--output-csv", str(out_csv)])
            self.assertEqual(rc, 0)
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_csv.is_file())


if __name__ == "__main__":
    unittest.main()
