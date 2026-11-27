import unittest
from unittest.mock import patch
from PIL import Image
from upright_board import nearest,RANK_DATA,SUIT_DATA
from review import read_cards

# Extracted from the third board position in the supplied Nov 27 screenshot.
# Viewport (30,60,984,502), bilinear resizing at 1536/960/720/480 pixels.
# None of these samples was added to the template bank.
PAIRS=[[[0.4375,"3fc79e7076076077073fe3fe7ff707e07e07e077077ff1fe"],[1.1111,"38c7fe7ffffffffffffff7ff7fe7fe3fe1fc1f80f8070060"]],[[0.4375,"1fc78e7076076077073fe3fe7ff707e07e07e077077ff1fe"],[1.1111,"18c3fe7ffffffffffffff7ff7fe7fe3fe1fc1f80f8070060"]],[[0.4062,"3fcf8ee06e06e06e067fe7feffee07e07e07e07f07ffe3fe"],[1.1111,"18c3fe7ff7ffffffff7ff7ff7ff7fe3fe1fc1f80f8070020"]],[[0.4,"7f8c02c02c02c06c06ffeffeffee0ec07c07c07c07e0e7fc"],[1.1875,"3fc7feffffffffffffffffff7fe7fe7fc3fc1f81f00f00f0"]]]
class UprightFallbackTests(unittest.TestCase):
    def test_saved_unhighlighted_eight_heart(self):
        for (ra,rm),(sa,sm) in PAIRS:
            self.assertEqual(nearest((int(rm,16),ra),RANK_DATA)[0],"8")
            self.assertEqual(nearest((int(sm,16),sa),SUIT_DATA,"dh")[0],"h")
    def test_fallback_used_only_on_missing_board_candidate(self):
        im=Image.new("RGB",(1536,709),(90,130,160))
        unknown={"candidate":None}
        fixed={"candidate":"8h"}
        with patch("review.card",side_effect=[None,None,unknown,None,None,None,None]),patch("review.highlighted_board_corner",return_value=None),patch("upright_board.upright_board_card",side_effect=lambda image,i:fixed if i==2 else None),patch("offline_card_audit.hero_features",return_value=None):
            self.assertEqual(read_cards(im)["board_slots"][2],fixed)
        with patch("review.card",return_value={"candidate":"Ks"}),patch("upright_board.upright_board_card") as fallback:
            read_cards(im)
            fallback.assert_not_called()
