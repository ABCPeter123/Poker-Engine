import unittest
import json
from pathlib import Path
from collections import Counter
from tempfile import TemporaryDirectory
from PIL import Image
from glyph_audit import read_samples

class RealFontManifestTests(unittest.TestCase):
    def test_nov25_fixture(self):
        p=Path(__file__).parent/"fixtures"/"glyph_amount_nov25.json"
        m=json.loads(p.read_text(encoding="utf-8"))
        self.assertEqual(len(m["lines"]),48)
        self.assertEqual(len(m["image_sha256"]),7)
        self.assertEqual(Counter(x["group"] for x in m["lines"]),{"hand1":19,"hand2":29})
        self.assertEqual(sum(x["label"].isdigit() for x in m["lines"]),44)
        for x in m["lines"]:
            self.assertIn(x["file"],m["image_sha256"])
            a,b,c,d=x["box"]
            self.assertTrue(0<=a<c<=1536 and 0<=b<d<=709)
        self.assertEqual(sum(x["name"]=="showdown_payout_ul" for x in m["lines"]),1)
    def test_changed_source_rejected(self):
        with TemporaryDirectory() as d:
            root=Path(d)
            Image.new("RGB",(20,20)).save(root/"a.png")
            m={"image_sha256":{"a.png":"0"*64},"lines":[{"file":"a.png","label":"5","group":"a","box":[0,0,10,10]}]}
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                read_samples(root,m)
