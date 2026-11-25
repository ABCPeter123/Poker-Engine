import unittest
import numpy as np
from PIL import Image
from numpy.lib.stride_tricks import sliding_window_view
from review import ink_masks, face_present
from card_geometry import gold_mask
from seat_cues import colors
from table_observation import dealer_marker, D, ANCHORS

class ExactVisionMathTests(unittest.TestCase):
    def setUp(self):
        self.a=np.random.default_rng(27).integers(0,256,(91,113,3),dtype=np.int16)
    def test_ink(self):
        a=self.a
        r,g,b=np.moveaxis(a,-1,0)
        gold=gold_mask(a)
        expected_red=(r>95)&(r-g>40)&(r-b>35)&~gold&((g-b<35)|(g<r*.55))
        expected_black=(a.max(2)<125)&(np.ptp(a,axis=2)<55)&~gold
        red,black=ink_masks(a)
        np.testing.assert_array_equal(red,expected_red)
        np.testing.assert_array_equal(black,expected_black)
    def test_colors(self):
        a=self.a
        r,g,b=np.moveaxis(a,-1,0)
        bright=(a.max(-1)>165)&((a.max(-1)-a.min(-1))>75)
        expected={"red":bright&(r>g+35)&(r>b+35),
                  "green":bright&(g>r+25)&(g>b+20),
                  "amber":bright&(r>170)&(g>110)&(b<np.minimum(r,g)-50)}
        for key,value in colors(a).items():
            np.testing.assert_array_equal(value,expected[key])
    def test_face(self):
        for a in (self.a,np.full_like(self.a,235)):
            light=(a.min(2)>180)&(np.ptp(a,axis=2)<32)
            expected=float(light.mean())>=.20 and float((light.mean(axis=1)>=.15).mean())>=.60
            self.assertEqual(face_present(Image.fromarray(a.astype(np.uint8)),(0,0,a.shape[1],a.shape[0])),expected)
    def test_dealer(self):
        image=Image.fromarray(np.random.default_rng(47).integers(0,256,(709,1536,3),dtype=np.uint8))
        a=np.asarray(image.resize((768,355)).convert("L"),dtype=np.int16)
        matches=[]
        for seat,(x,y) in ANCHORS.items():
            windows=sliding_window_view(a[y-22:y+23,x-30:x+31],(13,13))
            distances=np.abs(windows-D).mean(axis=(-2,-1))
            dy,dx=np.unravel_index(distances.argmin(),distances.shape)
            matches.append((float(distances[dy,dx]),seat,[int((x-30+dx+6)*2),int((y-22+dy+6)*2)]))
        matches.sort()
        score,seat,center=matches[0]
        expected={"candidate":seat if score<=15 and matches[1][0]-score>=6 else None,
                  "distance":round(score,2),"center":center if score<=15 else None,"verified":False}
        self.assertEqual(dealer_marker(image),expected)

if __name__=="__main__":
    unittest.main()
