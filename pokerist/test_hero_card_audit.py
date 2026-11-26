import unittest
import json
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from offline_card_audit import enclosed_loops,rank_candidate,hero_features

class HeroCardAuditTests(unittest.TestCase):
    def test_two_loops_and_veto(self):
        a=np.zeros((24,16))
        a[2:22,2:14]=1
        a[5:10,5:11]=0
        a[14:19,5:11]=0
        q=(a,.6)
        self.assertEqual(enclosed_loops(q),2)
        with patch("offline_card_audit.nearest",return_value="8"):
            self.assertEqual(rank_candidate(q,[]),"8")
            a[2:22,2:5]=0
            a[2:22,5:6]=0
            self.assertIsNone(rank_candidate(q,[]))
    def test_blank_hero_positions(self):
        im=Image.new("RGB",(1536,709))
        self.assertIsNone(hero_features(im,0))
        self.assertIsNone(hero_features(im,1))
    def test_calibrated_hero_manifest(self):
        m=json.loads((Path(__file__).parent/"fixtures"/"board_ring_nov25.json").read_text())
        rows=[r for r in m["frames"] if "hero" in r]
        self.assertEqual(len(rows),21)
        self.assertEqual(sum(c is not None for r in rows for c in r["hero"]),35)
        self.assertEqual(sum(c is None for r in rows for c in r["hero"]),7)
        self.assertNotIn("hero",next(r for r in m["frames"] if r["file"]=="IMG_0429.jpeg"))
