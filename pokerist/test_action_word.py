import unittest
from PIL import Image
from action_word import BANK,match_action,right_action
class ActionWordTests(unittest.TestCase):
    def test_calibrated_word_masks(self):
        for label,aspect,mask in BANK:
            self.assertEqual(match_action((mask,aspect))["candidate"],label)
    def test_blank_crop(self):
        self.assertIsNone(right_action(Image.new("RGB",(132,23),(90,130,160)),(0,0,132,23)))
    def test_bad_aspect_is_rejected(self):
        self.assertIsNone(match_action((BANK[0][2],8)))
