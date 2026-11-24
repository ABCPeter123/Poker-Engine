import unittest
from unittest.mock import patch
from pathlib import Path
import subprocess
import sys
from bootstrap import ensure_requirements


class BootstrapTests(unittest.TestCase):
    @patch("bootstrap.subprocess.run")
    def test_install_uses_current_python_and_absolute_requirements(self, run):
        ensure_requirements()
        command = run.call_args.args[0]
        self.assertEqual(command[:4], [sys.executable, "-m", "pip", "install"])
        self.assertEqual(Path(command[-1]), Path(__file__).resolve().with_name("requirements.txt"))
        self.assertTrue(run.call_args.kwargs["check"])

    @patch("bootstrap.subprocess.run")
    def test_runs_every_launch(self, run):
        ensure_requirements()
        ensure_requirements()
        self.assertEqual(run.call_count, 2)

    @patch("bootstrap.subprocess.run", side_effect=subprocess.CalledProcessError(1, "pip"))
    def test_failure_stops_launch(self, run):
        with self.assertRaises(SystemExit):
            ensure_requirements()


if __name__ == "__main__":
    unittest.main()
