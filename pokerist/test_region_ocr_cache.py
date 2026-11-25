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
    def test_reappearing_exact_mask_reuses_previous_ocr(self):
        cache=RegionOCRCache()
        first=Image.new("RGB",(50,30))
        ImageDraw.Draw(first).rectangle((20,5,25,14),fill="white")
        second=first.copy()
        ImageDraw.Draw(second).rectangle((5,5,12,14),fill="white")
        entries=[("hero",(0,0,50,30),"bet")]
        with patch("adaptive_labels.scan_regions",side_effect=[({"hero":[1]},None),({"hero":[2]},None)]) as scan:
            self.assertEqual(cache.scan(first,"test",entries)[0],{"hero":[1]})
            self.assertEqual(cache.scan(second,"test",entries)[0],{"hero":[2]})
            self.assertEqual(cache.scan(first,"test",entries)[0],{"hero":[1]})
            self.assertEqual(scan.call_count,2)
    def test_identical_crop_skips_mask_preprocessing(self):
        image=Image.new("RGB",(50,30))
        ImageDraw.Draw(image).rectangle((20,5,25,14),fill="white")
        cache=RegionOCRCache()
        entries=[("hero",(0,0,50,30),"bet")]
        with patch("adaptive_labels.scan_regions",return_value=({"hero":[1]},None)):
            cache.scan(image,"test",entries)
        with patch("adaptive_labels.prepared_region_mask",side_effect=AssertionError("unchanged crop preprocessed")):
            self.assertEqual(cache.scan(image.copy(),"test",entries),({"hero":[1]},None))
        self.assertEqual(cache.raw_hits,1)
    def test_raw_cache_does_not_reuse_results_across_ocr_engines(self):
        image=Image.new("RGB",(50,30))
        ImageDraw.Draw(image).rectangle((20,5,25,14),fill="white")
        cache=RegionOCRCache()
        entries=[("hero",(0,0,50,30),"bet")]
        with patch("adaptive_labels.scan_regions",side_effect=[({"hero":[1]},None),({"hero":[2]},None)]):
            self.assertEqual(cache.scan(image,"first",entries)[0],{"hero":[1]})
            self.assertEqual(cache.scan(image,"second",entries)[0],{"hero":[2]})
if __name__=="__main__":
    unittest.main()
