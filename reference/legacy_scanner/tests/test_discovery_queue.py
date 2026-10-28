import csv,tempfile,unittest
from pathlib import Path
from scanner.discovery_queue import build_queue,determine_priority,run

class DiscoveryQueueTests(unittest.TestCase):
    def test_rapidash_comes_first_but_is_not_investment(self):
        r=determine_priority(dict(title="CGC Blue Label GEM MINT 9.5 2002 Expedition Base Set Rapidash #62/165",asking_price="82.95",shipping="5.45",original_grade="9.5",grade_designation="gem_mint"))
        self.assertEqual(88.4,r["subtotal_before_tax"])
        self.assertTrue(r["rapidash_like_known_exit"])
        self.assertIsNone(r["expected_profit"])
        self.assertIsNone(r["estimated_psa10_probability"])
        self.assertEqual("RESEARCH_ONLY_NOT_A_TRADE",r["category"])
    def test_other_cards_no_invented_sale_price(self):
        r=determine_priority(dict(title="CGC old blue label gem mint 9.5 EX Dragon Flygon #15",asking_price="88",shipping="5",original_grade="9.5"))
        self.assertIsNone(r["psa10_verified_exit_median_if_exact_variant"])
    def test_mintplus_and_grade9_kept_in_separate_lanes(self):
        a,n=build_queue([dict(title="Articuno CGC 9.5 Mint+",original_grade="9.5"),dict(title="Skyridge CGC 9 old label",original_grade="9"),dict(title="Expedition Rapidash 62/165 CGC 9.5",original_grade="9.5")])
        self.assertEqual((len(a),n),(3,0))
        self.assertEqual({x["discovery_lane"] for x in a},{"mint_plus95_separate","cgc9_separate","unverified_95_other"})
    def test_rapidash_26_not_mismatched_with_nonholo62(self):
        r=determine_priority(dict(title="2002 Expedition Rapidash #26/165 CGC 9.5 Gem Mint",original_grade="9.5"))
        self.assertFalse(r["rapidash_like_known_exit"])
    def test_high_ask_does_not_exclude_candidate(self):
        item=determine_priority(dict(title="CGC Blue Label GEM MINT 9.5 Mew Black Star Promo Holo #9",original_grade="9.5",asking_price="2499",shipping="5"))
        self.assertEqual(item["subtotal_before_tax"],2504.0)
        self.assertEqual(item["discovery_lane"],"legacy_blue_gem_mint95_claim")
    def test_nonempty_top20_without_sold_comps(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"leads.csv"
            with p.open("w",newline="") as f:
                w=csv.DictWriter(f,fieldnames=["title","original_grade","asking_price","shipping"]);w.writeheader()
                for i in range(23):w.writerow(dict(title=f"CGC old label Gem Mint 9.5 Jungle 1st Edition card {i}",original_grade="9.5",asking_price="90",shipping="5"))
            result=run(p,Path(d)/"out")
            self.assertEqual(20,result["top20_investigation"])
            self.assertEqual(0,result["verified_profit_ranked"])
            with (Path(d)/"out"/"discovery_top20_inspect.csv").open() as f:
                self.assertEqual(20,len(list(csv.DictReader(f))))
if __name__=="__main__":unittest.main()
