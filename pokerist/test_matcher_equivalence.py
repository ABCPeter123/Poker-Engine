import unittest
import numpy as np
from benchmark_matcher import reference_match,optimized_match,samples
from review import RANKS,SUITS,decode,match

class MatcherEquivalenceTests(unittest.TestCase):
    def test_all_calibrated_and_perturbed_masks_match_reference(self):
        for mask,templates,threshold in samples():
            self.assertEqual(optimized_match(mask,templates,threshold),
                             reference_match(mask,templates,threshold))
    def test_threshold_and_margin_rules_unchanged(self):
        mask=decode(RANKS["J"])
        for threshold in (0,.025,.18,.25,1):
            self.assertEqual(match(mask,RANKS,threshold),reference_match(mask,RANKS,threshold))
    def test_cache_tracks_template_content(self):
        m=decode(SUITS["s"])
        templates={"s":SUITS["s"]}
        self.assertEqual(match(m,templates),("s",0.0))
        templates["s"]=SUITS["h"]
        self.assertEqual(match(m,templates),reference_match(m,templates))
    def test_empty_glyph(self):
        self.assertEqual(match(None,RANKS),(None,None))

if __name__=="__main__":
    unittest.main()
