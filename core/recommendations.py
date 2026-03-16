"""
Recommended parameter sets/ranges for Manual, FBWA, AUTO, Autotune.
Based on ArduPilot Plane docs and common best practices.
These are used by the comparison engine to suggest changes.
"""
from typing import Any, Dict, List, Optional

# Severity levels for report
SEVERITY_OK = "OK"
SEVERITY_WARNING = "Warning"
SEVERITY_CHANGE = "Change"
SEVERITY_CRITICAL = "Critical"

# Recommended param names and suggested values/ranges per flight mode.
# Format: param_name -> {"recommended": value or (min, max), "note": "..."}
# We keep these minimal; full list can be extended from ArduPilot docs.

MANUAL_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
    "SERVO_AUTO_TRIM": {"recommended": 0, "note": "Disable for manual; trim manually."},
    "FLTMODE1": {"recommended": 0, "note": "Manual mode."},
    "LIM_ROLL_CD": {"recommended": (3000, 4500), "note": "Roll limit (centidegrees)."},
    "LIM_PITCH_MAX": {"recommended": (2000, 3000), "note": "Max pitch up (centidegrees)."},
    "LIM_PITCH_MIN": {"recommended": (-3000, -2000), "note": "Max pitch down (centidegrees)."},
    "ARSPD_FBW_MIN": {"recommended": (800, 1500), "note": "Min airspeed for FBW (cm/s); set for stall margin."},
    "ARSPD_FBW_MAX": {"recommended": (2500, 5000), "note": "Max airspeed (cm/s)."},
}

FBWA_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
    "SERVO_AUTO_TRIM": {"recommended": 1, "note": "Enable auto-trim in FBWA."},
    "FLTMODE2": {"recommended": 5, "note": "FBWA = 5."},
    "LIM_ROLL_CD": {"recommended": (3000, 4500), "note": "Roll limit (centidegrees)."},
    "LIM_PITCH_MAX": {"recommended": (2000, 3000), "note": "Max pitch up."},
    "LIM_PITCH_MIN": {"recommended": (-3000, -2000), "note": "Max pitch down."},
    "ARSPD_FBW_MIN": {"recommended": (800, 1500), "note": "Min airspeed (cm/s)."},
    "ARSPD_FBW_MAX": {"recommended": (2500, 5000), "note": "Max airspeed (cm/s)."},
    "STALL_PREVENTION": {"recommended": 1, "note": "Enable stall prevention in FBWA."},
    "BATT_LOW_VOLT": {"recommended": (10.5, 11.0), "note": "Low voltage warning (V)."},
}

AUTO_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
    "FLTMODE3": {"recommended": 10, "note": "AUTO = 10."},
    "WP_LOITER_RAD": {"recommended": (800, 3000), "note": "Loiter radius (cm)."},
    "WP_RADIUS": {"recommended": (200, 1000), "note": "Waypoint radius (cm)."},
    "ALT_HOLD_RTL": {"recommended": (5000, 15000), "note": "RTL altitude (cm)."},
    "FS_THR_ENABLE": {"recommended": 1, "note": "Enable failsafe throttle."},
    "FS_THR_VALUE": {"recommended": (0, 200), "note": "Throttle PWM at failsafe."},
    "BATT_LOW_VOLT": {"recommended": (10.5, 11.0), "note": "Low voltage (V)."},
    "BATT_CRT_VOLT": {"recommended": (10.0, 10.5), "note": "Critical voltage (V)."},
    "RTL_ALTITUDE": {"recommended": (5000, 15000), "note": "RTL altitude (cm)."},
}

AUTOTUNE_RECOMMENDATIONS: Dict[str, Dict[str, Any]] = {
    "AUTOTUNE_LEVEL": {"recommended": (5, 8), "note": "Autotune aggression (5–8 typical)."},
    "FLTMODE6": {"recommended": 6, "note": "Autotune mode = 6."},
    "STAB_PITCH_P": {"recommended": (0.08, 0.25), "note": "Pitch P (will be tuned)."},
    "STAB_PITCH_I": {"recommended": (0.0, 0.1), "note": "Pitch I."},
    "STAB_PITCH_D": {"recommended": (0.0, 0.02), "note": "Pitch D."},
    "STAB_ROLL_P": {"recommended": (0.08, 0.25), "note": "Roll P (will be tuned)."},
    "STAB_ROLL_I": {"recommended": (0.0, 0.1), "note": "Roll I."},
    "STAB_ROLL_D": {"recommended": (0.0, 0.02), "note": "Roll D."},
    "LIM_ROLL_CD": {"recommended": (3000, 4500), "note": "Roll limit for autotune."},
}


def get_recommendations_for_mode(mode: str) -> Dict[str, Dict[str, Any]]:
    """Return recommendation map for mode: Manual, FBWA, AUTO, Autotune."""
    mode = (mode or "").strip().lower()
    if mode == "manual":
        return dict(MANUAL_RECOMMENDATIONS)
    if mode == "fbwa":
        return dict(FBWA_RECOMMENDATIONS)
    if mode == "auto":
        return dict(AUTO_RECOMMENDATIONS)
    if mode == "autotune":
        return dict(AUTOTUNE_RECOMMENDATIONS)
    return {}
