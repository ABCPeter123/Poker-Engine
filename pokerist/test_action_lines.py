import unittest
from PIL import Image
from table_observation import select_status
from adaptive_labels import prepared_region_mask
def word(text,y=0,x=0,confidence=90):
    return dict(text=text,x=x,y=y,w=20,h=10,confidence=confidence)
class ActionLineTests(unittest.TestCase):
    def test_actions_with_unrelated_low_confidence_line(self):
        for action in ("Raise","Check","Call","Fold"):
            self.assertEqual(select_status([word(action),word("Guest",y=20,confidence=10)])["candidate"],action)
    def test_conflicting_lines_and_non_actions(self):
        self.assertTrue(select_status([word("Call"),word("Raise",y=20)])["conflict"])
        self.assertIsNone(select_status([word("Call"),word("Raise",y=20,confidence=20)])["candidate"])
        self.assertIsNone(select_status([word("Check"),word("or",x=25),word("Raise",x=50)])["candidate"])
        self.assertIsNone(select_status([word("Call",confidence=30)])["candidate"])
    def test_pale_label_mask(self):
        im=Image.new("RGB",(10,10),(215,215,215))
        self.assertFalse(prepared_region_mask(im,(0,0,10,10),"status").any())
        self.assertTrue(prepared_region_mask(im,(0,0,10,10),"status_alt").all())
