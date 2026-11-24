import unittest
import numpy as np
from PIL import Image, ImageDraw
from card_geometry import gold_mask, face_bounds, corner_regions
from review import card, BOARD

class CardGeometryTests(unittest.TestCase):
    def make_face(self,highlight=False):
        im=Image.new("RGB",(1536,709),(75,120,150))
        d=ImageDraw.Draw(im)
        d.rectangle((548,242,627,352),fill=(245,190,15) if highlight else (230,230,230))
        d.rectangle((552,246,623,348),fill=(235,235,235))
        return im
    def test_gold_exclusion(self):
        a=np.array([[[255,210,20],[210,150,15],[180,28,42],[32,33,38]]])
        self.assertEqual(gold_mask(a).tolist(),[[True,True,False,False]])
    def test_highlighted_face_is_present(self):
        im=self.make_face(True)
        self.assertEqual(face_bounds(im,BOARD[0][2]),(552,246,624,349))
        self.assertIsNotNone(card(im,BOARD[0]))
        self.assertIsNone(card(im,BOARD[0])["candidate"])
    def test_face_bounds_anchor_moves(self):
        im=self.make_face(True)
        opts=corner_regions(im,BOARD[0])
        self.assertIn((BOARD[0][0],BOARD[0][1]),opts)
        self.assertIn(((556,248,581,285),(555,286,581,313)),opts)
    def test_logo_not_face(self):
        im=Image.new("RGB",(1536,709),(75,120,150))
        ImageDraw.Draw(im).rectangle((553,268,620,285),fill=(220,220,220))
        self.assertIsNone(face_bounds(im,BOARD[0][2]))
        self.assertIsNone(card(im,BOARD[0]))
    def test_partial_hole_strip(self):
        im=Image.new("RGB",(1536,709),(75,120,150))
        ImageDraw.Draw(im).rectangle((813,477,831,540),fill=(235,235,235))
        spec=((813,473,835,507),(810,510,837,540),(811,471,836,544))
        self.assertTrue(corner_regions(im,spec))

if __name__=="__main__":unittest.main()
