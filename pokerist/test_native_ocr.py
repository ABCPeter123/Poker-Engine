import unittest
from unittest.mock import patch
from PIL import Image,ImageDraw,ImageFont
from native_ocr import recognize_tsv,prepare_native
from ocr_runtime import resolve_tesseract

class NativeOCRTests(unittest.TestCase):
    def test_cli_fallback_uses_stdin(self):
        from subprocess import CompletedProcess
        im=Image.new("L",(50,20),255)
        with patch("native_ocr.subprocess.run",return_value=CompletedProcess([],0,b"header\n",b"")) as run:
            self.assertEqual(recognize_tsv(im,"fake",11,"0123"),"header\n")
            self.assertEqual(run.call_args.args[0][:3],["fake","stdin","stdout"])
            self.assertTrue(run.call_args.kwargs["input"].startswith(b"\x89PNG"))

    def test_native_digits_and_whitelist_reset_if_available(self):
        exe,_=resolve_tesseract()
        if not exe or not prepare_native(exe):
            self.skipTest("Native Tesseract installation not available")
        im=Image.new("L",(500,130),255)
        font=ImageFont.load_default(size=65)
        ImageDraw.Draw(im).text((30,20),"12345",fill=0,font=font)
        numeric=recognize_tsv(im,exe,7,"0123456789",persistent=True)
        self.assertIn("12345",numeric)
        im=Image.new("L",(500,130),255)
        ImageDraw.Draw(im).text((30,20),"CHECK",fill=0,font=font)
        text=recognize_tsv(im,exe,7,"",persistent=True)
        self.assertIn("CHECK",text)
