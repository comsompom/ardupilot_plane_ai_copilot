"""
Parameter loading: ArduPilot param DB and user params (file or MAVLink).
"""
import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Lazy MAVLink import for optional live connection
_pymavlink_available = None

def _check_pymavlink():
    global _pymavlink_available
    if _pymavlink_available is None:
        try:
            import pymavlink.mavutil
            _pymavlink_available = True
        except ImportError:
            _pymavlink_available = False
    return _pymavlink_available


def load_param_db(db_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load full ArduPilot parameter list from JSON DB. Returns list of param definitions."""
    if db_path is None:
        from config import PARAM_DB_PATH
        db_path = PARAM_DB_PATH
    db_path = Path(db_path)
    if not db_path.exists():
        return []
    with open(db_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("parameters", data.get("params", []))


def get_param_def(param_db: List[Dict], param_name: str) -> Optional[Dict[str, Any]]:
    """Get definition for a parameter by name."""
    for p in param_db:
        if p.get("name") == param_name:
            return p
    return None


# Param name: letters, numbers, underscore (ArduPilot style)
_PARAM_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def _parse_param_line(line: str) -> Optional[tuple]:
    """Parse one line into (name, value) or None. Tries comma, equals, then whitespace."""
    line = line.strip().strip("\r")
    if not line or line.startswith("#"):
        return None
    # 1) NAME=VALUE
    if "=" in line:
        idx = line.index("=")
        name = line[:idx].strip()
        val_str = line[idx + 1 :].strip()
        if _PARAM_NAME_RE.match(name):
            try:
                return (name, float(val_str))
            except ValueError:
                pass
    # 2) NAME,VALUE or NAME;VALUE (CSV-style; also "Index,Name,Value" skip header)
    sep = "," if "," in line else (";" if ";" in line else None)
    if sep:
        parts = [p.strip().strip('"') for p in line.split(sep)]
        if len(parts) >= 2:
            # Skip header row (e.g. Index,Name,Value)
            if parts[0].lower() in ("index", "id", "#", "num") and len(parts) >= 3:
                if "name" in parts[1].lower() or "param" in parts[1].lower():
                    return None
            name = parts[0]
            val_str = parts[1] if len(parts) > 1 else ""
            if _PARAM_NAME_RE.match(name):
                try:
                    return (name, float(val_str))
                except ValueError:
                    pass
            # Try second column as name, third as value (Index,Name,Value)
            if len(parts) >= 3 and _PARAM_NAME_RE.match(parts[1]):
                try:
                    return (parts[1], float(parts[2]))
                except ValueError:
                    pass
    # 3) PARAM_NAME\tVALUE or PARAM_NAME VALUE (tab or whitespace)
    parts = re.split(r"\s+", line, 1)
    if len(parts) >= 2:
        name = parts[0].strip()
        val_str = parts[1].strip()
        if _PARAM_NAME_RE.match(name):
            try:
                return (name, float(val_str))
            except ValueError:
                pass
    return None


def load_user_params_from_file(file_path: str | Path) -> Dict[str, float]:
    """
    Load user parameters from a .param file or plain text.
    Supports: NAME VALUE, NAME\tVALUE, NAME,VALUE, NAME=VALUE, and CSV (Name,Value or Index,Name,Value).
    Returns dict: param_name -> value (float).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return {}
    user_params = {}
    try:
        raw = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    # Strip BOM if present
    if raw.startswith("\ufeff"):
        raw = raw[1:]
    for line in raw.splitlines():
        parsed = _parse_param_line(line)
        if parsed is None:
            continue
        name, val = parsed
        user_params[name] = val
    return user_params


def fetch_user_params_mavlink(connection: str) -> Dict[str, float]:
    """
    Fetch current parameters from autopilot via MAVLink.
    connection: e.g. 'udp:127.0.0.1:14550' or 'com3' (Windows) or '/dev/ttyUSB0'.
    Returns dict: param_name -> value.
    """
    if not _check_pymavlink():
        return {}
    try:
        import pymavlink.mavutil
        mav = pymavlink.mavutil.mavlink_connection(connection)
        mav.wait_heartbeat(timeout=10)
        params = {}
        mav.mav.param_request_list_send(
            mav.target_system, mav.target_component
        )
        while True:
            msg = mav.recv_match(type="PARAM_VALUE", blocking=True, timeout=5)
            if msg is None:
                break
            name = msg.param_id.decode("utf-8").rstrip("\x00")
            params[name] = msg.param_value
            if msg.param_index == msg.param_count - 1:
                break
        return params
    except Exception:
        return {}


def save_param_db(params: List[Dict[str, Any]], db_path: Optional[Path] = None) -> None:
    """Save parameter list to JSON DB."""
    if db_path is None:
        from config import PARAM_DB_PATH
        db_path = PARAM_DB_PATH
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump({"parameters": params, "version": "4.6.2"}, f, indent=2)
