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


def scrape_params(url: str = None) -> list:
    url = url or ARDUPILOT_PARAMS_URL
    r = requests.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    table = soup.find("table")
    if not table:
        # Try alternative: look for parameter list in divs
        params = []
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) >= 3:
                name_cell = cells[0].get_text(strip=True)
                if name_cell and re.match(r"^[A-Z_0-9]+$", name_cell):
                    desc = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    default = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    params.append({
                        "name": name_cell,
                        "description": desc,
                        "default": default,
                        "range": cells[3].get_text(strip=True) if len(cells) > 3 else "",
                        "units": cells[4].get_text(strip=True) if len(cells) > 4 else "",
                    })
        return params
    params = []
    rows = table.find_all("tr")
    headers = [th.get_text(strip=True).lower() for th in rows[0].find_all("th")] if rows else []
    for row in rows[1:]:
        cells = row.find_all(["td", "th"])
        if len(cells) < 2:
            continue
        name = cells[0].get_text(strip=True)
        if not name or not re.match(r"^[A-Z_0-9]+$", name):
            continue
        d = {"name": name}
        for i, h in enumerate(headers[1:], 1):
            if i < len(cells):
                d[h] = cells[i].get_text(strip=True)
        if "description" not in d and len(cells) > 1:
            d["description"] = cells[1].get_text(strip=True)
        if "default" not in d and len(cells) > 2:
            d["default"] = cells[2].get_text(strip=True)
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
