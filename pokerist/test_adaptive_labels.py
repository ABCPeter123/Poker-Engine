import unittest
from adaptive_labels import select_amount, numeric_mask
import numpy as np
from review import number_text, NUMBERS

def w(text,x,y=10,confidence=95):
    return {"text":text,"x":x,"y":y,"w":len(text)*8,"h":16,"confidence":confidence}

class AdaptiveLabelTests(unittest.TestCase):
    def test_shifted_amount(self):
        for x in (10,55,120):
            r=select_amount([w("19500",x)],number_text)
            self.assertEqual(r["candidate"]["value"],19500)
            self.assertEqual(r["text_bounds"][0],x)
    def test_grouped_digits(self):
        r=select_amount([w("19",10),w("950",32)],number_text)
        self.assertEqual(r["candidate"]["value"],19950)
    def test_multiple_lines_unknown(self):
        self.assertIsNone(select_amount([w("50",10),w("19500",10,40)],number_text)["candidate"])
    def test_bad_fragment_unknown(self):
        self.assertIsNone(select_amount([w("9",10,confidence=40),w("500",30)],number_text)["candidate"])
        self.assertIsNone(select_amount([w("50",10),w("25",50)],number_text)["candidate"])
    def test_competing_low_confidence_line_blocks_high_confidence(self):
        self.assertIsNone(select_amount([w("500",10),w("5000",10,40,confidence=20)],number_text)["candidate"])
    def test_nonfinite_confidence_is_rejected(self):
        r=select_amount([w("500",10,confidence=float("nan"))],number_text)
        self.assertIsNone(r["candidate"])
        self.assertEqual(r["ocr_confidence"],-1)
    def test_no_text_unknown(self):
        self.assertIsNone(select_amount([],number_text)["candidate"])
    def test_rounded_amount(self):
        self.assertEqual(select_amount([w("8.6K",10)],number_text)["candidate"]["value"],8600)
    def test_split_compact_suffix(self):
        for value,suffix,expected in (("4","k",4000),("200","K",200000),("4.5","K",4500)):
            r=select_amount([w(value,10),w(suffix,50)],number_text)
            self.assertEqual(r["candidate"]["value"],expected)
            self.assertTrue(r["candidate"]["approximate"])
        self.assertIsNone(select_amount([w("4",10),w("5",35),w("K",50)],number_text)["candidate"])
    def test_stack_icon_preprocessing(self):
        a=np.full((22,60,3),60,dtype=np.uint8)
        a[3:17,3:16]=235
        a[4:17,19:27]=235
        a[4:17,30:38]=235
        m=numeric_mask(a,"stack")
        self.assertFalse(m[:,:16].any())
        self.assertTrue(m[:,19:27].any())
    def test_colored_chip_preprocessing(self):
        a=np.full((35,80,3),60,dtype=np.uint8)
        a[6:29,6:28]=[200,30,20]
        a[12:18,10:14]=235
        a[11:24,39:47]=235
        m=numeric_mask(a,"bet")
        self.assertFalse(m[:,:28].any())
        self.assertTrue(m[:,39:47].any())
    def test_low_confidence_keeps_raw_not_amount(self):
        result=select_amount([w("22200",10,confidence=0)],number_text)
        self.assertEqual(result["raw"],"22200")
        self.assertEqual(result["ocr_confidence"],0)
        self.assertIsNone(result["candidate"])
    def test_search_regions_wider_than_old_crops(self):
        self.assertTrue(all(box[2]-box[0]>=160 for box in NUMBERS.values()))

if __name__=="__main__":unittest.main()
