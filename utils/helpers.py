"""Small helpers used by every module. No Streamlit code lives here."""
from __future__ import annotations

import sys
from html import escape as esc  # noqa: F401  (re-exported for the other modules)
from pathlib import Path

# project root = the folder that contains app/, utils/, models/ and data/
BASE_DIR = Path(__file__).resolve().parent.parent
SEARCH_DIRS = ("models", "data", "dataset", "")
NOT_DETECTED = "Not detected — please verify."


def find_file(*names: str) -> Path | None:
    """Return the first existing file among the given names, looking in models/, data/, dataset/ and the project root."""
    for name in names:
        for sub in SEARCH_DIRS:
            candidate = BASE_DIR / sub / name
            if candidate.is_file():
                return candidate
    return None


def install_hint(package: str) -> str:
    """Exact pip command for the Python that is running the app (works on Windows, macOS and Linux)."""
    return f"{sys.executable} -m pip install {package}"