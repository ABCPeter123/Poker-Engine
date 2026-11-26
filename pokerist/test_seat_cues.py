import unittest
import numpy as np
from PIL import Image
from seat_cues import SEATS, avatar_appearance, bar_evidence, hero_bar_evidence, label_candidate, seat_evidence

class CueTests(unittest.TestCase):
    def test_avatar_appearance(self):
        a=np.full((80,80,3),[85,100,125],dtype=np.int16)
        # Uniform blue default profiles are ambiguous, not folds.
        self.assertEqual(avatar_appearance(a)["candidate"],"silhouette")
        a[:25]=[50,50,50]
        self.assertEqual(avatar_appearance(a)["candidate"],"dimmed")
        a[25:45]=[185,120,90]
        self.assertEqual(avatar_appearance(a)["candidate"],"colored")
        a[:]=[200,200,200]
        self.assertEqual(avatar_appearance(a)["candidate"],"obscured")
        a[:]=[60,85,105]
        a[:8]=[20,150,220]
        self.assertEqual(avatar_appearance(a)["candidate"],"empty")
        a[:]=[25,25,25]
        self.assertEqual(avatar_appearance(a)["candidate"],"unknown")
    def test_gray(self):
        a=np.full((40,140,3),100,dtype=np.int16)
        self.assertFalse(bar_evidence(a)["multicolor_band_candidate"])
    def test_bright_multicolor(self):
        a=np.full((40,140,3),100,dtype=np.int16)
        a[20:24,15:45]=[40,240,50]
        a[20:24,50:90]=[240,45,40]
        self.assertTrue(bar_evidence(a)["multicolor_band_candidate"])
    def test_amber_alone_is_not_active(self):
        a=np.full((40,140,3),100,dtype=np.int16)
        a[20:24,20:90]=[240,180,35]
        self.assertFalse(bar_evidence(a)["multicolor_band_candidate"])
    def test_partial_hero_ring_requires_strong_green_span(self):
        a=np.full((43,156,3),100,dtype=np.int16)
        a[20:26,105:130]=[40,240,50]
        self.assertFalse(bar_evidence(a)["multicolor_band_candidate"])
        self.assertTrue(hero_bar_evidence(a)["hero_green_fallback"])
        a[:]=100
        a[20:26,105:130]=[240,180,35]
        self.assertFalse(hero_bar_evidence(a)["multicolor_band_candidate"])
        a[:]=100
        a[20:30,105:110]=[40,240,50]
        self.assertFalse(hero_bar_evidence(a)["multicolor_band_candidate"])
    def test_label_requires_text(self):
        self.assertTrue(label_candidate("ALL-IN"))
        self.assertTrue(label_candidate("All in"))
        self.assertFalse(label_candidate("2500"))
        self.assertFalse(label_candidate("CALL IN"))
        self.assertFalse(label_candidate("NOT ALL IN"))
    def test_darkness_and_appearance_never_imply_fold_or_departure(self):
        previous=Image.new("RGB",(1536,709),(150,150,150))
        image=Image.new("RGB",(1536,709),(70,70,70))
        evidence=seat_evidence(image,None,previous)
        for seat in evidence["seats"].values():
            self.assertTrue(seat["darkened_candidate"])
            self.assertTrue(seat["appearance_change_candidate"])
            self.assertIsNone(seat["folded"])
            self.assertIsNone(seat["departed"])
            self.assertIsNone(seat["all_in_label"]["candidate"])
        self.assertIsNone(evidence["active_band_candidate"])
    def test_conflicting_bands(self):
        a=np.full((709,1536,3),100,dtype=np.uint8)
        for seat in ("hero","left"):
            x,y,_,_=SEATS[seat]["bar"]
            a[y+10:y+14,x+10:x+40]=[40,240,50]
            a[y+10:y+14,x+45:x+75]=[240,45,40]
        e=seat_evidence(Image.fromarray(a))
        self.assertTrue(e["active_band_conflict"])
        self.assertIsNone(e["active_band_candidate"])

if __name__=="__main__":
    unittest.main()
