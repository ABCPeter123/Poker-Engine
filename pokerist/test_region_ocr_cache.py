import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw
from adaptive_labels import RegionOCRCache
class RegionCacheTests(unittest.TestCase):
    def test_same_mask_reused_changed_mask_rescanned(self):
        cache=RegionOCRCache()
        image=Image.new("RGB",(200,100))
        ImageDraw.Draw(image).rectangle((20,5,25,14),fill="white")
        ImageDraw.Draw(image).rectangle((120,5,125,14),fill="white")
        entries=[("hero",(0,0,50,30),"bet"),("left",(100,0,150,30),"bet")]
        with patch("adaptive_labels.scan_regions",side_effect=lambda im,exe,regions,**kw:({key:[key] for key,_,_ in regions},None)) as scan:
            self.assertEqual(cache.scan(image,"test",entries)[0],{"hero":["hero"],"left":["left"]})
            cache.scan(image,"test",entries)
            self.assertEqual(scan.call_count,1)
            ImageDraw.Draw(image).rectangle((5,5,12,14),fill="white")
            cache.scan(image,"test",entries)
            self.assertEqual(scan.call_count,2)
            self.assertEqual(scan.call_args.args[2],[entries[0]])
    def test_changed_region_failure_invalidates_old_evidence(self):
        cache=RegionOCRCache()
        image=Image.new("RGB",(50,30))
        ImageDraw.Draw(image).rectangle((20,5,25,14),fill="white")
        entries=[("hero",(0,0,50,30),"bet")]
        with patch("adaptive_labels.scan_regions",side_effect=[({"hero":[1]},None),({},"error"),({"hero":[2]},None)]):
            cache.scan(image,"test",entries)
            ImageDraw.Draw(image).rectangle((5,5,12,14),fill="white")
            self.assertEqual(cache.scan(image,"test",entries),({},"error"))
            self.assertEqual(cache.scan(image,"test",entries),({"hero":[2]},None))
if __name__=="__main__":
    unittest.main()
