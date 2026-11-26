import unittest
from PIL import Image
from review import RANKS,SUITS,decode,match
from table_observation import D,dealer_marker,status_label,call_prompt,action_prompt_panel,observe_table
from amount_text import number_text
import numpy as np
class ObservationTests(unittest.TestCase):
    def test_new_rank_masks(self):
        for name in ('6_nov25_424_1536','6_nov25_424_960','T_nov25_424_720','T_nov25_433_1536'):
            self.assertEqual(match(decode(RANKS[name]),RANKS)[0],name[0])
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
        self.assertEqual(call_prompt("CHECK or RAISE",90,number_text)["value"],0)
        self.assertIsNone(call_prompt("CHECK or RAISE",50,number_text))
    def test_prompt_panel_requires_blue_fill_and_two_borders(self):
        a=np.full((709,1536,3),[90,130,160],dtype=np.uint8)
        self.assertFalse(action_prompt_panel(Image.fromarray(a)))
        a[386:420,630:907]=[30,65,105]
        a[387:389,630:907]=[220,220,220]
        a[417:419,630:907]=[220,220,220]
        self.assertTrue(action_prompt_panel(Image.fromarray(a)))
        a[417:419,630:907]=[30,65,105]
        self.assertFalse(action_prompt_panel(Image.fromarray(a)))
    def test_prompt_can_corroborate_missing_ring_not_override_opponent(self):
        from unittest.mock import patch
        im=Image.new("RGB",(1536,709))
        base={"seats":{},"active_band_candidate":None,"active_band_conflict":False}
        with patch("table_observation.action_prompt_panel",return_value=True),patch("table_observation.scan_labels",return_value=({},None)),patch("table_observation.read_call_prompt",return_value={"candidate":number_text("0")}) as reader:
            r=observe_table(im,"test",number_text,{},base,[{"candidate":"As"},{"candidate":"Kd"}])
            self.assertEqual(r["turn_candidate"],"hero")
            self.assertEqual(r["turn_source"],"explicit action prompt")
            self.assertTrue(r["seats"]["hero"]["turn_candidate"])
            self.assertEqual(observe_table(im,"test",number_text,{},dict(base,active_band_candidate="left"),[{}])["turn_candidate"],"left")
            self.assertIsNone(observe_table(im,"test",number_text,{},dict(base,active_band_conflict=True),[{}])["turn_candidate"])
            self.assertIsNone(observe_table(im,"test",number_text,{},base,[None,None])["turn_candidate"])
            self.assertEqual(reader.call_count,1)
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
