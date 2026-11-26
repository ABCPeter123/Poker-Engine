import unittest
from unittest.mock import patch
from review import RANKS,decode,glyph_holes,rank_match
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
