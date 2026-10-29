import unittest
from holy_pokemon.promo_priority import preset, queries, matches_promo, discover, tag_listing

class PromoPriorityTests(unittest.TestCase):
    def test_preset(self):
        data=preset()
        self.assertEqual(data["priority_weight"],100)
        self.assertEqual(data["canonical_category_url"],"https://www.pricecharting.com/console/pokemon-promo")
        self.assertEqual(len(queries()),4)
        self.assertGreaterEqual(len(data["queries"]),8)
        with self.assertRaises(ValueError):queries(0)
    def test_tagging_no_trade_approval(self):
        row={"listing_id":"1","title":"Pokemon Black Star Promo Eevee PSA 9",
             "source":"ebay_browse","valuation_eligible":False,"actionable":False}
        tagged=tag_listing(row,"black-star-psa9")
        self.assertEqual(tagged["priority_research_tier"],"CRITICAL_RESEARCH")
        self.assertFalse(tagged["promo_trade_approved"])
        self.assertFalse(tagged["valuation_eligible"])
        self.assertEqual(row.get("research_preset"),None)
        self.assertFalse(matches_promo("Pokemon Jungle Vaporeon PSA 9"))
    def test_discover_dedupes_and_filters(self):
        class Fake:
            def __init__(self):self.calls=[]
            def search(self,q):
                self.calls.append(q)
                return [
                    {"listing_id":"1","title":"Pokemon Black Star Promo Mew PSA 9"},
                    {"listing_id":"2","title":"Pokemon Jungle Mew PSA 9"}
                ]
        c=Fake()
        out=discover(c)
        self.assertEqual(len(c.calls),4)
        self.assertEqual(len(out),1)
        self.assertEqual(out[0]["listing_id"],"1")
        self.assertEqual(len(out[0]["matched_promo_queries"]),3)
if __name__=="__main__":unittest.main()
