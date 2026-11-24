import unittest
from review import number_text, NUMBERS
class NumberCropTests(unittest.TestCase):
    def test_rounded_pot_trailing_punctuation(self):
        self.assertEqual(number_text("1.5K.")["value"],1500)
        self.assertTrue(number_text("1.5K.")["approximate"])
    def test_invalid_text_not_guessed(self):
        self.assertIsNone(number_text("SB 000"))
        self.assertIsNone(number_text("$9850"))
    def test_upper_left_crop_wider(self):
        x,_,right,_=NUMBERS["upper_left"]
        self.assertGreaterEqual(right-x,60)
if __name__=="__main__":unittest.main()
