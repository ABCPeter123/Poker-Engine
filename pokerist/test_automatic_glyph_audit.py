import unittest
from unittest.mock import patch
import numpy as np
from PIL import Image
from automatic_glyph_audit import nearest,fit_amount,predict_amount,amount_audit,card_feature,card_audit,summarize

class AutomaticGlyphAuditTests(unittest.TestCase):
    def test_no_candidate_when_library_empty(self):
        self.assertIsNone(predict_amount(np.zeros((10,10)),[])["candidate"])
    def test_equal_distance_is_ambiguous(self):
        entry=(np.zeros((24,16)),.5)
        result=nearest(entry,[("1",entry),("7",entry)])
        self.assertEqual(result["margin"],0)
    def test_single_class_cannot_establish_margin(self):
        entry=(np.zeros((24,16)),.5)
        self.assertIsNone(nearest(entry,[("0",entry)]))
    def test_competing_segmentations_abstain(self):
        patch_image=np.zeros((16,16))
        # Different masks, not eight identical crops with contradictory mocked results.
        pieces=[[np.full((12,5),.7+i*.01)] for i in range(8)]
        with patch("automatic_glyph_audit.segment",side_effect=pieces),patch("automatic_glyph_audit.feature",return_value=(np.ones((24,16)),.5)),patch("automatic_glyph_audit.GlyphBank.nearest",side_effect=[{"label":str(i%2),"distance":.01,"margin":.1} for i in range(8)]) as matcher:
            result=predict_amount(patch_image,[])
        self.assertEqual(matcher.call_count,8)
        self.assertIsNone(result["candidate"])
        self.assertEqual(result["reason"],"conflicting segmentations")
    def test_inference_never_receives_label(self):
        a=np.zeros((24,20));a[3:21,4:8]=200;a[3:21,12:16]=180
        with patch("automatic_glyph_audit.predict_amount",return_value={"candidate":None,"readings":[]}) as fn:
            amount_audit([("a","11",a,"a"),("b","22",a,"b")])
        for call in fn.call_args_list:
            self.assertEqual(len(call.args),2)
        self.assertEqual(set(fn.call_args_list[0].args[1].labels),{"2"})
        self.assertEqual(set(fn.call_args_list[1].args[1].labels),{"1"})
    def test_blank_card_feature(self):
        self.assertIsNone(card_feature(Image.new("RGB",(20,30),"white"),False))
    def test_unknown_card_is_not_a_false_positive(self):
        im=Image.new("RGB",(20,30),"white")
        r=card_audit([("a","As",im,im,"a"),("b","Kd",im,im,"b")],True)
        self.assertEqual(r["missing"],2)
        self.assertEqual(r["incorrect"],0)
    def test_counts_wrong_missing_and_correct(self):
        r=summarize([{"candidate":"5","expected":"5"},{"candidate":None,"expected":"2"},{"candidate":"1","expected":"7"}])
        self.assertEqual((r["correct"],r["missing"],r["incorrect"]),(1,1,1))

if __name__=="__main__":
    unittest.main()
