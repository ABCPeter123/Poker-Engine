import unittest
from PIL import Image
from frame_crop import game_bounds

class CropTests(unittest.TestCase):
    def test_clean_landscape(self):
        image=Image.new("RGB",(1102,511),(40,80,115))
        self.assertEqual(game_bounds(image),(0,0,1102,511))
    def test_windows_title_bar(self):
        image=Image.new("RGB",(1102,540),(242,242,242))
        image.paste((40,80,115),(0,29,1102,540))
        self.assertEqual(game_bounds(image),(0,29,1102,540))
    def test_black_letterbox(self):
        image=Image.new("RGB",(1102,900),(0,0,0))
        image.paste((40,80,115),(0,194,1102,705))
        self.assertEqual(game_bounds(image),(0,194,1102,705))
    def test_reject_wrong_shape(self):
        with self.assertRaises(ValueError):
            game_bounds(Image.new("RGB",(600,600),(40,80,115)))
    def test_blank_frame(self):
        with self.assertRaises(ValueError):
            game_bounds(Image.new("RGB",(1102,511),(0,0,0)))

if __name__=="__main__":
    unittest.main()
