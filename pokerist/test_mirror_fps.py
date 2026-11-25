import unittest
from pathlib import Path
class MirrorFPSDefaultTests(unittest.TestCase):
    def test_receiver_uses_configured_fps_not_fixed_30(self):
        source=(Path(__file__).resolve().parents[1]/"start_mirror.py").read_text(encoding="utf-8")
        self.assertIn('choices=(30,60), default=60',source)
        self.assertIn('"-fps", str(args.fps)',source)
        self.assertNotIn('"-fps", "30"',source)
