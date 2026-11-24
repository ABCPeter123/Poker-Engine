import unittest
from start_mirror import parse_geometry, fit_size
class MirrorGeometryTests(unittest.TestCase):
    def test_landscape_geometry(self):
        self.assertEqual(parse_geometry("*** codec is h264: geometry is (w,h)=(1920,1088) (source); (x,y)=(0,0); (w,h)=(1920,1080)"),(1920,1080))
    def test_portrait_geometry(self):
        self.assertEqual(parse_geometry("geometry is (w,h)=(1088,1920) (source); (x,y)=(0,0); (w,h)=(1080,1920)"),(1080,1920))
    def test_unrelated_or_invalid_log(self):
        self.assertIsNone(parse_geometry("AirPlay connection request"))
        self.assertIsNone(parse_geometry("geometry is (w,h)=(1920,1080) (source); (x,y)=(0,0); (w,h)=(3000,1080)"))
    def test_fit(self):
        self.assertEqual(fit_size(1920,1080,960,700),(960,540))
        self.assertEqual(fit_size(1080,1920,960,640),(360,640))
if __name__ == "__main__":
    unittest.main()
