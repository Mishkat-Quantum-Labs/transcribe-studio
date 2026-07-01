"""Package and user-data paths (works in dev and after pip/uv install)."""

from __future__ import annotations

import os
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = PACKAGE_DIR / "config"
TEMPLATES_DIR = PACKAGE_DIR / "templates"
STATIC_DIR = PACKAGE_DIR / "static"


def data_dir() -> Path:
    """Writable directory for DB, audio, and LLM uploads."""
    override = os.environ.get("TRANSCRIBE_STUDIO_DATA", "").strip()
    if override:
        return Path(override).expanduser()
    legacy = PACKAGE_DIR.parent / "data"
    if (legacy / "transcribe.db").exists():
        return legacy
    return Path.home() / ".transcribe-studio"