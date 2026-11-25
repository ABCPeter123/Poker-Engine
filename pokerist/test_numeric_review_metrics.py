import unittest
from numeric_review_metrics import numeric_evidence,summarize_numeric
from check_saved_frame import field_results
from benchmark_saved_frames import validate_manifest,compare_reports,gate

class NumericReviewTests(unittest.TestCase):
    def test_raw_correct_but_unaccepted(self):
        r={"number_candidates":{"pot":{"raw":"4.5K","candidate":None,"ocr_confidence":0}}}
        rows=numeric_evidence(r,{"amounts":{"pot":4500}})
        s=summarize_numeric(rows)
        self.assertEqual(s["raw_by_method"]["primary"]["match"],1)
        self.assertEqual(s["accepted"]["missing"],1)
    def test_conflicting_accepted_candidate_is_missing(self):
        r={"number_candidates":{"pot":{"raw":"450","candidate":{"value":450},
             "saved_line_status":"conflicting readings","saved_line_evidence":[{"raw":"430","method":"stretch","confidence":90}]}}}
        expected={"amounts":{"pot":450}}
        rows=numeric_evidence(r,expected)
        self.assertEqual(rows[0]["accepted_status"],"missing")
        self.assertEqual(field_results(r,expected)[0]["status"],"missing")
        self.assertEqual(summarize_numeric(rows)["conflicts"],1)
        self.assertEqual(summarize_numeric(rows)["raw_by_method"]["stretch"]["incorrect"],1)
    def test_zero_and_approximation(self):
        r={"number_candidates":{"hero":{"raw":"0","candidate":{"value":0}},
             "pot":{"raw":"200k","candidate":{"value":200000,"approximate":True}}}}
        s=summarize_numeric(numeric_evidence(r,{"amounts":{"hero":0,"pot":200000}}))
        self.assertEqual(s["accepted"]["match"],2)
        self.assertEqual(s["approximate_accepted"],1)
    def test_unlabelled_amounts_not_scored(self):
        self.assertEqual(numeric_evidence({"number_candidates":{"pot":{"raw":"500"}}},{}),[])
    def test_invalid_numeric_labels_rejected(self):
        for labels in ({"pot":True},{"hero":-1},{"hero":1.5},{"unknown":0},{"hero":None}):
            with self.assertRaises(ValueError):
                validate_manifest({"cases":[{"file":"a.png","expected":{"hole_slots":[None]*2,"board_slots":[None]*5,"amounts":labels}}]})
    def test_crop_changes_not_paired(self):
        row={"field":"amount.pot","expected":10,"actual":10,"status":"match"}
        a={"file":"a","variant":"original","sha256":"abc","fields":[row],"crop":[0,0,10,10]}
        b={**a,"crop":[1,1,11,11]}
        result=compare_reports({"details":[b]},{"details":[a]})
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["unpaired"]),1)
    def test_ocr_error_blocks_gate(self):
        report={"frames_processed":1,"errors":[],"variants":{"original":{"ocr_errors":1,"groups":{"visible_cards":{"accuracy":1,"incorrect":0,"missing":0}}}}}
        self.assertFalse(gate(report,1,0))
if __name__=="__main__":
    unittest.main()
