import unittest
import numpy as np
from glyph_audit import segment,feature,evaluate

def patch():
    a=np.zeros((24,20),dtype=float)
    a[3:21,4:8]=200
    a[3:21,12:16]=180
    return a

class GlyphAuditTests(unittest.TestCase):
    def test_separate_regions(self):
        self.assertEqual(len(segment(patch(),.55)),2)
    def test_blank_is_not_a_digit(self):
        self.assertEqual(segment(np.zeros((20,20)),.55),[])
    def test_group_holdout(self):
        result=evaluate([("a","11",patch(),"a"),("b","22",patch(),"b")])
        self.assertEqual(result["matching_lines"],0)
        self.assertEqual(result["lines_with_unseen_classes"],2)
    def test_segmentation_failure_reported(self):
        result=evaluate([("a","123",patch(),"a"),("b","11",patch(),"b")])
        self.assertEqual(result["segmented_lines"],1)
        self.assertIsNone(result["details"][0]["prediction"])
    def test_aspect_ratio_preserved(self):
        f=feature(np.ones((20,5)))
        self.assertEqual(f[0].shape,(24,16))
        self.assertEqual(f[1],.25)

if __name__=="__main__":
    unittest.main()
