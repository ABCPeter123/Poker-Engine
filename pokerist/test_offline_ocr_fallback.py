import unittest
from unittest.mock import patch
from PIL import Image
from offline_ocr_fallback import amount_fallback,board_rank_fallback
class OfflineFallbackTests(unittest.TestCase):
    def test_numeric_agreement(self):
        im=Image.new("L",(60,20))
        with patch("offline_ocr_fallback.single_word",side_effect=[("22825",31),("22825",13)]):
            self.assertEqual(amount_fallback(im,"test"),"22825")
        with patch("offline_ocr_fallback.single_word",side_effect=[("22825",99),("22835",99)]):
            self.assertIsNone(amount_fallback(im,"test"))
        with patch("offline_ocr_fallback.single_word",side_effect=[("22825",99),("22825",0)]):
            self.assertIsNone(amount_fallback(im,"test"))
    def test_rank_whitelist(self):
        im=Image.new("RGB",(1536,709))
        for raw,confidence,expected in [("10",86,"T"),("3",95,"3"),("0",99,None),("3",40,None),("33",99,None)]:
            with patch("offline_ocr_fallback.single_word",return_value=(raw,confidence)):
                self.assertEqual(board_rank_fallback(im,547,"test"),expected)
