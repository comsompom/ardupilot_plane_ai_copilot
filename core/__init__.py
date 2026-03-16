"""
Core engine for ArduPilot AI Assistant.
Shared by standalone and Flask UIs.
"""
from .params import load_param_db, load_user_params_from_file, get_param_def
from .comparator import compare_params
from .recommendations import get_recommendations_for_mode
from .reports import generate_report, ReportMode, export_report_html, export_report_pdf, export_report_txt
from .plane_types import PLANE_TYPES, get_plane_type_info
from .ai_assistant import get_ai_response

__all__ = [
    "load_param_db",
    "load_user_params_from_file",
    "get_param_def",
    "compare_params",
    "get_recommendations_for_mode",
    "generate_report",
    "ReportMode",
    "export_report_html",
    "export_report_pdf",
    "export_report_txt",
    "PLANE_TYPES",
    "get_plane_type_info",
    "get_ai_response",
]
