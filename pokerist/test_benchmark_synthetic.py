import unittest
from benchmark_synthetic import synthetic_frame
from review import WIDTH,HEIGHT
class SyntheticBenchmarkTests(unittest.TestCase):
    def test_changes_are_controlled_and_frames_are_distinct(self):
        first,a=synthetic_frame(0,3)
        second,b=synthetic_frame(1,3)
        fourth,c=synthetic_frame(3,3)
        self.assertEqual(first.size,(WIDTH,HEIGHT))
        self.assertEqual(a,b)
        self.assertNotEqual(first.tobytes(),second.tobytes())
        self.assertNotEqual(a,c)
        self.assertEqual(len(a),11)
        self.assertEqual(sum(key.startswith('bet:') for key in a),5)
