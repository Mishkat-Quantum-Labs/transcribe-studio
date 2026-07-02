"""Platform fixes before any other app code runs."""

from __future__ import annotations

import os
import sys

# Python 3.13 on Windows: _pyrepl can raise WinError 123 in Cursor/WT/non-VT consoles.
if sys.platform == "win32":
    os.environ.setdefault("PYTHON_BASIC_REPL", "1")