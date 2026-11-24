import unittest
from unittest.mock import patch
import subprocess
from ocr_runtime import resolve_tesseract, verify_tesseract

class OCRRuntimeTests(unittest.TestCase):
    @patch("ocr_runtime.subprocess.run")
    def test_version_check(self, run):
        run.return_value=subprocess.CompletedProcess([],0,"tesseract 5.0","")
        self.assertEqual(verify_tesseract("test.exe"),("test.exe",None))
    @patch("ocr_runtime.subprocess.run",side_effect=OSError("missing DLL"))
    def test_executable_failure(self, run):
        exe,error=verify_tesseract("test.exe")
        self.assertIsNone(exe)
        self.assertIn("missing DLL",error)
    @patch.dict("os.environ",{"TESSERACT_CMD":"nonexistent-ocr-test.exe"})
    @patch("ocr_runtime.shutil.which",return_value=None)
    @patch("ocr_runtime.Path.is_file",return_value=False)
    def test_bad_override(self,*args):
        exe,error=resolve_tesseract()
        self.assertIsNone(exe)
        self.assertIn("TESSERACT_CMD",error)
    @patch.dict("os.environ",{},clear=True)
    @patch("ocr_runtime.shutil.which",return_value=None)
    @patch("ocr_runtime.Path.is_file",return_value=False)
    def test_no_install(self,*args):
        exe,error=resolve_tesseract()
        self.assertIsNone(exe)
        self.assertIn("not found",error)

if __name__=="__main__":unittest.main()
