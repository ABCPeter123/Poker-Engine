import unittest
from start_mirror import parse_geometry, parse_sink_geometry, fit_size, auth_options, receiver_id
class MirrorGeometryTests(unittest.TestCase):
    def test_landscape_geometry(self):
        self.assertEqual(parse_geometry("*** codec is h264: geometry is (w,h)=(1920,1088) (source); (x,y)=(0,0); (w,h)=(1920,1080)"),(1920,1080))
    def test_portrait_geometry(self):
        self.assertEqual(parse_geometry("geometry is (w,h)=(1088,1920) (source); (x,y)=(0,0); (w,h)=(1080,1920)"),(1080,1920))
    def test_unrelated_or_invalid_log(self):
        self.assertIsNone(parse_geometry("AirPlay connection request"))
        self.assertIsNone(parse_geometry("geometry is (w,h)=(1920,1080) (source); (x,y)=(0,0); (w,h)=(3000,1080)"))
    def test_sink_orientation_changes(self):
        line = "DEBUG d3d11videosink gstd3d11videosink.cpp:123:gst_d3d11_video_sink_set_caps: set caps video/x-raw(memory:D3D11Memory), width=(int)1920, height=(int)886, pixel-aspect-ratio=(fraction)1/1"
        self.assertEqual(parse_sink_geometry(line), (1920, 886))
        self.assertEqual(parse_sink_geometry(line.replace("1920", "886").replace("height=(int)886", "height=(int)1920")), (886, 1920))
    def test_sink_ignores_capability_ranges(self):
        self.assertIsNone(parse_sink_geometry("DEBUG d3d11videosink get caps width=(int)[ 1, 8192 ], height=(int)[ 1, 8192 ]"))
        self.assertIsNone(parse_sink_geometry("DEBUG unrelated set caps width=(int)1920, height=(int)886"))
    def test_pixel_aspect_ratio(self):
        self.assertEqual(parse_sink_geometry("DEBUG d3d11videosink set caps width=(int)720, height=(int)576, pixel-aspect-ratio=(fraction)16/15"), (768, 576))
    def test_auth_modes(self):
        self.assertEqual(auth_options("password", "Example123"), ["-pw", "Example123"])
        self.assertEqual(auth_options("random"), ["-pw"])
        self.assertEqual(auth_options("pin"), ["-pin"])
        with self.assertRaises(ValueError):
            auth_options("password", "short")
    def test_receiver_id(self):
        first = receiver_id(123, "password")
        self.assertEqual(first, receiver_id(123, "password"))
        self.assertNotEqual(first, receiver_id(123, "pin"))
        self.assertEqual(int(first.split(":")[0], 16) & 3, 2)
    def test_fit(self):
        self.assertEqual(fit_size(1920,1080,960,700),(960,540))
        self.assertEqual(fit_size(1080,1920,960,640),(360,640))
if __name__ == "__main__":
    unittest.main()
