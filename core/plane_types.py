"""
ArduPilot plane types and frame info.
Based on ArduPlane frame classes / MAVLink FRAME_TYPE.
"""
from dataclasses import dataclass
from typing import List, Optional

# ArduPlane frame types (simplified from ArduPilot docs)
# See: https://ardupilot.org/plane/docs/plane-frame-type.html
PLANE_TYPES = [
    {"id": "0", "name": "Undefined", "description": "Unknown or custom frame"},
    {"id": "1", "name": "QuadPlane", "description": "QuadPlane (VTOL)"},
    {"id": "2", "name": "Flying Wing", "description": "Flying wing (e.g. Zagi, Tek Sumo)"},
    {"id": "3", "name": "V-Tail", "description": "V-tail plane"},
    {"id": "4", "name": "Elevon", "description": "Elevon (delta wing)"},
    {"id": "5", "name": "Plane", "description": "Standard plane (aileron + elevator + rudder)"},
    {"id": "6", "name": "Copter", "description": "Copter (legacy)"},
    {"id": "7", "name": "Heli", "description": "Helicopter (legacy)"},
    {"id": "8", "name": "Dual Elevon", "description": "Dual elevon (elevons on two wings)"},
    {"id": "9", "name": "Dual Servo", "description": "Dual servo (two aileron servos)"},
    {"id": "10", "name": "Tailtrottle", "description": "Tail-sitter / throttle on tail"},
    {"id": "11", "name": "Custom", "description": "Custom frame type"},
]


@dataclass
class PlaneTypeInfo:
    id: str
    name: str
    description: str


def get_plane_type_info(plane_type_id: Optional[str] = None) -> List[PlaneTypeInfo]:
    """Return list of plane type info; if id given, filter to that one."""
    infos = [PlaneTypeInfo(id=t["id"], name=t["name"], description=t["description"]) for t in PLANE_TYPES]
    if plane_type_id is not None:
        infos = [p for p in infos if p.id == str(plane_type_id)]
    return infos


def get_plane_type_name(plane_type_id: str) -> str:
    """Get display name for a plane type ID."""
    for t in PLANE_TYPES:
        if t["id"] == str(plane_type_id):
            return t["name"]
    return "Unknown"
