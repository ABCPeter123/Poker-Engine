import unittest
from amount_text import number_text
from contrast_amounts import prepare_contrast_line,scan_contrast_regions
from PIL import Image, ImageDraw

class AmountGrammarTests(unittest.TestCase):
    def test_compact_amounts(self):
        for text,amount,step in (("4k",4000,"1000"),("5K",5000,"1000"),
            ("200k",200000,"1000"),("4.5K",4500,"100.0"),("1.25m",1250000,"10000.00")):
            with self.subTest(text=text):
                r=number_text(text)
                self.assertEqual(r["value"],amount)
                self.assertTrue(r["approximate"])
                self.assertEqual(float(r["display_step"]),float(step))
        self.assertEqual(number_text("4 K")["value"],4000)
        self.assertEqual(number_text("1.5K.")["value"],1500)
    def test_grouped_integers(self):
        for s in ("19950","19 950","19,950","19\u202f950"):
            self.assertEqual(number_text(s)["value"],19950)
        self.assertEqual(number_text("0")["value"],0)
    def test_reject_ambiguous_and_overflow(self):
        for s in ("","1O0","1 2 3","4 5K","1.5","1,500K","4.0001K","4KM","-4K","1e3","9007199254740992"):
            self.assertIsNone(number_text(s),s)
    def test_contrast_blank_has_no_text(self):
        im=Image.new("RGB",(180,40),(60,85,100))
        self.assertIsNone(prepare_contrast_line(im,(0,0,180,40),"stack"))
        self.assertEqual(scan_contrast_regions(im,None,{"hero":(0,0,180,40)})["hero"]["raw"],"")
    def test_contrast_keeps_grayscale(self):
        im=Image.new("RGB",(170,31),(60,85,100))
        d=ImageDraw.Draw(im)
        d.rectangle((40,8,52,22),fill="white")
        d.rectangle((58,8,68,22),fill=(220,220,220))
        d.rectangle((72,8,80,22),fill=(180,180,180))
        crop=prepare_contrast_line(im,(0,0,170,31),"stack")
        self.assertIsNotNone(crop)
        self.assertGreater(len(crop.getcolors(100000)),2)

if __name__=="__main__":
    unittest.main()
