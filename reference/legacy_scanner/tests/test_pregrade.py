import unittest
from scanner.pregrade import inspect, build

def specimen(top=50,bottom=50,error=1):
    d={'front_photo_url':'https://example.org/front.jpg',
       'back_photo_url':'https://example.org/back.jpg',
       'photo_quality':'high',
       'measurement_method':'manual_straight_on_border_pixels',
       'measurement_uncertainty_pp':str(error),
       'front_top_px':str(top),'front_bottom_px':str(bottom),
       'front_left_px':'50','front_right_px':'50',
       'back_top_px':'50','back_bottom_px':'50',
       'back_left_px':'50','back_right_px':'50'}
    d.update({f'defect_{x}':'not_visible' for x in ('scratches','print_lines',
       'whitening','corner_wear','dents','creases','stains','gloss_loss','trimming')})
    return d

L={'title':'Test CGC Mint+ 9.5','marketplace_item_id':'111',
   'url':'https://www.ebay.com/itm/111','grade':'9.5'}

class PregradeTests(unittest.TestCase):
    def test_no_photos_never_pass(self):
        r=inspect(L,{})
        self.assertEqual('INSUFFICIENT_PHOTO_EVIDENCE',r['pregrade_status'])
        self.assertEqual('',r['psa10_probability'])
    def test_front_top_bottom_over_limit_flags(self):
        r=inspect(L,specimen(top=61,bottom=39))
        self.assertEqual('PSA10_VISUAL_CONCERN',r['pregrade_status'])
        self.assertIn('front_tb_outside',r['psa10_screen_concerns'])
    def test_front_top_bottom_borderline(self):
        r=inspect(L,specimen(top=54.5,bottom=45.5,error=1))
        self.assertEqual('BORDERLINE_OR_UNVERIFIED',r['pregrade_status'])
    def test_clean_photo_cannot_certify(self):
        r=inspect(L,specimen(top=52,bottom=48,error=1))
        self.assertEqual('PHOTO_SCREEN_PLAUSIBLE_NOT_A_GRADE',r['pregrade_status'])
        self.assertEqual('false',r['purchase_approved'])
    def test_defect_flags(self):
        d=specimen();d['defect_corner_wear']='seen'
        self.assertEqual('PSA10_VISUAL_CONCERN',inspect(L,d)['pregrade_status'])
    def test_bad_quality_prevents_numeric_veto(self):
        d=specimen(top=70,bottom=30);d['photo_quality']='blurry'
        self.assertEqual('INSUFFICIENT_PHOTO_EVIDENCE',inspect(L,d)['pregrade_status'])
    def test_all_listings_preserved(self):
        l=[L,dict(L,marketplace_item_id='222')]
        t,r=build(l,[{'marketplace_item_id':'111',**specimen()}])
        self.assertEqual(2,len(t));self.assertEqual(2,len(r))
        self.assertEqual('INSUFFICIENT_PHOTO_EVIDENCE',r[1]['pregrade_status'])
    def test_unmeasured_reviewer_concern_is_not_verified_veto(self):
        r=inspect(L,{'reviewer_concern':'front_top_bottom_offcenter'})
        self.assertEqual('PRELIMINARY_CONCERN_UNMEASURED',r['pregrade_status'])
    def test_duplicate_inspection_rejected(self):
        with self.assertRaises(ValueError):
            build([L],[{'marketplace_item_id':'111'},{'marketplace_item_id':'111'}])

if __name__=='__main__': unittest.main()
