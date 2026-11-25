"""Exercise the actual saved-image pipeline, with synthetic (non-private) frames."""
import unittest
from unittest.mock import patch
import tempfile
import json
from pathlib import Path
from PIL import Image, ImageDraw
from review import review, normalize, read_cards, BOARD
from check_saved_frame import field_results

class SavedPipelineTests(unittest.TestCase):
    def image(self):
        return Image.new("RGB",(1536,709),(75,120,150))
    def test_empty_frame_review_contract(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"blank.png"
            self.image().save(path)
            result=review(path,None)
        self.assertEqual(result["hole_slots"],[None]*2)
        self.assertEqual(result["board_slots"],[None]*5)
        self.assertEqual(result["street_candidate"],"Preflop")
        self.assertFalse(result["verified"])
        self.assertEqual(set(result["table_observation"]["seats"]),
                         {"hero","left","upper_left","upper_right","right"})
        self.assertEqual(json.loads(json.dumps(result,allow_nan=False))["board_slots"],[None]*5)
    def test_all_review_modes_and_timings(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"blank.png"
            self.image().save(path)
            for flags in ({},{"enhanced":True},{"deep":True}):
                with self.subTest(flags=flags):
                    result=review(path,None,**flags)
                    self.assertEqual(result["board_slots"],[None]*5)
                    if flags:
                        self.assertEqual(len(result["saved_field_evidence"]),18)
                    else:
                        self.assertNotIn("saved_field_evidence",result)
                    timings=result["timings_ms"]
                    self.assertEqual(set(timings),{"seat_cues","cards","amounts","table_observation","total"})
                    self.assertTrue(all(v>=0 for v in timings.values()))
                    self.assertAlmostEqual(timings["total"],sum(v for k,v in timings.items() if k!="total"),delta=.003)
    def test_visible_unknown_is_not_empty_after_normalization(self):
        im=self.image()
        d=ImageDraw.Draw(im)
        for _,_,box in BOARD[:3]:
            x0,y0,x1,y1=box
            d.rectangle((x0,y0,x1-1,y1-1),fill=(245,190,15))
            d.rectangle((x0+4,y0+4,x1-5,y1-5),fill=(235,235,235))
        framed=Image.new("RGB",(1536,749),(240,240,240))
        framed.paste(im,(0,40))
        result=read_cards(normalize(framed))
        self.assertEqual(result["street_candidate"],"Flop")
        self.assertEqual(result["quality"]["unrecognized_visible_cards"],3)
        self.assertTrue(all(c is not None and c["candidate"] is None for c in result["board_slots"][:3]))
        self.assertEqual(result["board_slots"][3:],[None,None])
        rows=field_results(result,{"board_slots":[None]*5})
        self.assertEqual(sum(r["status"]=="incorrect" for r in rows),3)
    def test_saved_conflict_is_not_used_as_stack_candidate(self):
        from saved_amount_review import add_evidence
        from review import review_image, number_text
        raw={"raw":"186550","candidate":number_text("186550")}
        disputed=add_evidence(raw,[{"method":"stretch","raw":"106550","confidence":80}],number_text)
        with patch("review.read_numbers",return_value=({"right":raw},None)),patch(
                "saved_amount_review.add_saved_amount_evidence",return_value={"right":disputed}),patch(
                "review.seat_evidence",return_value={"seats":{},"active_band_candidate":None}),patch(
                "table_observation.scan_labels",return_value=({},None)):
            result=review_image(self.image(),"mock-tesseract",enhanced=True)
        self.assertIsNone(result["number_candidates"]["right"]["candidate"])
        self.assertIsNone(result["table_observation"]["seats"]["right"]["stack"])
        self.assertEqual(result["number_candidates"]["right"]["original_candidate"]["value"],186550)
    def test_noncontiguous_board_is_not_a_valid_street(self):
        im=self.image()
        d=ImageDraw.Draw(im)
        for i in (0,2,3):
            x0,y0,x1,y1=BOARD[i][2]
            d.rectangle((x0,y0,x1-1,y1-1),fill=(235,235,235))
        result=read_cards(normalize(im))
        self.assertIsNone(result["street_candidate"])
        self.assertTrue(result["quality"]["noncontiguous_board"])

if __name__=="__main__":
    unittest.main()
