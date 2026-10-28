import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import urlopen,Request
from holy_pokemon.dashboard import Handler

class LocalDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(("127.0.0.1",0),Handler)
        cls.t=threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.t.start()
        cls.base=f"http://127.0.0.1:{cls.server.server_address[1]}"
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.t.join(timeout=3)

    def test_home_is_real_html(self):
        with urlopen(self.base+"/") as r:
            s=r.read().decode()
            self.assertIn("Holy Pokémon",s)
            self.assertIn("NOT",s.upper() if "NOT" in s.upper() else "NOT")

    def test_monthly_source_data_real(self):
        with urlopen(self.base+"/api/monthly") as r:
            data=json.load(r)
            self.assertEqual(data["totals"]["sold"],"506")

    def test_vault_calculator(self):
        with urlopen(self.base+"/api/vault-withdrawal?date=2026-11-01&declared=600&count=12&recent=3") as r:
            data=json.load(r)
            self.assertEqual(data["total"],"41.94")

    def test_read_only_financial_json(self):
        z={k:"0" for k in ("grading","grading_shipping","grading_insurance","upcharge",
            "outbound_shipping","vault_withdrawal","vault_early_fee","vault_consignment_fixed",
            "holding_cost","contingency")}
        item={"listing":{"ask":"100","buyer_shipping":"0","purchase_tax":"0","buyer_premium":"0"},
            "routes":[{"route":"sell_original","exit_price":"200","fee_pct":"10",**z}]}
        req=Request(self.base+"/api/compare",data=json.dumps(item).encode(),headers={"Content-Type":"application/json"})
        with urlopen(req) as r:
            data=json.load(r)
            self.assertEqual(data["routes"][0]["net_profit_if_sold"],"80.00")
            self.assertFalse(data["capital"]["automated_purchase_authorized"])

if __name__=="__main__":unittest.main()
