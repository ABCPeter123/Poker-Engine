import unittest
import numpy as np
from benchmark_hybrid import synthetic_samples

class HybridSyntheticTests(unittest.TestCase):
    def test_groups_are_disjoint_and_deterministic(self):
        a,b=synthetic_samples(),synthetic_samples()
        self.assertEqual(len(a),32)
        self.assertEqual(len({x[0] for x in a}),4)
        self.assertEqual(len({x[1] for x in a}),len(a))
        for x,y in zip(a,b):
            self.assertTrue(np.array_equal(x[2],y[2]))
            self.assertGreater(x[2].max()-x[2].min(),100)
