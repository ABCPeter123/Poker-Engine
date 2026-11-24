import unittest
from PIL import Image
from saved_amount_review import strict_amount,add_evidence,prepare_line
from review import number_text

def obs(raw,confidence=90):
    return {"raw":raw,"confidence":confidence}

class SavedAmountTests(unittest.TestCase):
    def test_reject_malformed(self):
        for value in ("O","1O0","1 23","196 $29","450 |","1.5","1 2 3"):
            self.assertIsNone(strict_amount(value,number_text))
        self.assertEqual(strict_amount("19 950",number_text)["value"],19950)
        self.assertEqual(strict_amount("4.5K",number_text)["value"],4500)
    def test_two_high_confidence_and_matching_primary_raw(self):
        a={"raw":"19000","candidate":None}
        r=add_evidence(a,[obs("19 000"),obs("19000",78),obs("??")],number_text)
        self.assertEqual(r["candidate"]["value"],19000)
        self.assertFalse(r["candidate"]["verified"])
        self.assertIsNone(a["candidate"])
    def test_disagreement_does_not_promote(self):
        r=add_evidence({"raw":"430","candidate":None},[obs("450"),obs("450"),obs("430",30)],number_text)
        self.assertIsNone(r["candidate"])
        self.assertEqual(r["saved_line_status"],"conflicting readings")
    def test_keep_primary_with_explicit_conflict(self):
        p={"raw":"186550","candidate":number_text("186550")}
        r=add_evidence(p,[obs("106550"),obs("106550")],number_text)
        self.assertEqual(r["candidate"]["value"],186550)
        self.assertEqual(r["saved_line_status"],"conflicting readings")
    def test_low_confidence_and_no_primary_raw(self):
        for p,passes in [({"raw":"0","candidate":None},[obs("0",60),obs("0",62)]),
                         ({"raw":"","candidate":None},[obs("50"),obs("50")])]:
            self.assertIsNone(add_evidence(p,passes,number_text)["candidate"])
    def test_zero_is_valid_and_empty_is_not(self):
        self.assertEqual(strict_amount("0",number_text)["value"],0)
        self.assertIsNone(strict_amount("",number_text))
        self.assertIsNone(prepare_line(Image.new("RGB",(100,40),(50,80,110)),(0,0,100,40),"stack",140))

if __name__=="__main__":
    unittest.main()
