"""Allow: python -m app [--port 8083]"""

import app._bootstrap  # noqa: F401 — Windows console fix (must be first)

from app.cli import main

if __name__ == "__main__":
    main()