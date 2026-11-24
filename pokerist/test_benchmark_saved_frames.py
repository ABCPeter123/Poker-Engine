import unittest
from pathlib import Path
from benchmark_saved_frames import validate_manifest, transform, score, summarize, gate
from check_saved_frame import field_results
from PIL import Image
from review import decode, RANKS

class CorpusTests(unittest.TestCase):
    def test_empty_and_missing_are_distinct(self):
        rows=field_results({"board_slots":[{"candidate":"As"}, {"candidate":None}, None]},
                           {"board_slots":["As","Kd",None]})
        self.assertEqual(score(rows)["visible_cards"]["accuracy"],.5)
        self.assertEqual(score(rows)["empty_slots"]["accuracy"],1)
    def test_false_positive_fails_gate(self):
        rows=field_results({"board_slots":[{"candidate":"As"},{"candidate":None}]},{"board_slots":["As",None]})
        report=summarize([{"variant":"original","elapsed_ms":50,"fields":rows}],[])
        self.assertFalse(gate(report,1,0))
    def test_missing_file_not_success(self):
        self.assertFalse(gate(summarize([], [{"file":"missing.png"}]),1,0))
    def test_p95_and_strict_gate(self):
        rows=field_results({"board_slots":[{"candidate":"As"}]},{"board_slots":["As"]})
        report=summarize([{"variant":"original","elapsed_ms":v,"fields":rows} for v in range(1,21)],[])
        self.assertEqual(report["variants"]["original"]["p95_ms"],19)
        self.assertTrue(gate(report,1,0))
    def test_manifest_rejects_duplicates_and_missing_slots(self):
        good={"file":"a.png","expected":{"hole_slots":["As","Kd"],"board_slots":[None]*5}}
        self.assertEqual(len(validate_manifest({"cases":[good]})),1)
        with self.assertRaises(ValueError):validate_manifest({"cases":[good,good]})
        with self.assertRaises(ValueError):validate_manifest({"cases":[{"file":"a.png","expected":{}}]})
    def test_image_variants_preserve_geometry(self):
        image=Image.new("RGB",(716,331),(70,120,150))
        for mode in ("original","downscale","jpeg"):
            self.assertEqual(transform(image,mode).size,image.size)
    def test_template_cache_is_read_only(self):
        mask=decode(RANKS["J"])
        self.assertIs(mask,decode(RANKS["J"]))
        with self.assertRaises(ValueError):mask[0,0]=True
    def test_fixture_manifest_valid(self):
        import json
        data=json.loads((Path(__file__).with_name("fixtures")/"saved_corpus.json").read_text(encoding="utf-8"))
        self.assertEqual(len(validate_manifest(data)),18)

if __name__=="__main__":
    unittest.main()
