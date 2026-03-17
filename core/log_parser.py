"""
ArduPilot flight log parser.
Supports binary .bin logs via pymavlink; extracts message counts, time range, mode changes, and events.
"""
from pathlib import Path
from typing import Any, Dict, List, Optional

_pymavlink_available = None

# ArduPlane custom_mode values (common)
FLIGHT_MODE_NAMES = {
    0: "Manual", 1: "CIRCLE", 2: "STABILIZE", 3: "TRAINING",
    5: "FBWA", 6: "FBWB", 7: "CRUISE", 10: "AUTO", 11: "RTL",
    12: "LOITER", 14: "AVOID_ADSB", 15: "GUIDED", 16: "INITIALISING",
    17: "QSTABILIZE", 18: "QHOVER", 19: "QLOITER", 20: "QLAND",
    21: "QRTL", 22: "QAUTOTUNE", 23: "THERMAL",
}


def _check_pymavlink():
    global _pymavlink_available
    if _pymavlink_available is None:
        try:
            import pymavlink.mavutil
            _pymavlink_available = True
        except ImportError:
            _pymavlink_available = False
    return _pymavlink_available


def _get_msg_time(msg: Any) -> Optional[float]:
    """Extract timestamp from message (seconds) if available."""
    for attr in ("time_boot_ms", "time_usec", "TimeUS"):
        t = getattr(msg, attr, None)
        if t is not None:
            if "usec" in attr or attr == "TimeUS":
                return float(t) / 1e6
            return float(t) / 1000.0
    return None


def parse_flight_log(file_path: str | Path) -> Dict[str, Any]:
    """
    Parse ArduPilot binary log (.bin). Returns dict with message counts, time range, mode changes, events.
    """
    path = Path(file_path)
    if not path.exists():
        return {"ok": False, "error": "File not found", "events": [], "mode_changes": [], "message_counts": {}, "summary": {}}
    if not _check_pymavlink():
        return {"ok": False, "error": "pymavlink required for .bin log parsing", "events": [], "mode_changes": [], "message_counts": {}, "summary": {}}
    try:
        from pymavlink.mavutil import mavlink_connection
        mlog = mavlink_connection(str(path))
        events: List[Dict[str, Any]] = []
        mode_changes: List[Dict[str, Any]] = []
        message_counts: Dict[str, int] = {}
        first_ts: Optional[float] = None
        last_ts: Optional[float] = None
        last_mode = None
        while True:
            msg = mlog.recv_match(blocking=False)
            if msg is None:
                break
            mtype = msg.get_type()
            message_counts[mtype] = message_counts.get(mtype, 0) + 1
            ts = _get_msg_time(msg)
            if ts is not None:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
            if mtype == "HEARTBEAT":
                mode = getattr(msg, "custom_mode", None)
                if mode is not None and mode != last_mode:
                    mode_name = FLIGHT_MODE_NAMES.get(mode, f"Mode_{mode}")
                    mode_changes.append({"time_s": ts, "time_boot_ms": getattr(msg, "time_boot_ms", 0), "mode": mode, "mode_name": mode_name})
                    last_mode = mode
            elif mtype in ("EV", "STATUSTEXT", "MESSAGE"):
                text = getattr(msg, "text", None) or getattr(msg, "Message", str(msg))
                if isinstance(text, (bytes, bytearray)):
                    text = text.decode("utf-8", errors="replace").rstrip("\x00")
                text = str(text)[:120]
                events.append({"type": mtype, "text": text, "time_s": ts})
        total_messages = sum(message_counts.values())
        duration_s = (last_ts - first_ts) if (first_ts is not None and last_ts is not None) else None
        summary = {
            "total_messages": total_messages,
            "message_types": len(message_counts),
            "mode_changes": len(mode_changes),
            "events": len(events),
            "duration_seconds": round(duration_s, 1) if duration_s is not None else None,
            "first_ts": first_ts,
            "last_ts": last_ts,
        }
        return {
            "ok": True,
            "events": events[:200],
            "mode_changes": mode_changes[:100],
            "message_counts": dict(sorted(message_counts.items(), key=lambda x: -x[1])),
            "summary": summary,
        }
    except Exception as e:
        return {"ok": False, "error": str(e), "events": [], "mode_changes": [], "message_counts": {}, "summary": {}}


def analyze_flight_log(log_data: Dict[str, Any]) -> Dict[str, Any]:
    """Suggest what to fix based on log summary; returns suggestions and human-readable summary."""
    if not log_data.get("ok"):
        return {"suggestions": [f"Could not parse log: {log_data.get('error', 'Unknown')}."], "summary": "Parse failed.", "parsed_overview": None}
    s = log_data.get("summary", {})
    total = s.get("total_messages", 0)
    mode_count = s.get("mode_changes", 0)
    event_count = s.get("events", 0)
    duration = s.get("duration_seconds")
    suggestions = []
    if total == 0:
        suggestions.append("No messages found in log; file may be empty or not a valid ArduPilot .bin log.")
    else:
        if event_count > 20:
            suggestions.append("Many events in log; review for errors or warnings.")
        if mode_count > 10:
            suggestions.append("Frequent mode changes; ensure flight mode setup and failsafes are correct.")
        if not suggestions:
            suggestions.append("Log parsed successfully; review message breakdown and mode changes for your plane type.")
    lines = [f"Total messages: {total}"]
    if duration is not None:
        lines.append(f"Duration: {duration:.1f} s")
    lines.append(f"Message types: {s.get('message_types', 0)}")
    lines.append(f"Mode changes: {mode_count} | Events: {event_count}")
    return {"suggestions": suggestions, "summary": "; ".join(lines), "parsed_overview": s}
