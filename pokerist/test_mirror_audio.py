import unittest
from unittest.mock import patch
from pathlib import Path
from start_mirror import audio_options, audio_warning, inspect_audio_sink

class MirrorAudioTests(unittest.TestCase):
    def test_prefers_installed_modern_sink(self):
        seen=[]
        def probe(exe,name,env):
            seen.append((exe.name,name))
            return True
        self.assertEqual(audio_options(Path("bin/uxplay.exe"),{},probe=probe),["-as","wasapi2sink","-vsync","no"])
        self.assertEqual(seen,[("gst-inspect-1.0.exe","wasapi2sink")])
    def test_fallbacks(self):
        for sink in ("wasapisink","directsoundsink"):
            self.assertEqual(audio_options("uxplay.exe",{},probe=lambda *a:a[1]==sink),["-as",sink,"-vsync","no"])
        self.assertEqual(audio_options("uxplay.exe",{},probe=lambda *a:None),["-as","autoaudiosink","-vsync","no"])
    def test_manual_sink_and_sync(self):
        self.assertEqual(audio_options("uxplay.exe",{},"directsoundsink","timestamp",probe=lambda *a:True),["-as","directsoundsink","-vsync"])
        with self.assertRaises(ValueError):
            audio_options("uxplay.exe",{},"directsoundsink",probe=lambda *a:False)
        self.assertEqual(audio_options("uxplay.exe",{},"default","timestamp"),["-as","autoaudiosink","-vsync"])
    def test_missing_inspector(self):
        with patch("start_mirror.subprocess.run",side_effect=FileNotFoundError):
            self.assertIsNone(inspect_audio_sink("gst-inspect","wasapi2sink",{}))
    def test_audio_warning_not_silence(self):
        self.assertTrue(audio_warning("WARN audiobasesink correct clock skew"))
        self.assertTrue(audio_warning("ERROR wasapi device removed"))
        self.assertFalse(audio_warning("Audio format AAC"))
        self.assertFalse(audio_warning("WARN d3d11videosink caps changed"))
