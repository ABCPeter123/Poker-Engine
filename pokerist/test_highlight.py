import unittest
import numpy as np
from PIL import Image
from review import ink_masks, glyph, decode, match, RANKS, SUITS, lower_corner, BOARD
from table_observation import participation_label

class HighlightTests(unittest.TestCase):
    def test_gold_is_not_rank_ink(self):
        pixels=np.array([[[255,210,20],[210,150,15],[180,28,42],[32,33,38],[240,240,240]]],dtype=np.int16)
        red,black=ink_masks(pixels)
        self.assertEqual(red.tolist(),[[False,False,True,False,False]])
        self.assertEqual(black.tolist(),[[False,False,False,True,False]])
    def test_gold_outline_does_not_change_glyph(self):
        a=np.full((40,30,3),235,dtype=np.uint8)
        a[8:30,12:16]=[30,30,30]
        a[26:30,6:16]=[30,30,30]
        plain=glyph(Image.fromarray(a),(0,0,30,40),"black")
        a[:5]=[255,210,20];a[:,:4]=[255,210,20]
        outlined=glyph(Image.fromarray(a),(0,0,30,40),"black")
        np.testing.assert_array_equal(plain,outlined)
    def test_rank_coverage(self):
        self.assertEqual(set(k.split("_")[0] for k in RANKS),set("23456789TJQKA"))
        self.assertEqual(set(k.split("_")[0] for k in SUITS),set("cdhs"))
    def test_new_templates_self_match(self):
        for k in ("K_corner1","A_corner1","2_cornerred","5_corner","J_highlightboard","J_highlighthole"):
            self.assertEqual(match(decode(RANKS[k]),RANKS)[0],k.split("_")[0])
    def test_lower_corner_keeps_card_region(self):
        self.assertEqual(lower_corner(BOARD[0])[2],BOARD[0][2])
    def test_no_participation_is_not_a_fold(self):
        self.assertEqual(participation_label(None,False),"No participation detected")
        self.assertEqual(participation_label(None,True),"Participation evidence")
        self.assertEqual(participation_label(None,False,True),"Participation evidence")
        self.assertEqual(participation_label("Fold",False),"Fold")

if __name__=="__main__":unittest.main()
