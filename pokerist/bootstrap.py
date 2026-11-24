"""Install declared dependencies with the interpreter used to launch the review."""
import importlib
from pathlib import Path
import site
import subprocess
import sys


def ensure_requirements():
    requirements = Path(__file__).resolve().with_name("requirements.txt")
    print("Checking Pokerist dependencies...", flush=True)
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install",
             "--disable-pip-version-check", "--no-input",
             "-r", str(requirements)],
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(
            "Could not install Pokerist requirements. Check the pip output above. "
            "If pip is missing, run: py -m ensurepip --upgrade"
        ) from exc
    # A new user-site directory can be created during the first pip install.
    if site.ENABLE_USER_SITE:
        user_site = site.getusersitepackages()
        if Path(user_site).is_dir() and user_site not in sys.path:
            site.addsitedir(user_site)
    importlib.invalidate_caches()
