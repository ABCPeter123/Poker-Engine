import unittest
from PIL import Image
from review import RANKS,SUITS,decode,match
from table_observation import D,dealer_marker,status_label
import numpy as np
class ObservationTests(unittest.TestCase):
    def test_added_ranks(self):
        for k in ("8_sample","7_sample","6_sample","T_sample","9_sample"):
            self.assertEqual(match(decode(RANKS[k]),RANKS)[0],k.split("_")[0])
    def test_dealer_marker(self):
        a=np.full((355,768),140,dtype=np.uint8)
        a[89:102,412:425]=D.astype(np.uint8)
        self.assertEqual(dealer_marker(Image.fromarray(a).convert("RGB").resize((1536,709)))["candidate"],"upper_right")
    def test_no_marker(self):
        self.assertIsNone(dealer_marker(Image.new("RGB",(1536,709),(90,130,160)))["candidate"])
    def test_status_only_explicit(self):
        self.assertEqual(status_label("Small blind"),"Small blind")
        self.assertEqual(status_label("Sat out"),"Sat out")
        self.assertIsNone(status_label("Guest"))
if __name__=="__main__":unittest.main()
