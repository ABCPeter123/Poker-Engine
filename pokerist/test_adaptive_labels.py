import unittest
from adaptive_labels import select_amount
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
    def test_no_text_unknown(self):
        self.assertIsNone(select_amount([],number_text)["candidate"])
    def test_rounded_amount(self):
        self.assertEqual(select_amount([w("8.6K",10)],number_text)["candidate"]["value"],8600)
    def test_search_regions_wider_than_old_crops(self):
        self.assertTrue(all(box[2]-box[0]>=160 for box in NUMBERS.values()))

if __name__=="__main__":unittest.main()
