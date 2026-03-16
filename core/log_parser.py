"""
ArduPilot flight log parser (MVP).
Supports binary .bin logs via pymavlink or plain text .log if applicable.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

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


def parse_flight_log(file_path: str | Path) -> Dict[str, Any]:
    """
    Parse ArduPilot binary log (.bin). Returns dict with summary and events.
    """
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "error": "File not found", "events": [], "summary": {}}
    if not _check_pymavlink():
        return {"ok": False, "error": "pymavlink required for .bin log parsing", "events": [], "summary": {}}
    try:
        from pymavlink.mavutil import mavlink_connection
        mlog = mavlink_connection(str(path))
        events = []
        mode_changes = []
        last_mode = None
        while True:
            msg = mlog.recv_match(blocking=False)
            if msg is None:
                break
            mtype = msg.get_type()
            if mtype == "HEARTBEAT":
                mode = getattr(msg, "custom_mode", None)
                if mode is not None and mode != last_mode:
                    mode_changes.append({"time": getattr(msg, "time_boot_ms", 0), "mode": mode})
                    last_mode = mode
            elif mtype in ("EV", "STATUSTEXT"):
                text = getattr(msg, "text", str(msg))[:80]
                events.append({"type": mtype, "text": text})
        summary = {"mode_changes": len(mode_changes), "events": len(events)}
        return {"ok": True, "events": events[:100], "mode_changes": mode_changes[:50], "summary": summary}
    except Exception as e:
        return {"ok": False, "error": str(e), "events": [], "summary": {}}


def analyze_flight_log(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """Suggest what to fix based on log summary."""
    if not log_data.get("ok"):
        return {"suggestions": [f"Could not parse log: {log_data.get('error', 'Unknown')}."], "summary": "Parse failed."}
    suggestions = []
    s = log_data.get("summary", {})
    if s.get("events", 0) > 20:
        suggestions.append("Many events in log; review for errors or warnings.")
    if s.get("mode_changes", 0) > 10:
        suggestions.append("Frequent mode changes; ensure flight mode setup and failsafes are correct.")
    if not suggestions:
        suggestions.append("Log parsed; review events and mode changes for your plane type.")
    return {"suggestions": suggestions, "summary": str(s)}
