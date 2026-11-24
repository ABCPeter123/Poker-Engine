import unittest
from unittest.mock import Mock
from PIL import Image
from saved_card_review import reconcile, read_enhanced

def c(label):
    return {"candidate":label,"verified":False}

def result(first=None, second=None, board=None):
    return {"hole_slots":[first,second],"board_slots":board if board is not None else [None]*5,
            "quality":{"unrecognized_visible_cards":0}}

class EnhancementTests(unittest.TestCase):
    def test_three_agree_and_provenance(self):
        raw=result(c(None),c("Kd"))
        votes=[result(c("As"),c("Kd")) for _ in range(3)]+[result(c(None),c("Kd"))]
        out=reconcile(raw,votes)
        self.assertEqual(out["hole_slots"][0]["candidate"],"As")
        self.assertEqual(out["hole_slots"][0]["enhancement_votes"],3)
        self.assertFalse(out["hole_slots"][0]["verified"])
        self.assertIsNone(raw["hole_slots"][0]["candidate"])
        self.assertEqual(out["quality"]["unrecognized_visible_cards"],0)
    def test_two_votes_not_enough(self):
        raw=result(c(None))
        self.assertIsNone(reconcile(raw,[result(c("As"))]*2)["hole_slots"][0]["candidate"])
    def test_any_disagreement_prevents_recovery(self):
        raw=result(c(None))
        votes=[result(c("As"))]*3+[result(c("Ad"))]
        self.assertIsNone(reconcile(raw,votes)["hole_slots"][0]["candidate"])
    def test_empty_and_already_read_slots_unchanged(self):
        raw=result(None,c("Kd"))
        self.assertEqual(reconcile(raw,[result(c("As"),c("Qd"))]*4),raw)
    def test_duplicate_existing_card_not_added(self):
        raw=result(c(None),c("As"))
        self.assertIsNone(reconcile(raw,[result(c("As"),c("As"))]*4)["hole_slots"][0]["candidate"])
    def test_duplicate_proposals_not_added(self):
        raw=result(c(None),c(None))
        self.assertEqual(reconcile(raw,[result(c("As"),c("As"))]*4),raw)
    def test_no_extra_pass_for_complete_reading(self):
        reader=Mock(return_value=result(c("As"),c("Kd")))
        read_enhanced(Image.new("RGB",(1536,709)),reader)
        self.assertEqual(reader.call_count,1)
    def test_extra_pass_only_when_visible_unknown(self):
        reader=Mock(side_effect=[result(c(None)),result(c("As")),result(c("As")),result(c("As")),result(c(None))])
        self.assertEqual(read_enhanced(Image.new("RGB",(20,20)),reader)["hole_slots"][0]["candidate"],"As")
        self.assertEqual(reader.call_count,5)

if __name__=="__main__":
    unittest.main()
