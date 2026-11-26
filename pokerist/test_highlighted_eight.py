import unittest
from PIL import Image,ImageDraw
import numpy as np
from review import BOARD,RANKS,SUITS,decode,rank_match,match,glyph_holes,highlighted_red_glyph,highlighted_board_corner,ink_masks

# Fixed rank/suit crops from the supplied 2026-11-26 dashboard image.
# Reconstructed at 1536, 960, 720 and 480 px before normalization.
PAIRS=[["3f8,79e,e06,e06,e06,e0e,71c,7fc,7fc,f0e,e07,e07,e07,e0f,7fe,3fc","040,0f0,0f0,1f8,3f8,3fc,7fe,fff,fff,fff,7fe,3fc,1f8,1f0,0f0,060"],["1f8,38c,70e,606,706,706,79e,3fc,7fe,706,e07,e07,607,70e,3de,1fc","060,0f0,1f0,3f8,3fc,7fe,fff,fff,fff,fff,7fe,3fc,1f8,1f0,0f0,060"],["1f8,38e,70e,606,606,706,3de,3fc,7fe,706,e07,e07,607,70f,3fe,1f8","060,0f0,1f0,1f8,3fc,7fe,fff,fff,fff,fff,7fe,3fc,1f8,0f0,0f0,060"],["1f0,3f8,606,e06,e06,e06,70e,7fc,7fc,7be,e07,e07,e07,e07,79e,7fc","060,0f0,1f0,3f8,3fc,7fe,fff,fff,fff,fff,7fe,3fc,1f8,0f0,0f0,040"]]

class HighlightedEightTests(unittest.TestCase):
    def test_saved_red_corner_masks(self):
        for rank,suit in PAIRS:
            self.assertEqual(glyph_holes(decode(rank)),2)
            self.assertEqual(rank_match(decode(rank))[0],"8")
            self.assertEqual(match(decode(suit),{k:v for k,v in SUITS.items() if k[0] in "dh"},.18)[0],"d")
    def test_red_ink_removed_by_gold_mask_is_preserved(self):
        im=Image.new("RGB",(24,32),"white")
        a=np.asarray(decode(PAIRS[0][0]),dtype=np.uint8)
        expanded=np.repeat(np.repeat(a,2,axis=0),2,axis=1).astype(bool)
        pixels=np.full((32,24,3),240,dtype=np.uint8)
        pixels[expanded]=(180,100,65)
        self.assertFalse(ink_masks(pixels)[0].any())
        self.assertEqual(rank_match(highlighted_red_glyph(Image.fromarray(pixels),(0,0,24,32)))[0],"8")
    def test_missing_board_is_not_invented(self):
        self.assertIsNone(highlighted_board_corner(Image.new("RGB",(1536,709),(90,130,160)),BOARD[1]))
    def test_highlighted_red_card_with_clean_corner(self):
        im=Image.new("RGB",(1536,709),(90,130,160))
        rankbox,suitbox,body=BOARD[1]
        draw=ImageDraw.Draw(im)
        draw.rectangle(body,fill=(235,235,235),outline=(220,170,25),width=4)
        for box,mask in zip((rankbox,suitbox),PAIRS[0]):
            pixels=np.full((16,12,3),235,dtype=np.uint8)
            pixels[decode(mask)]=(180,100,65)
            # Keep original mask aspect and enough neutral face area.
            im.paste(Image.fromarray(pixels).resize((24,32),Image.Resampling.NEAREST) if box==rankbox else Image.fromarray(pixels).resize((24,26),Image.Resampling.NEAREST),box[:2])
        self.assertEqual(highlighted_board_corner(im,BOARD[1])["candidate"],"8d")
