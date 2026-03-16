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


def load_user_params_from_file(file_path: str | Path) -> Dict[str, float]:
    """
    Load user parameters from a .param file or plain text (NAME VALUE lines).
    Returns dict: param_name -> value (float).
    """
    file_path = Path(file_path)
    if not file_path.exists():
        return {}
    user_params = {}
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            # Format: PARAM_NAME\tVALUE or PARAM_NAME VALUE
            parts = re.split(r"\s+", line, 1)
            if len(parts) >= 2:
                name = parts[0].strip()
                try:
                    val = float(parts[1].strip())
                    user_params[name] = val
                except ValueError:
                    pass
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
