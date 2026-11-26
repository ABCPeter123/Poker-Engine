import unittest
from unittest.mock import patch
import numpy as np
from review import RANKS,decode,glyph_holes,rank_match,reconcile_deskewed_hole
class RankTopologyTests(unittest.TestCase):
    def test_queen_and_eight_topology(self):
        for key,value in RANKS.items():
            label=key.split("_")[0]
            if label in ("8","Q"):
                with self.subTest(key=key):
                    self.assertEqual(glyph_holes(decode(value)),2 if label=="8" else 1)
    def test_queen_shape_vetoes_false_eight(self):
        with patch("review.match",return_value=("8",.1)):
            self.assertEqual(rank_match(decode(RANKS["Q"])),(None,.1))
            self.assertEqual(rank_match(decode(RANKS["8_sample"])),("8",.1))
    def test_other_ranks_unchanged(self):
        with patch("review.match",return_value=("Q",.1)):
            self.assertEqual(rank_match(decode(RANKS["Q"])),("Q",.1))

    def test_single_pixel_dropout_on_saved_eight_and_queen_templates(self):
        for key,value in RANKS.items():
            label=key.split("_")[0]
            if label not in ("8","Q"):continue
            original=decode(value)
            for y,x in zip(*np.where(original)):
                damaged=original.copy()
                damaged[y,x]=False
                with self.subTest(key=key,y=y,x=x):
                    self.assertEqual(rank_match(damaged)[0],label)

    def test_three_has_no_enclosed_loops(self):
        for key,value in RANKS.items():
            if key.split("_")[0]!="3":continue
            original=decode(value)
            self.assertEqual(glyph_holes(original),0)
            self.assertEqual(rank_match(original)[0],"3")
            for y,x in zip(*np.where(original)):
                damaged=original.copy()
                damaged[y,x]=False
                self.assertEqual(glyph_holes(damaged),0)
    def test_false_three_on_closed_loop_is_rejected(self):
        with patch("review.match",return_value=("3",.1)):
            for key,value in RANKS.items():
                if key.split("_")[0] in ("8","9","Q"):
                    if glyph_holes(decode(value))>0:
                        self.assertEqual(rank_match(decode(value)),(None,.1))
            self.assertEqual(rank_match(decode(RANKS["3"])),("3",.1))
    def test_deskewed_disagreement_is_not_silently_accepted(self):
        primary={"candidate":"3c","rank_candidate":"3","suit_candidate":"c"}
        result=reconcile_deskewed_hole(primary,"8","c")
        self.assertIsNone(result["candidate"])
        self.assertEqual(result["suit_candidate"],"c")
        self.assertEqual(result["alternatives"],["3c","8c"])
        self.assertIs(reconcile_deskewed_hole(primary,"3","c"),primary)
        self.assertIs(reconcile_deskewed_hole(primary,None,None),primary)
        self.assertEqual(reconcile_deskewed_hole(None,"8","c")["candidate"],"8c")
