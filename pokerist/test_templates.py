import unittest
import numpy as np
from review import decode, match, RANKS, SUITS

class TemplateTests(unittest.TestCase):
    def test_tilted_hole_nine(self):
        self.assertEqual(match(decode(RANKS["9_hole"]), RANKS), ("9",0.0))
    def test_same_label_variants_are_not_competing(self):
        template=SUITS["d"]
        self.assertEqual(match(decode(template), {"d":template,"d_other":template,"c":SUITS["c"]}),("d",0.0))
    def test_all_calibrated_templates(self):
        for templates in (RANKS,SUITS):
            for key,value in templates.items():
                self.assertEqual(match(decode(value),templates)[0],key.split("_")[0])

if __name__=="__main__":
    unittest.main()
