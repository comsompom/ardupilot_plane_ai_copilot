#!/usr/bin/env python3
"""Run the Flask web app for ArduPilot AI Assistant."""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(WEB))
os.chdir(WEB)

from app import main

if __name__ == "__main__":
    main()
