import json
import unittest
from pathlib import Path
from collections import Counter
class AdditionalFontManifestTests(unittest.TestCase):
    def test_independent_groups(self):
        root=Path(__file__).parent/"fixtures"
        old=json.loads((root/"glyph_amount_nov25.json").read_text())
        new=json.loads((root/"glyph_amount_nov25_additional.json").read_text())
        self.assertEqual(len(new["lines"]),62)
        self.assertEqual(len(set(r["label"] for r in new["lines"])),19)
        self.assertEqual(Counter(r["group"] for r in new["lines"]),{"hand3":4,"hand4":58})
        self.assertFalse(set(old["image_sha256"]) & set(new["image_sha256"]))
        self.assertFalse({r["group"] for r in old["lines"]} & {r["group"] for r in new["lines"]})
        for r in new["lines"]:
            self.assertTrue(r["label"].isdigit())
            self.assertIn(r["file"],new["image_sha256"])
            x,y,a,b=r["box"]
            self.assertTrue(0<=x<a<=1536 and 0<=y<b<=709)
