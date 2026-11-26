import unittest
from PIL import Image
from review import RANKS,SUITS,decode,match
from table_observation import D,dealer_marker,status_label,call_prompt
from amount_text import number_text
import numpy as np
class ObservationTests(unittest.TestCase):
    def test_added_ranks(self):
        for k in ("8_sample","7_sample","6_sample","T_sample","9_sample"):
            self.assertEqual(match(decode(RANKS[k]),RANKS)[0],k.split("_")[0])
    def test_dealer_marker(self):
        a=np.full((355,768),140,dtype=np.uint8)
        a[89:102,412:425]=D.astype(np.uint8)
        self.assertEqual(dealer_marker(Image.fromarray(a).convert("RGB").resize((1536,709)))["candidate"],"upper_right")
    def test_call_prompt_requires_explicit_price(self):
        for raw in ("CALL 50 OR RAISE","CALL ♢ 200 OR RAISE"):
            self.assertIsNotNone(call_prompt(raw,90,number_text))
        for raw in ("Call","CHECK","CALL 1.2K OR RAISE","CALL 50","BET 50"):
            self.assertIsNone(call_prompt(raw,90,number_text))
        self.assertIsNone(call_prompt("CALL 50 OR RAISE",30,number_text))
        self.assertEqual(status_label("Ante"),"Ante")
    def test_no_marker(self):
        self.assertIsNone(dealer_marker(Image.new("RGB",(1536,709),(90,130,160)))["candidate"])
    def test_status_only_explicit(self):
        self.assertEqual(status_label("Small blind"),"Small blind")
        self.assertEqual(status_label("Sat out"),"Sat out")
        self.assertIsNone(status_label("Guest"))
    def test_exact_dealer_cache_matches_uncached_on_changed_regions(self):
        from adaptive_labels import RegionOCRCache
        from unittest.mock import patch
        cache=RegionOCRCache()
        a=np.full((355,768),140,dtype=np.uint8)
        a[89:102,412:425]=D.astype(np.uint8)
        im=Image.fromarray(a).convert("RGB").resize((1536,709))
        expected=dealer_marker(im)
        self.assertEqual(dealer_marker(im,cache),expected)
        with patch("table_observation.sliding_window_view",side_effect=AssertionError("unchanged dealer region rescanned")):
            self.assertEqual(dealer_marker(im,cache),expected)
        a[89:102,412:425]=140
        changed=Image.fromarray(a).convert("RGB").resize((1536,709))
        self.assertEqual(dealer_marker(changed,cache),dealer_marker(changed))
if __name__=="__main__":unittest.main()
