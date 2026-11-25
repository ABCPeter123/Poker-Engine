import json
import unittest
from pathlib import Path
from audit_manifest import audit_manifest
class ManifestAuditTests(unittest.TestCase):
    def test_explicit_zero_and_empty_are_labels(self):
        r=audit_manifest({"cases":[{"file":"a.png","expected":{"hole_slots":[None]*2,"board_slots":[None]*5,"bets":{"hero":0}}}]})
        self.assertEqual(r["labelled"],8)
        self.assertEqual(r["fields"]["bet.hero"]["labelled"],1)
        self.assertEqual(r["fields"]["bet.left"]["labelled"],0)
        self.assertIn("bet.left",r["missing_by_file"][0]["missing_labels"])
        self.assertFalse(r["complete"])
    def test_actual_calibration_corpus(self):
        path=Path(__file__).with_name("fixtures")/"saved_corpus.json"
        r=audit_manifest(json.loads(path.read_text(encoding="utf-8")))
        self.assertEqual(r["possible_labels"],360)
        self.assertEqual(r["labelled"],149)
        self.assertEqual(r["fully_labelled_frames"],0)
        self.assertFalse(r["recognition_accuracy_verified"])
if __name__=="__main__":
    unittest.main()
