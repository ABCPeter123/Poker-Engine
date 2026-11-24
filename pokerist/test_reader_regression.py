import unittest
from review import RANKS, SUITS, decode, match, BOARD, ten_corner, number_text
from adaptive_labels import reconcile_amount, stack_line_mask
import numpy as np

class ReaderRegression(unittest.TestCase):
    def test_captured_glyphs(self):
        for key in ("T_capture0","8_capture1","8_capture2","3_capture4"):
            self.assertEqual(match(decode(RANKS[key]),RANKS)[0],key.split("_")[0])
        for key in ("s_capture0","d_capture1","h_capture2","h_capture4"):
            allowed="cs" if key[0] in "cs" else "dh"
            self.assertEqual(match(decode(SUITS[key]),{k:v for k,v in SUITS.items() if k[0] in allowed},.25)[0],key[0])
    def test_ten_crop_is_wider_but_preserves_suit(self):
        r,s,b=ten_corner(BOARD[0])
        self.assertGreaterEqual(r[2]-r[0],35)
        self.assertEqual(s,BOARD[0][1])
        self.assertEqual(b,BOARD[0][2])
    def test_agreement_required(self):
        first={"raw":"15500","candidate":None,"ocr_confidence":0}
        second={"raw":"15 500","candidate":{"value":15500},"ocr_confidence":84}
        self.assertEqual(reconcile_amount(first,second,number_text)["candidate"]["value"],15500)
        first["raw"]="500"
        self.assertIsNone(reconcile_amount(first,second,number_text)["candidate"])
    def test_stack_line_removes_other_rows(self):
        a=np.zeros((33,170,3),dtype=np.uint8)
        a[0,70:80]=235
        a[8:22,60:65]=235
        a[8:22,70:77]=235
        a[8:22,80:87]=235
        m=stack_line_mask(a)
        self.assertFalse(m[0].any())
        self.assertTrue(m[8:22].any())

if __name__=="__main__":unittest.main()
