import unittest
from unittest.mock import patch
import numpy as np
from hybrid_amount_audit import consensus,endpoint_parts,parse_vision_response,measure

class HybridAmountTests(unittest.TestCase):
    def test_conflict_not_resolved_by_majority(self):
        self.assertEqual(consensus({"glyph":"1500","ocr":"1500","vision":"1300"})["status"],"conflict")
        self.assertIsNone(consensus({"glyph":"1500","ocr":None})["candidate"])
        self.assertEqual(consensus({"glyph":"1,500","ocr":"1500"})["candidate"],(1500,False,None))
        self.assertIsNone(consensus({"glyph":"1.5K","ocr":"1500"})["candidate"])
    def test_strict_response_and_local_only(self):
        self.assertEqual(parse_vision_response('{"text":"1500"}'),"1500")
        for content in ('{"text":1500}','{"text":"1500 maybe"}','{"text":null}','{"text":"1500","confidence":1}','1500'):
            self.assertIsNone(parse_vision_response(content))
        endpoint_parts("http://127.0.0.1:8081/v1/chat/completions")
        for url in ("https://example.com/v1/chat/completions","http://localhost:8081/other","http://localhost:8081@evil.com/v1/chat/completions"):
            with self.assertRaises(ValueError):endpoint_parts(url)
    def test_vision_reader_sees_only_crop_and_scores_separately(self):
        patch_a=np.zeros((10,10))
        samples=[("a","100",patch_a,"a"),("b","200",patch_a,"b")]
        with patch("hybrid_amount_audit.fit_amount",return_value=[]),patch("hybrid_amount_audit.predict_amount",return_value={"candidate":"100"}),patch("hybrid_amount_audit.ocr_reader",return_value="100"):
            report=measure(samples,"fake",lambda image:"200")
        self.assertEqual(report["scores"]["two_reader"],{"correct":1,"incorrect":1,"unknown":0})
        self.assertEqual(report["scores"]["ensemble"]["unknown"],2)
        self.assertEqual(report["vision_calls"],2)
