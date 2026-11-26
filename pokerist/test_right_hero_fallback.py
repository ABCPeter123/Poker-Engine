import unittest
from unittest.mock import patch
from PIL import Image
from review import read_cards
from adaptive_labels import RegionOCRCache

class RightHeroFallbackTests(unittest.TestCase):
    def test_deskewed_corner_recovers_missing_candidate_and_caches(self):
        im=Image.new("RGB",(1536,709))
        cache=RegionOCRCache()
        with patch("review.card",return_value=None),patch("offline_card_audit.hero_features",return_value=("rank","suit")) as geometry,patch("offline_card_audit.legacy_candidate",side_effect=["2","c"]):
            result=read_cards(im,cache)
            self.assertEqual(result["hole_slots"][1]["candidate"],"2c")
            self.assertEqual(result["hole_slots"][1]["source"],"deskewed corner fallback")
            self.assertEqual(read_cards(im,cache),result)
            self.assertEqual(geometry.call_count,1)
    def test_missing_suit_is_not_invented(self):
        im=Image.new("RGB",(1536,709))
        with patch("review.card",return_value=None),patch("offline_card_audit.hero_features",return_value=("rank","suit")),patch("offline_card_audit.legacy_candidate",side_effect=["2",None]):
            result=read_cards(im)
            self.assertIsNone(result["hole_slots"][1]["candidate"])
            self.assertEqual(result["hole_slots"][1]["rank_candidate"],"2")
    def test_complete_candidate_not_overwritten(self):
        im=Image.new("RGB",(1536,709))
        known={"candidate":"2c"}
        with patch("review.card",return_value=known),patch("offline_card_audit.hero_features",side_effect=AssertionError("unneeded fallback")):
            self.assertEqual(read_cards(im)["hole_slots"][1],known)
