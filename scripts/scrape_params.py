"""
Scrape ArduPilot Plane parameters from the official docs and save to JSON.
Run from project root: python scripts/scrape_params.py
"""
import json
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import ARDUPILOT_PARAMS_URL, PARAM_DB_PATH, DATA_DIR


# Match parameter heading: "PARAM_NAME: Short description" (optional trailing ¶)
_PARAM_HEADING_RE = re.compile(r"^([A-Z][A-Z0-9_]*):\s*(.*)$")


def _parse_param_block_text(text: str) -> dict:
    """Extract range and units from parameter block text (content after an h3)."""
    out = {"range": "", "units": ""}
    if not text:
        return out
    # Patterns: "Range" then value (e.g. "1 to 255"), "Units" then value (e.g. "seconds")
    for label, key in (("Range", "range"), ("Units", "units")):
        idx = text.find(label)
        if idx == -1:
            continue
        rest = text[idx + len(label) :].strip()
        # Take first line or up to next known label
        for stop in ("Range", "Units", "Increment", "Values", "Bitmask", "Note:"):
            if stop != label and stop in rest:
                end = rest.find(stop)
                if end != -1:
                    rest = rest[:end].strip()
        # First line or first segment
        first_line = rest.split("\n")[0].strip() if "\n" in rest else rest
        first_line = first_line.split("  ")[0].strip()
        if first_line and not first_line.startswith("Bit ") and len(first_line) < 80:
            out[key] = first_line
    return out


def scrape_params(url: str = None) -> list:
    url = url or ARDUPILOT_PARAMS_URL
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    params = []
    # ArduPilot params page uses one <h3> per parameter (not a single big table).
    # The first <table> on the page is a small "Range" table inside a param block.
    for h3 in soup.find_all("h3"):
        raw = h3.get_text(strip=True).strip("\u00b6")  # strip ¶
        m = _PARAM_HEADING_RE.match(raw)
        if not m:
            continue
        name, desc = m.group(1), m.group(2).strip()
        if not name:
            continue
        d = {"name": name, "description": desc or "", "default": "", "range": "", "units": ""}
        # Optional: parse following siblings for range/units
        nxt = h3.find_next_sibling()
        if nxt and nxt.name != "h3":
            block = []
            s = nxt
            for _ in range(25):
                if s is None or s.name == "h3":
                    break
                block.append(s.get_text(separator=" ", strip=True))
                s = s.find_next_sibling()
            combined = " ".join(block)
            extra = _parse_param_block_text(combined)
            d["range"] = extra["range"] or d["range"]
            d["units"] = extra["units"] or d["units"]
        params.append(d)
    return params


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Fetching {ARDUPILOT_PARAMS_URL} ...")
    params = scrape_params()
    print(f"Found {len(params)} parameters.")
    out = {"parameters": params, "version": "4.6.2", "source": ARDUPILOT_PARAMS_URL}
    PARAM_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PARAM_DB_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"Saved to {PARAM_DB_PATH}")


if __name__ == "__main__":
    main()
