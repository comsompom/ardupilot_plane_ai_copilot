"""
Compare user parameters vs ArduPilot param list and recommended sets per flight mode.
"""
from typing import Any, Dict, List, Optional, Tuple

from .recommendations import (
    SEVERITY_OK,
    SEVERITY_WARNING,
    SEVERITY_CHANGE,
    SEVERITY_CRITICAL,
    get_recommendations_for_mode,
)


def _in_range(value: float, spec: Any) -> bool:
    """Check if value is within recommended (single value or (min, max) tuple)."""
    if isinstance(spec, (int, float)):
        return abs(value - float(spec)) < 1e-6
    if isinstance(spec, (list, tuple)) and len(spec) >= 2:
        lo, hi = float(spec[0]), float(spec[1])
        return lo <= value <= hi
    return False


def compare_params(
    user_params: Dict[str, float],
    param_db: List[Dict[str, Any]],
    mode: str,
    plane_type_id: Optional[str] = None,
    wingspan_m: Optional[float] = None,
    weight_kg: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Compare user params vs recommendations for the given flight mode.
    Returns list of rows: parameter, current_value, recommended, severity, action_note.
    """
    recs = get_recommendations_for_mode(mode)
    param_db_by_name = {p.get("name"): p for p in param_db if p.get("name")}

    rows = []
    seen = set()

    for param_name, rec in recs.items():
        recommended = rec.get("recommended")
        note = rec.get("note", "")
        current = user_params.get(param_name)
        defn = param_db_by_name.get(param_name, {})

        if current is None:
            # Parameter missing in user config
            rec_str = str(recommended) if recommended is not None else "—"
            rows.append({
                "parameter": param_name,
                "current_value": None,
                "recommended": rec_str,
                "severity": SEVERITY_CHANGE,
                "action": f"Consider adding: {note}",
                "description": defn.get("description", ""),
            })
            seen.add(param_name)
            continue

        current_f = float(current)
        if _in_range(current_f, recommended):
            rows.append({
                "parameter": param_name,
                "current_value": current_f,
                "recommended": str(recommended),
                "severity": SEVERITY_OK,
                "action": "OK",
                "description": defn.get("description", ""),
            })
        else:
            rec_str = str(recommended) if recommended is not None else "—"
            rows.append({
                "parameter": param_name,
                "current_value": current_f,
                "recommended": rec_str,
                "severity": SEVERITY_WARNING,
                "action": f"Consider changing: {note}",
                "description": defn.get("description", ""),
            })
        seen.add(param_name)

    # Optionally add params from param_db that are in user_params but not in recs
    # (e.g. for "missing from recommended set" we already cover recs; here we could
    # report "unknown param" or "extra param" — skip for simplicity)

    return rows


