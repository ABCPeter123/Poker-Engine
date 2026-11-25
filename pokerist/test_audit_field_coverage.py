import unittest
from audit_field_coverage import audit,FIELDS

def frame(rows,elapsed=20):
    return {"file":"a.png","variant":"original","fields":rows,"elapsed_ms":elapsed}

def row(field,status="match"):
    return {"field":field,"status":status}

class FieldCoverageTests(unittest.TestCase):
    def test_required_fields(self):
        self.assertEqual(len(FIELDS),20)
        self.assertEqual(len(set(FIELDS)),20)
    def test_partial_labels_do_not_pass(self):
        r=audit({"details":[frame([row("amount.hero")])],"expected_frames":1})
        v=r["variants"]["original"]
        self.assertEqual(v["fields"]["bet.hero"]["untested"],1)
        self.assertIsNone(v["fields"]["bet.hero"]["accuracy_when_tested"])
        self.assertFalse(r["complete_validation"])
    def test_all_fields(self):
        r=audit({"details":[frame([row(f) for f in FIELDS])],"expected_frames":1})
        self.assertTrue(r["complete_validation"])
        self.assertEqual(r["variants"]["original"]["sequential_equivalent_fps"],50)
    def test_incorrect_and_missing_distinct(self):
        r=audit({"details":[frame([row("turn","incorrect"),row("dealer","missing")])],"expected_frames":1})
        v=r["variants"]["original"]["fields"]
        self.assertEqual(v["turn"]["incorrect"],1)
        self.assertEqual(v["dealer"]["missing"],1)
    def test_duplicate_frame_or_field_rejected(self):
        f=frame([row("turn")])
        with self.assertRaises(ValueError):
            audit({"details":[f,f]})
        with self.assertRaises(ValueError):
            audit({"details":[frame([row("turn"),row("turn")])]})
    def test_unprocessed_expected_frame_fails(self):
        self.assertFalse(audit({"details":[frame([row(f) for f in FIELDS])],"expected_frames":2})["complete_validation"])
    def test_empty_report_fails(self):
        self.assertFalse(audit({"details":[],"expected_frames":0})["complete_validation"])

if __name__=="__main__":
    unittest.main()
