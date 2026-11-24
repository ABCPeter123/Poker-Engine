import unittest
from PIL import Image, ImageDraw
from review import face_present, card, BOARD, HOLE, HOLE_MIRROR, RANKS, SUITS, decode, match
import numpy as np

class CardFaceTests(unittest.TestCase):
    def test_logo_like_letters_not_card(self):
        image=Image.new("RGB",(1536,709),(75,120,150))
        draw=ImageDraw.Draw(image)
        for _,_,box in BOARD:
            x,y,_,_=box
            for dx in (4,25,46):
                draw.rectangle((x+dx,y+27,x+dx+14,y+75),fill=(167,202,215))
        self.assertTrue(all(card(image,spec) is None for spec in BOARD))
    def test_white_face_without_known_glyph_stays_unknown(self):
        image=Image.new("RGB",(1536,709),(75,120,150))
        ImageDraw.Draw(image).rectangle(BOARD[0][2],fill=(235,235,235))
        self.assertTrue(face_present(image,BOARD[0][2]))
        self.assertIsNone(card(image,BOARD[0])["candidate"])
    def test_calibrated_glyph_variants(self):
        for label in ("J_mirror","3_mirror","9_black"):
            self.assertEqual(match(decode(RANKS[label]),RANKS)[0],label.split("_")[0])
        for label in ("h_mirror","s_mirror","s_black"):
            self.assertEqual(match(decode(SUITS[label]),SUITS)[0],label.split("_")[0])

if __name__=="__main__":
    unittest.main()
