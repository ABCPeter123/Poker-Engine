import json,unittest
from pathlib import Path
import numpy as np
from offline_font_review import stack_crop,amount_crop,STACKS,AMOUNTS
from offline_card_audit import board_features
from offline_ring_audit import markers
class OfflineCropTests(unittest.TestCase):
    def test_blank_regions_abstain(self):
        a=np.zeros((709,1536,3),dtype=np.uint8)
        for x,y in STACKS.values():self.assertIsNone(stack_crop(a,x,y))
        for key in AMOUNTS:self.assertIsNone(amount_crop(a,key))
        for i in range(5):self.assertIsNone(board_features(a,i))
        self.assertIsNone(markers(a)["active"])
        self.assertIsNone(markers(a)["winner_ring"])
    def test_manifest_counts_and_nulls(self):
        root=Path(__file__).parent/"fixtures"
        a=json.loads((root/"glyph_amount_nov25_final.json").read_text())
        self.assertEqual(len(a["lines"]),55)
        self.assertEqual(sum(r["label"] is None for r in a["lines"]),20)
        b=json.loads((root/"board_ring_nov25.json").read_text())
        self.assertEqual(len(b["frames"]),22)
        self.assertEqual(len({r["group"] for r in b["frames"]}),5)
        self.assertEqual(sum(c is not None for r in b["frames"] for c in r["board"]),73)
        self.assertEqual(len(b["image_sha256"]),22)
