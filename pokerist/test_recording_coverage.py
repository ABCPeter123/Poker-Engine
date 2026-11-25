import unittest
from unittest.mock import patch
from PIL import Image
from audit_recording import audit_frames
from saved_bar_evidence import evidence_crop,raw_passes

def frames(*values):
    return [{"best_effort_timestamp_time":v} for v in values]

class RecordingCoverageTests(unittest.TestCase):
    def test_regular_recording(self):
        r=audit_frames(frames(0,.033,.067,.1),40)
        self.assertTrue(r["coverage_pass"])
        self.assertEqual(r["max_gap_ms"],34)
    def test_gap_and_missed_event(self):
        r=audit_frames(frames(0,.033,.5,.533),100,[{"start_s":.1,"end_s":.2}])
        self.assertFalse(r["coverage_pass"])
        self.assertEqual(len(r["large_gaps"]),1)
        self.assertEqual(r["labelled_windows"][0]["frames_in_window"],0)
    def test_duplicate_invalid_and_reordered_timestamps(self):
        r=audit_frames(frames(0,.1,.05,.05,"N/A"),200)
        self.assertEqual(r["duplicate_timestamps"],1)
        self.assertEqual(r["backwards_timestamps"],1)
        self.assertEqual(r["missing_timestamps"],1)
        self.assertFalse(r["coverage_pass"])
    def test_event_end_is_exclusive(self):
        r=audit_frames(frames(0,.1,.2,.3),110,[{"start_s":.1,"end_s":.2}])
        self.assertEqual(r["labelled_windows"][0]["frames_in_window"],1)
        self.assertTrue(r["coverage_pass"])
    def test_outside_coverage_and_invalid_windows(self):
        self.assertFalse(audit_frames(frames(0,.1),200,[{"start_s":-.1,"end_s":.05}])["coverage_pass"])
        with self.assertRaises(ValueError):
            audit_frames(frames(0,.1),200,[{"start_s":.2,"end_s":.1}])
    def test_empty_or_one_frame_cannot_pass(self):
        self.assertFalse(audit_frames([])["coverage_pass"])
        self.assertFalse(audit_frames(frames(0))["coverage_pass"])

class SavedBarEvidenceTests(unittest.TestCase):
    def test_crop_preserves_original_pixels(self):
        im=Image.new("RGB",(100,50),(12,34,56))
        crop,box=evidence_crop(im,(5,40,95,48))
        self.assertEqual(crop.size,(90,8))
        self.assertEqual(crop.getpixel((0,0)),(12,34,56))
        self.assertEqual(box,(5,40,95,48))
    def test_invalid_crop_rejected(self):
        with self.assertRaises(ValueError):
            evidence_crop(Image.new("RGB",(100,50)),(0,40,101,50))
    def test_missing_ocr_preserves_explicit_error(self):
        with patch("saved_bar_evidence.subprocess.run",side_effect=OSError("unavailable")):
            readings=raw_passes(Image.new("RGB",(100,20)),"missing")
        self.assertEqual(len(readings),2)
        self.assertTrue(all(r["raw"]=="" and "error" in r for r in readings))

if __name__=="__main__":
    unittest.main()
