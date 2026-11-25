import unittest
import numpy as np
from automatic_glyph_audit import GlyphBank,nearest,predict_amount

class GlyphBankTests(unittest.TestCase):
    def test_vectorized_matches_reference(self):
        rng=np.random.default_rng(123)
        library=[(str(i%10),(rng.random((24,16)),float(rng.random()))) for i in range(80)]
        bank=GlyphBank(library)
        for _ in range(50):
            q=(rng.random((24,16)),float(rng.random()))
            a,b=nearest(q,library),bank.nearest(q)
            self.assertEqual(a["label"],b["label"])
            self.assertAlmostEqual(a["distance"],b["distance"],places=12)
            self.assertAlmostEqual(a["margin"],b["margin"],places=12)
    def test_missing_and_tied_classes(self):
        p=np.zeros((24,16))
        self.assertIsNone(GlyphBank([]).nearest((p,1)))
        self.assertIsNone(GlyphBank([("1",(p,1))]).nearest((p,1)))
        bank=GlyphBank([("2",(p,1)),("1",(p,1))])
        self.assertEqual(bank.nearest((p,1)),{"label":"1","distance":0.0,"margin":0.0})
        self.assertIsNone(predict_amount(np.zeros((20,30)),bank)["candidate"])
