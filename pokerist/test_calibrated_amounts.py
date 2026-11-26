import unittest
from PIL import Image
from calibrated_amounts import bank,candidate,combine,BET_KEYS
from amount_text import number_text
class CalibratedAmountTests(unittest.TestCase):
    def test_model_decodes_all_digits(self):
        b=bank()
        self.assertEqual(b.pixels.shape,(24,384))
        self.assertEqual(set(b.labels),set("0123456789.K"))
    def test_empty_bet_regions_abstain(self):
        image=Image.new("RGB",(1536,709),(50,80,110))
        for key in BET_KEYS.values():self.assertEqual(candidate(image,key),(None,None))
    def test_conflicts_preserved_and_no_fake_confidence(self):
        g={**number_text("13.5K"),"source":"fixed-font","glyph_candidate":True}
        p={"candidate":None,"ocr_confidence":0}
        r=combine(p,g,[1,2,3,4])
        self.assertEqual(r["candidate"]["value"],13500)
        self.assertTrue(r["candidate"]["approximate"])
        self.assertEqual(r["ocr_confidence"],0)
        r=combine({"candidate":number_text("20")},g,None)
        self.assertIsNone(r["candidate"])
        self.assertTrue(r["reader_conflict"])
        self.assertEqual(r["ocr_candidate"]["value"],20)
