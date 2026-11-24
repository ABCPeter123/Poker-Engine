"""Find and diagnose the optional native Tesseract dependency."""
import os
from pathlib import Path
import shutil
import subprocess

def resolve_tesseract():
    override = os.environ.get("TESSERACT_CMD")
    if override:
        value = shutil.which(override) or (override if Path(override).is_file() else None)
        if not value:
            return None, "TESSERACT_CMD does not point to an executable."
        return verify_tesseract(value)
    candidates = [shutil.which("tesseract")]
    if os.name == "nt":
        for key in ("ProgramFiles", "ProgramFiles(x86)", "LOCALAPPDATA"):
            root = os.environ.get(key)
            if root:
                candidates.extend(str(Path(root) / p / "tesseract.exe") for p in
                                  ("Tesseract-OCR", "Programs/Tesseract-OCR"))
        candidates.append(r"C:\msys64\ucrt64\bin\tesseract.exe")
    errors = []
    for path in dict.fromkeys(p for p in candidates if p):
        if Path(path).is_file():
            exe, error = verify_tesseract(path)
            if exe:
                return exe, None
            errors.append(error)
    return None, "; ".join(errors) if errors else "Tesseract executable not found. Install it or set TESSERACT_CMD to its full path."

def verify_tesseract(path):
    try:
        result = subprocess.run([path, "--version"], capture_output=True, text=True,
                                timeout=5, check=True)
        if "tesseract" not in (result.stdout + result.stderr).lower():
            return None, "Executable did not identify itself as Tesseract."
        return path, None
    except (OSError, subprocess.SubprocessError) as exc:
        return None, f"Tesseract could not start: {exc}"

if __name__ == "__main__":
    exe, error = resolve_tesseract()
    print(f"OCR ready: {exe}" if exe else f"OCR unavailable: {error}")
    raise SystemExit(0 if exe else 1)
