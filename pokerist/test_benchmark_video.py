import io
import unittest
from benchmark_video import read_exact, summarize

class VideoBenchmarkTests(unittest.TestCase):
    def test_throughput_and_latency_are_distinct(self):
        report=summarize(120,[5]*119+[20],1.5,True,True,[])
        self.assertTrue(report["throughput_pass"])
        self.assertFalse(report["strict_frame_budget_pass"])
        self.assertEqual(report["frames_over_budget"],1)
        self.assertFalse(report["full_field_accuracy_verified"])
    def test_missing_frame_or_source_gap_fails(self):
        self.assertFalse(summarize(120,[5]*119,1,True,True,[])["throughput_pass"])
        self.assertFalse(summarize(120,[5]*120,1,False,True,[])["throughput_pass"])
        self.assertFalse(summarize(120,[5]*120,3,True,True,[])["throughput_pass"])
    def test_ocr_error_fails(self):
        self.assertFalse(summarize(120,[5]*120,1,True,True,[{"error":"OCR"}])["throughput_pass"])
    def test_read_exact(self):
        s=io.BytesIO(b"abcdef")
        self.assertEqual(read_exact(s,3),b"abc")
        self.assertEqual(read_exact(s,3),b"def")
        self.assertIsNone(read_exact(s,3))
        with self.assertRaises(EOFError):
            read_exact(io.BytesIO(b"ab"),3)

if __name__=="__main__":
    unittest.main()
