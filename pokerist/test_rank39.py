"""Regression masks from saved images, independent of live capture."""
import unittest
from review import RANKS,decode,match

# Unused crop variants: 960/480 of calibration cards, black 9 from
# another hand, dimmed 3 from the same hand at showdown.
SAMPLES=[
  [
    "9",
    960,
    "1f8,7fe,79e,a0f,a05,e05,e05,f0f,ffe,ffc,e00,a06,a8e,79e,7fe,078"
  ],
  [
    "9",
    480,
    "3fc,7fe,eff,b97,b17,a17,a97,bff,bfe,bf8,af0,a86,a8e,7fe,7fe,1f8"
  ],
  [
    "3",
    960,
    "3fc,7be,e0e,e06,e00,f00,780,3f0,780,f00,e00,e07,e07,f07,7fe,3fc"
  ],
  [
    "3",
    480,
    "1f8,7fe,e06,e06,e00,f00,7c0,3e0,7c0,f00,e00,e06,e07,f0f,7fe,1f8"
  ],
  [
    "9",
    1536,
    "3fc,79e,70e,e06,e06,e07,e07,f0e,ffe,efc,e00,e00,e06,70e,7fe,1f8"
  ],
  [
    "9",
    960,
    "1fc,7df,f07,e07,e07,e07,e07,f07,fff,ffc,e00,e00,e07,707,7fe,1fc"
  ],
  [
    "9",
    720,
    "1f8,79c,f0e,e06,e07,e07,e07,f0e,ffe,ffc,e00,e00,e06,70e,7fc,1f8"
  ],
  [
    "9",
    480,
    "1fc,7de,f07,e07,e07,e07,e07,f0f,ffe,ff8,e00,e00,e06,f0f,7fe,1fc"
  ],
  [
    "3",
    1536,
    "0f8,3fe,78f,707,707,700,780,3f0,7f0,700,f00,f07,f07,707,7ff,1fc"
  ],
  [
    "3",
    960,
    "1f8,3fc,79e,70e,70e,780,7e0,3f0,7e0,f00,f00,f0f,f0f,79e,7fc,1f8"
  ],
  [
    "3",
    720,
    "1f8,3fc,79e,71e,70e,780,7c0,7f0,7e0,f80,f00,f8f,f0f,79e,7fe,1f8"
  ],
  [
    "3",
    480,
    "1f8,7fe,7de,70e,f06,f80,7e0,7f0,7e0,f80,f00,f8f,f0f,ffe,7fe,1f8"
  ]
]

class Rank39Tests(unittest.TestCase):
    def test_saved_rank_crops(self):
        for rank,width,mask in SAMPLES:
            with self.subTest(rank=rank,width=width,mask=mask):
                self.assertEqual(match(decode(mask),RANKS)[0],rank)
    def test_prior_recognized_templates_still_match(self):
        prior={k:v for k,v in RANKS.items() if not k.startswith(("3_nov25_439_","9_nov25_427_"))}
        for key,value in prior.items():
            glyph=decode(value)
            if match(glyph,prior)[0]==key.split("_")[0]:
                with self.subTest(template=key):
                    self.assertEqual(match(glyph,RANKS)[0],key.split("_")[0])
