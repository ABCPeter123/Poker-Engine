import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from review import read_cards,BOARD
from adaptive_labels import RegionOCRCache

class CardRegionCacheTests(unittest.TestCase):
    def test_exact_region_cache_matches_uncached_and_invalidates_on_change(self):
        im=Image.new("RGB",(1536,709),(70,120,150))
        cache=RegionOCRCache()
        first=read_cards(im,cache)
        with patch("review.card",side_effect=AssertionError("unchanged card was rescanned")):
            self.assertEqual(read_cards(im,cache),first)
        changed=im.copy()
        ImageDraw.Draw(changed).rectangle(BOARD[2][2],fill=(240,240,240))
        self.assertEqual(read_cards(changed,cache),read_cards(changed))
        self.assertNotEqual(read_cards(changed,cache),first)

if __name__=="__main__":
    unittest.main()
