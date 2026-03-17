"""
Mission Planner / waypoint file parser.
Supports common mission file formats (.waypoints, .plan, or similar).
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

# Common MAV_CMD names for mission display
MAV_CMD_NAMES = {
    16: "WAYPOINT",
    20: "RETURN_TO_LAUNCH",
    21: "LAND",
    22: "TAKEOFF",
    17: "LOITER_UNLIM",
    18: "LOITER_TURNS",
    19: "LOITER_TIME",
    24: "LOITER_TO_ALT",
    25: "DO_FOLLOW",
    30: "CONDITION_CHANGE_ALT",
    31: "CONDITION_DISTANCE",
    112: "DO_CHANGE_SPEED",
    115: "DO_SET_SERVO",
    178: "DO_LAND_START",
    189: "DO_DIGICAM_CONTROL",
    201: "DO_SET_HOME",
    205: "DO_CONTROL_VIDEO",
    206: "DO_SET_ROI",
    214: "DO_MOUNT_CONTROL",
    220: "DO_SET_CAM_TRIGG_DIST",
    221: "DO_FENCE_ENABLE",
    300: "DO_SET_RESUME_REPEAT_DIST",
}


def parse_mission_file(file_path: str | Path) -> Dict[str, Any]:
    """
    Parse a mission file. Returns dict with keys: waypoints, commands, raw_lines, errors.
    """
    path = Path(file_path)
    if not path.exists():
        return {"waypoints": [], "commands": [], "raw_lines": [], "errors": ["File not found"]}
    text = path.read_text(encoding="utf-8", errors="replace")
    waypoints = []
    commands = []
    errors = []
    raw_lines = text.splitlines()
    # Simple QGC/Mission Planner style: QGC WPL 110 (version), then index, current, coord_frame, command, p1..p7, lat, lon, alt
    for i, line in enumerate(raw_lines):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t") if "\t" in line else line.split()
        if len(parts) >= 9:
            try:
                idx = int(parts[0])
                current = int(parts[1])
                frame = int(parts[2])
                cmd = int(parts[3])
                p1, p2, p3, p4 = float(parts[4]), float(parts[5]), float(parts[6]), float(parts[7])
                lat, lon, alt = float(parts[8]), float(parts[9]) if len(parts) > 9 else 0, float(parts[10]) if len(parts) > 10 else 0
                waypoints.append({
                    "index": idx, "current": current, "frame": frame, "command": cmd,
                    "p1": p1, "p2": p2, "p3": p3, "p4": p4,
                    "lat": lat, "lon": lon, "alt": alt,
                })
                commands.append(cmd)
            except (ValueError, IndexError):
                errors.append(f"Line {i+1}: parse error")
    # Build summary: command counts, waypoint list summary
    cmd_counts: Dict[int, int] = {}
    for c in commands:
        cmd_counts[c] = cmd_counts.get(c, 0) + 1
    wp_summary = []
    for w in waypoints[:50]:  # first 50 for display
        cmd = w.get("command", 0)
        name = MAV_CMD_NAMES.get(cmd, f"CMD_{cmd}")
        wp_summary.append({
            "index": w.get("index"),
            "command": cmd,
            "command_name": name,
            "lat": w.get("lat"), "lon": w.get("lon"), "alt": w.get("alt"),
        })
    summary = {
        "waypoint_count": len(waypoints),
        "unique_commands": len(set(commands)),
        "command_breakdown": {MAV_CMD_NAMES.get(c, f"CMD_{c}"): n for c, n in sorted(cmd_counts.items(), key=lambda x: -x[1])},
        "has_home": 16 in commands,
        "has_takeoff": 22 in commands,
        "has_rtl": 20 in commands,
        "has_land": 21 in commands,
        "parse_errors": len(errors),
    }
    return {
        "waypoints": waypoints,
        "commands": commands,
        "raw_lines": raw_lines,
        "errors": errors,
        "summary": summary,
        "waypoint_summary": wp_summary,
    }


def analyze_mission(mission_data: Dict[str, Any], plane_type_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Basic sanity checks and suggestions from parsed mission.
    """
    wp = mission_data.get("waypoints", [])
    suggestions = []
    if not wp:
        return {"ok": False, "suggestions": ["No waypoints found."], "summary": "Empty or invalid mission."}
    cmds = mission_data.get("commands", [])
    if 16 not in cmds and wp:
        suggestions.append("Consider adding a HOME waypoint (command 16).")
    if 22 in cmds:
        suggestions.append("TAKEOFF present; ensure altitude and throttle are set for your plane.")
    if 20 in cmds or 21 in cmds:
        suggestions.append("RTL/LAND present; verify RTL_ALTITUDE and landing parameters.")
    s = mission_data.get("summary", {})
    waypoint_count = s.get("waypoint_count", len(wp))
    unique = s.get("unique_commands", len(set(cmds)))
    summary = f"{waypoint_count} waypoints, {unique} unique commands."
    if mission_data.get("errors"):
        summary += f" ({len(mission_data['errors'])} parse warning(s).)"
    return {
        "ok": len(suggestions) == 0,
        "suggestions": suggestions or ["Mission has waypoints; review climb rates and turn radii for your plane type."],
        "summary": summary,
    }
