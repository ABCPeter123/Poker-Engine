import unittest
import numpy as np
from amount_glyph_library import decode_library,build_library,evaluate_and_build
class AmountGlyphLibraryTests(unittest.TestCase):
    def test_missing_classes_are_not_invented(self):
        patch=np.zeros((24,12),dtype=float)
        patch[3:21,4:8]=255
        model=build_library([("a","1",patch,"stack")])
        self.assertIn("0",model["missing_digits"])
        self.assertIn("9",model["missing_digits"])
        self.assertFalse(model["validated_for_automatic_full_screen"])
        self.assertEqual(len(decode_library(model)),len(model["templates"]))
    def test_invalid_pixel_values_rejected(self):
        model={"format":1,"feature_size":[24,16],"templates":[{"label":"1","aspect":.5,"pixels":[256]*384}]}
        with self.assertRaises(ValueError):decode_library(model)
    def test_one_group_cannot_claim_holdout(self):
        with self.assertRaises(ValueError):evaluate_and_build([("a","1",np.zeros((10,10)),"stack")])
