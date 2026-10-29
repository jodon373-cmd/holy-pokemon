import csv
import tempfile
import unittest
from pathlib import Path
from holy_pokemon.open_strategy_discovery import (
    Identity, generate, identity_from_row, load_universe, route_registry,
    DEFAULT_JUNGLE, DEFAULT_CROSS_SET
)

class OpenEndedDiscoveryTests(unittest.TestCase):
    def test_full_builtin_universe_and_all_routes(self):
        identities,skipped=load_universe([DEFAULT_JUNGLE,DEFAULT_CROSS_SET])
        self.assertGreaterEqual(len(identities),152)
        self.assertEqual(skipped,[])
        self.assertGreaterEqual(len(route_registry()),10)
        results=generate(identities,route_registry())
        self.assertEqual(len(results),len(identities)*len(route_registry()))
        self.assertTrue(all(r["status"]=="UNEXECUTED_RESEARCH_QUERY" for r in results))
        self.assertTrue(all(r["trade_approved"] is False for r in results))
        self.assertTrue(all(r["estimated_profit"] is None for r in results))
        self.assertTrue(all(r["measured_grade_upgrade_probability"] is None for r in results))
    def test_arbitrary_set_era_and_card_not_whitelisted(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"any.csv"
            with p.open("w",newline="") as file:
                out=csv.DictWriter(file,fieldnames=["set","card","number","edition","year","language"])
                out.writeheader()
                out.writerow(dict(set="EX Deoxys",card="Rayquaza ex",number="107",
                                  edition="gold star holo",year="2005",language="English"))
            identities,skipped=load_universe([p])
            self.assertEqual(skipped,[])
            self.assertEqual(len(identities),1)
            results=generate(identities,route_registry())
            self.assertGreaterEqual(len(results),10)
            self.assertTrue(all("EX Deoxys" in x["origin_search_query"] for x in results))
            self.assertTrue(any("CGC Gem Mint 10 sold" in x["target_sold_comp_query"] for x in results))
    def test_strict_variant_and_holo_separation(self):
        keys=[
            Identity("Jungle","Vaporeon","12","unlimited holo","1999"),
            Identity("Jungle","Vaporeon","12","1st_edition holo","1999"),
            Identity("Jungle","Vaporeon","28","unlimited nonholo","1999")
        ]
        results=generate(keys,route_registry()[:1])
        self.assertEqual(len(set(r["origin_search_query"] for r in results)),3)
        self.assertNotEqual(results[0]["identity"]["edition"],results[1]["identity"]["edition"])
    def test_missing_identity_is_skipped_not_invented(self):
        row={"set":"Fossil","card":"Lapras","number":"10"}
        self.assertIsNone(identity_from_row(row,source="supplied.csv"))
    def test_source_dedupes_exact_variants(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"cards.csv"
            p.write_text("set,card,number,edition\nFossil,Lapras,10,unlimited holo\nFossil,Lapras,10,unlimited holo\nFossil,Lapras,10,1st edition holo\n")
            ids,skipped=load_universe([p])
            self.assertEqual(len(ids),2)
            self.assertEqual(skipped,[])

if __name__=="__main__":
    unittest.main()
