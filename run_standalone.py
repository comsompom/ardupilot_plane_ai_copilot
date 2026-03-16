#!/usr/bin/env python3
"""Run the standalone desktop application (native PC app with Tkinter)."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from standalone.app_tk import main

if __name__ == "__main__":
    main()
