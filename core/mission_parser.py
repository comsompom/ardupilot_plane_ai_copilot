"""
Mission Planner / waypoint file parser (MVP).
Supports common mission file formats (.waypoints, .plan, or similar).
"""
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


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
    return {"waypoints": waypoints, "commands": commands, "raw_lines": raw_lines, "errors": errors}


def analyze_mission(mission_data: Dict[str, Any], plane_type_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Simple analysis: basic sanity checks and suggestions.
    """
    wp = mission_data.get("waypoints", [])
    suggestions = []
    if not wp:
        return {"ok": False, "suggestions": ["No waypoints found."], "summary": "Empty or invalid mission."}
    # Check for HOME (command 16) and common commands
    cmds = mission_data.get("commands", [])
    if 16 not in cmds and wp:
        suggestions.append("Consider adding a HOME waypoint (command 16).")
    if 22 in cmds:  # TAKEOFF
        suggestions.append("TAKEOFF present; ensure altitude and throttle are set for your plane.")
    if 20 in cmds or 21 in cmds:  # RETURN_TO_LAUNCH, LAND
        suggestions.append("RTL/LAND present; verify RTL_ALTITUDE and landing parameters.")
    return {
        "ok": len(suggestions) == 0,
        "suggestions": suggestions or ["Mission has waypoints; review climb rates and turn radii for your plane type."],
        "summary": f"{len(wp)} waypoints, {len(set(cmds))} unique commands.",
    }
