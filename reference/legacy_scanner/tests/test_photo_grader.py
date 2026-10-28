import tempfile,unittest
from pathlib import Path
import numpy as np
from PIL import Image
from scanner.photo_grader import read_image,quality,estimated_border,analyze
from scanner.grade_image_dataset import audit

class PhotoGraderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'test.png'
        image=np.full((700,500,3),220,dtype=np.uint8)
        image[32:668,28:472]=[200,80,90]
        image[36:664,32:468]=[50,75,100]
        Image.fromarray(image).save(self.path)
    def test_load_and_quality(self):
        self.assertEqual((700,500,3),read_image(self.path).shape)
        self.assertGreaterEqual(quality(read_image(self.path))['blur_variance'],0)
    def test_file_restrictions(self):
        with self.assertRaises(ValueError):read_image('/no/file.png')
        with self.assertRaises(ValueError):read_image('https://example.com/a.jpg')
    def test_border_hint(self):
        self.assertIn('major_percent',estimated_border(read_image(self.path))['tb'])
    def test_never_certify(self):
        r=analyze(str(self.path),already_cropped=True)
        self.assertIsNone(r['psa10_probability'])
        self.assertIsNone(r['grade_estimate'])
        self.assertFalse(r['purchase_approved'])
        self.assertIn('back_missing_image',r['reasons'])
    def test_dataset_rights_needed(self):
        r=audit([dict(image_id='1',card_id='A',grade='10',grade_company='PSA',side='front',local_path=str(self.path))])
        self.assertEqual(0,r['summary']['unique_usable_images'])
    def test_dataset_duplicate_image_rejected(self):
        rows=[dict(image_id=str(i),card_id=str(i),grade='10',grade_company='PSA',
                   side='front',local_path=str(self.path),rights_basis='self_photographed',
                   rights_evidence='owner attestation') for i in (1,2)]
        r=audit(rows)
        self.assertEqual(1,r['summary']['unique_usable_images'])
        self.assertEqual(1,r['summary']['rejected'])
    def test_grade_diversity_required(self):
        rows=[dict(image_id='1',card_id='A',grade='10',grade_company='PSA',
                   side='front',local_path=str(self.path),rights_basis='self_photographed',
                   rights_evidence='owner attestation')]
        r=audit(rows,min_unique_images=1,min_each_grade=0)
        self.assertFalse(r['summary']['ready_for_training_review'])
if __name__=='__main__':unittest.main()
