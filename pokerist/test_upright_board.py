import unittest
from PIL import Image
from upright_board import compiled,nearest,RANK_DATA,SUIT_DATA,upright_board_card
class UprightBoardTests(unittest.TestCase):
    def test_complete_label_coverage(self):
        self.assertEqual({r[0] for r in compiled(RANK_DATA)},set("23456789TJQKA"))
        self.assertEqual({r[0] for r in compiled(SUIT_DATA)},set("cdhs"))
    def test_no_blank_board(self):
        im=Image.new("RGB",(1536,709),(75,120,150))
        for i in range(5):self.assertIsNone(upright_board_card(im,i))
    def test_calibrated_gold_masks(self):
        for label,aspect,mask in compiled(RANK_DATA)[-2:]:
            self.assertEqual(nearest((mask,aspect),RANK_DATA)[0],label)
        for label,aspect,mask in compiled(SUIT_DATA)[-2:]:
            self.assertEqual(nearest((mask,aspect),SUIT_DATA,"cs")[0],label)
    def test_ambiguous_masks_abstain(self):
        self.assertIsNone(nearest(None,RANK_DATA)[0])
