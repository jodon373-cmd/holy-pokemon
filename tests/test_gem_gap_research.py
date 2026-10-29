import unittest
from holy_pokemon.gem_gap_research import rank

def pop(set_name,card,n,edition,psa10=10,psa_total=1000,cgc10=20,cgc_total=300,guide9="150",guide10="500"):
    return {
        "set":set_name, "card":card, "number":str(n), "edition":edition,
        "psa_9_pop":"100", "psa_10_pop":str(psa10), "psa_total":str(psa_total),
        "cgc_10_inclusive_pop":str(cgc10), "cgc_total":str(cgc_total),
        "grade9_blended_guide_usd_not_psa9_sold":guide9,
        "cgc_gem10_guide_usd_not_sold":guide10, "priority":"A",
        "population_url":"https://example.com/pop","price_guide_url":"https://example.com/guide"
    }

def sale(set_name,card,n,edition,company,grade,price,date="2026-09-01",status="PRICECHARTING_REPORTED_COMPLETED_SALE_NOT_INDEPENDENT_FINAL_PAYOUT"):
    return {"set":set_name,"card":card,"card_number":str(n),"edition":edition,
            "grading_company":company,"grade_class":grade,"reported_price_usd":str(price),
            "reported_date":date,"source_status":status}

class CrossSetGemGapTests(unittest.TestCase):
    def test_never_use_guide_as_psa_sold(self):
        r=rank([pop("Fossil","Lapras",10,"unlimited holo")],[])
        self.assertIsNone(r[0]["success_only_historical_sale_spread_net_assumptions"])
        self.assertEqual(r[0]["psa9_source_reported_sale_count"],0)
        self.assertIsNotNone(r[0]["guide_only_spread_not_realized"])
        self.assertFalse(r[0]["purchase_approved"])
        self.assertTrue(r[0]["no_calibrated_conversion_probability"])
    def test_transaction_same_variant_and_grade_restriction(self):
        pops=[pop("Fossil","Lapras",10,"unlimited holo"),
              pop("Fossil","Lapras",10,"1st edition holo")]
        sales=[
            sale("Fossil","Lapras",10,"unlimited holo","PSA","MINT_9",200),
            sale("Fossil","Lapras",10,"unlimited holo","PSA","MINT_9",180),
            sale("Fossil","Lapras",10,"unlimited holo","CGC","GEM_MINT_10",500),
            sale("Fossil","Lapras",10,"unlimited holo","CGC","GEM_MINT_10",520),
            sale("Fossil","Lapras",10,"unlimited holo","CGC","GEM_MINT_10",600),
            sale("Fossil","Lapras",10,"1st edition holo","CGC","GEM_MINT_10",8000),
            sale("Fossil","Lapras",10,"unlimited holo","CGC","PRISTINE_10",9000),
            sale("Fossil","Lapras",10,"unlimited holo","CGC","GEM_MINT_10",7000,status="ACTIVE_LISTING"),
        ]
        out=rank(pops,sales)
        valid=next(x for x in out if x["edition"]=="unlimited holo")
        self.assertEqual(valid["psa9_source_reported_sale_count"],2)
        self.assertEqual(valid["cgc_gem10_source_reported_sale_count"],3)
        self.assertEqual(valid["cgc10_source_reported_sale_lower_quartile"],"500.00")
        self.assertEqual(valid["success_only_historical_sale_spread_net_assumptions"],"160.00")
        other=next(x for x in out if x["edition"]=="1st edition holo")
        self.assertIsNone(other["success_only_historical_sale_spread_net_assumptions"])
        self.assertNotEqual(other["research_status"],valid["research_status"])
    def test_no_confidence_from_population_ratio(self):
        records=[pop("Fossil","Gengar",5,"unlimited holo",psa10=1,cgc10=90)]
        result=rank(records,[])[0]
        self.assertFalse(result["purchase_approved"])
        self.assertEqual(result["research_status"],"INSUFFICIENT_SAME_GRADE_SALES_DO_NOT_VALIDATE_TRADE")
    def test_invalid_fees(self):
        with self.assertRaises(ValueError):
            rank([],[],fee_pct="101")
        with self.assertRaises(ValueError):
            rank([],[],acquisition_cost_buffer="-5")

if __name__=="__main__":
    unittest.main()
