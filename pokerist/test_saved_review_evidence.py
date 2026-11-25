import unittest
from unittest.mock import patch
from contextlib import redirect_stdout
from io import StringIO
from tempfile import TemporaryDirectory
from pathlib import Path
import json
from base64 import b64decode
from io import BytesIO
from PIL import Image
from saved_review_evidence import union_box,crop_evidence,component_choices,saved_evidence

class SavedEvidenceTests(unittest.TestCase):
    def test_union_clips_to_image(self):
        im=Image.new("RGB",(30,20))
        self.assertEqual(union_box([(1,2,10,12),(8,8,28,18)],im,4),(0,0,30,20))
    def test_png_preserves_pixels_and_bounds(self):
        im=Image.new("RGB",(20,15),(23,45,67))
        data=crop_evidence(im,(3,2,15,12))
        with Image.open(BytesIO(b64decode(data["png_base64"]))) as crop:
            self.assertEqual(crop.size,(12,10))
            self.assertEqual(crop.getpixel((0,0)),(23,45,67))
        self.assertEqual(data["bounds"],[3,2,15,12])
    def test_component_evidence_does_not_invent_card(self):
        def recognize(image,box,color,templates,threshold):
            if box==(0,0,10,10) and color=="red":
                return "A",.1
            return None,None
        r=component_choices(Image.new("RGB",(30,30)),[((0,0,10,10),(0,10,10,20),False)],
                            recognize,{"A":"x"},{"h":"x","s":"x"})
        self.assertEqual(r["rank"][0]["label"],"A")
        self.assertEqual(r["suit"],[])
        self.assertNotIn("candidate",r)
    def test_wide_rank_cannot_suggest_non_ten(self):
        def recognize(image,box,color,templates,threshold):
            return ("A",.01) if box==(0,0,10,10) else (None,None)
        r=component_choices(Image.new("RGB",(30,30)),[((0,0,10,10),(0,10,10,20),True)],
                            recognize,{"A":"x","T":"x"},{"h":"x","s":"x"})
        self.assertEqual(r["rank"],[])
    def test_quiet_cli_writes_full_report_without_echoing_image_data(self):
        from review import main
        sample={"saved_field_evidence":{"pot":{"png_base64":"AA"*300000}}}
        with TemporaryDirectory() as d:
            output=Path(d)/"review.json"
            stream=StringIO()
            with patch("sys.argv",["review.py","sample.png","--output",str(output),"--no-ocr","--quiet"]),patch("review.review",return_value=sample),redirect_stdout(stream):
                main()
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")),sample)
            self.assertLess(len(stream.getvalue()),1000)
    def test_complete_review_has_all_expected_crop_keys(self):
        im=Image.new("RGB",(1536,709),(30,60,80))
        evidence=saved_evidence(im,{"hole_slots":[None]*2,"board_slots":[None]*5})
        self.assertEqual(len(evidence),18)
        self.assertIn("pot",evidence)
        self.assertIn("bet.hero",evidence)
        self.assertIn("board.4",evidence)
        self.assertNotIn("components",evidence["board.0"])

if __name__=="__main__":
    unittest.main()
