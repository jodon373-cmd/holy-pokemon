import unittest
from datetime import date
from holy_pokemon.vault_engine import (
    transition,withdrawal_quote,psa_consignment_net,partner_offer_net,reconcile_payout
)

class VaultTests(unittest.TestCase):
    def test_future_fee_not_applied_today(self):
        q=withdrawal_quote(asof=date(2026,10,28),declared_usd="499",
            item_count=1,recently_vaulted_count=1)
        self.assertIsNone(q["total"])
        self.assertEqual(q["early"],"4.99")

    def test_shipping_tiers_after_effective_date(self):
        d=date(2026,10,29)
        self.assertEqual(withdrawal_quote(asof=d,declared_usd="499.99",item_count=1)["shipping"],"19.99")
        self.assertEqual(withdrawal_quote(asof=d,declared_usd="500",item_count=1)["shipping"],"24.99")
        self.assertEqual(withdrawal_quote(asof=d,declared_usd="5000",item_count=1)["shipping"],"42.99")
        self.assertEqual(withdrawal_quote(asof=d,declared_usd="25000",item_count=1)["shipping"],"57.99")
        self.assertEqual(withdrawal_quote(asof=d,declared_usd="75000",item_count=1)["shipping"],"139.99")
        self.assertIsNone(withdrawal_quote(asof=d,declared_usd="300000",item_count=1)["total"])

    def test_ten_item_shipment_and_early_fee(self):
        q=withdrawal_quote(asof=date(2026,11,1),declared_usd="600",
            item_count=12,recently_vaulted_count=3)
        self.assertEqual(q["shipping"],"26.97")
        self.assertEqual(q["early"],"14.97")
        self.assertEqual(q["total"],"41.94")

    def test_canada_handling(self):
        q=withdrawal_quote(asof=date(2026,11,1),declared_usd="600",item_count=1,country="CA")
        self.assertEqual(q["shipping"],"49.98")

    def test_psa_fee_single_no_ebay_double(self):
        result=psa_consignment_net("200")
        self.assertEqual(result["net"],"174.00")
        self.assertEqual(result["psa_fee"],"26.00")
        self.assertEqual(result["additional_ebay_fee"],"0")

    def test_unknown_consignment_tier_requires_quote(self):
        self.assertIsNone(psa_consignment_net("1000")["net"])

    def test_partner_offer_actual_not_index(self):
        self.assertIsNone(partner_offer_net("300",actual_active_offer=False)["net"])
        self.assertIsNone(partner_offer_net("300",actual_active_offer=True,card_listed=True)["net"])
        self.assertEqual(partner_offer_net("300",actual_active_offer=True)["net"],"300.00")

    def test_prohibit_unconfirmed_external_action(self):
        with self.assertRaises(PermissionError):transition("vaulted","withdraw_requested",user_confirmed=False)
        r=transition("vaulted","withdraw_requested",user_confirmed=True)
        self.assertFalse(r["remote_action_executed"])

    def test_payout_not_realized_until_provided(self):
        r=reconcile_payout(gross="200",psa_fee="26",actual_payout=None,card_id="card1")
        self.assertIsNone(r["realized_cash"])
        r=reconcile_payout(gross="200",psa_fee="26",actual_payout="174",
            card_id="card1",payout_reference="owner receipt")
        self.assertTrue(r["actual_payout_verified"])
        self.assertEqual(r["status"],"RECONCILED")

if __name__=="__main__":unittest.main()
