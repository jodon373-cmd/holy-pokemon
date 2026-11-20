"""Geometry and local-tool regressions. All generated photos are synthetic."""
import base64
import unittest
import cv2
import numpy as np
from holy_pokemon.centering_tool import inspect, manual_ratios
from holy_pokemon.centering_v3 import measure_bgr


class CenteringToolTests(unittest.TestCase):
    def scene(self, left=40, right=35):
        image=np.full((1400,1000,3),40,np.uint8)
        # Physical blue card, plus a separate neutral holder/label.
        cv2.rectangle(image,(100,25),(900,1380),(180,180,180),8)
        image[60:270,130:870]=210
        image[330:1310,150:850]=(160,45,10)
        image[370:1270,150+left:850-right]=(175,195,210)
        cv2.circle(image,(500,800),130,(100,70,220),-1)
        return image

    def data(self,image):
        return base64.b64encode(cv2.imencode('.png',image)[1]).decode()

    def test_automatic_card_excludes_holder(self):
        result=measure_bgr(self.scene(),side='back')
        self.assertEqual(result['status'],'MEASURED_NEEDS_VALIDATION',result)
        self.assertTrue(all(y>325 for x,y in result['outer_quad']))
        self.assertAlmostEqual(result['ratios']['left_pct'],40/75*100,delta=2)

    def test_off_center_control_is_not_forced_to_pass(self):
        result=measure_bgr(self.scene(100,20),side='back')
        self.assertEqual(result['status'],'MEASURED_NEEDS_VALIDATION',result)
        self.assertGreater(result['ratios']['max_horizontal_pct'],75)

    def test_neutral_holder_alone_abstains(self):
        image=np.full((1400,1000,3),70,np.uint8)
        cv2.rectangle(image,(150,300),(850,1280),(180,180,180),12)
        self.assertEqual(measure_bgr(image,side='back')['status'],'ABSTAIN')

    def test_two_cards_abstain(self):
        result=measure_bgr(np.concatenate([self.scene(),self.scene()],axis=1),side='back')
        self.assertEqual(result['reason'],'multiple_supported_cards')

    def test_yellow_front_automatic_without_corners(self):
        image=np.full((1400,1000,3),40,np.uint8)
        image[330:1310,150:850]=(20,210,240)
        image[368:1272,185:815]=(180,50,80)
        result=measure_bgr(image,side='front')
        self.assertEqual(result['status'],'MEASURED_NEEDS_VALIDATION',result)
        self.assertAlmostEqual(result['ratios']['left_pct'],50,delta=2)
        self.assertAlmostEqual(result['ratios']['top_pct'],50,delta=2)

    def test_silver_front_automatic_without_corners(self):
        image=np.full((1400,1000,3),40,np.uint8)
        cv2.rectangle(image,(90,20),(910,1380),(160,160,160),8)
        image[60:250,120:880]=210
        image[330:1310,150:850]=(230,230,230)
        image[365:1275,180:820]=(170,45,80)
        result=measure_bgr(image,side='front')
        self.assertEqual(result['status'],'MEASURED_NEEDS_VALIDATION',result)
        self.assertEqual(result['layout'],'silver_border')
        self.assertAlmostEqual(result['ratios']['left_pct'],50,delta=2)
        self.assertAlmostEqual(result['ratios']['top_pct'],50,delta=2)
        self.assertTrue(all(y>325 for x,y in result['outer_quad']))

    def test_side_detected_without_user_selection(self):
        result=inspect(dict(image=self.data(self.scene())))
        self.assertEqual(result['side'],'back')
        self.assertIsNotNone(result['result']['ratios'])

    def test_manual_60_40_remains_60_40(self):
        result=manual_ratios(dict(left=60,right=40,top=50,bottom=50))
        self.assertEqual(result['left_pct'],60)

    def test_invalid_manual_guides_rejected(self):
        for value in [0,-1,float('nan'),float('inf'),800]:
            with self.assertRaises(ValueError):
                manual_ratios(dict(left=value,right=40,top=50,bottom=50))

    def test_rectification_uses_selected_card(self):
        result=inspect(dict(image=self.data(self.scene()),side='back',quad=[[150,330],[849,330],[849,1309],[150,1309]]))
        self.assertEqual((result['width'],result['height']),(700,980))
        rect=cv2.imdecode(np.frombuffer(base64.b64decode(result['image'].split(',')[1]),np.uint8),cv2.IMREAD_COLOR)
        self.assertEqual(rect.shape[:2],(980,700))

    def test_outside_corners_rejected(self):
        with self.assertRaises(ValueError):
            inspect(dict(image=self.data(self.scene()),quad=[[-10,330],[849,330],[849,1309],[-10,1309]]))
