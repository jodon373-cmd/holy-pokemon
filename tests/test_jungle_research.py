import unittest
from holy_pokemon.jungle_research import rank_candidates

class JungleResearchTests(unittest.TestCase):
    def test_same_card_edition_and_grade_only(self):
        pops=[
            {"name":"Vaporeon","card_number":"12","variant":"unlimited","psa_10_rate_pct":"0.21","cgc_gem10_rate_pct":"1.7"},
            {"name":"Vaporeon","card_number":"12","variant":"1st_edition"}
        ]
        def row(edition, grade, price):
            return {"card":"Vaporeon","number":"12","edition":edition,
                    "grade_class":grade,"reported_usd":str(price),
                    "verification":"REPORTED_COMPLETED_SALE"}
        sales=[row("unlimited","PSA_9",300),row("unlimited","CGC_GEM_MINT_10",800),
               row("1st_edition","CGC_GEM_MINT_10",2500)]
        found=rank_candidates(sales,pops)
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]["edition"],"unlimited")
        self.assertEqual(found[0]["success_only_spread_after_assumed_fee_grading_usd"],"341.00")
        self.assertFalse(found[0]["purchase_approved"])
    def test_unknown_not_used(self):
        rows=[{"card":"Snorlax","number":"11","edition":"unlimited",
               "grade_class":"PSA_9","reported_usd":"100",
               "verification":"ACTIVE_ASK_NOT_SALE"}]
        self.assertEqual(rank_candidates(rows,[]),[])
    def test_invalid_costs(self):
        with self.assertRaises(ValueError):rank_candidates([],[],fee_pct="101")
        with self.assertRaises(ValueError):rank_candidates([],[],grading_cost="-1")

if __name__=="__main__":unittest.main()
