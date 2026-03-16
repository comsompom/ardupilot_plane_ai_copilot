"""
Report generation: tables per mode (Manual, FBWA, AUTO, Autotune) and export (HTML, PDF, TXT).
"""
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from .comparator import compare_params
from .params import load_param_db, load_user_params_from_file
class ReportMode(str, Enum):
    MANUAL = "Manual"
    FBWA = "FBWA"
    AUTO = "AUTO"
    AUTOTUNE = "Autotune"


def generate_report(
    user_params: Dict[str, float],
    param_db: Optional[List[Dict[str, Any]]] = None,
    mode: str = "Manual",
    plane_type_id: Optional[str] = None,
    wingspan_m: Optional[float] = None,
    weight_kg: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Generate report data for one mode.
    Returns dict with keys: mode, plane_type_id, rows (list of row dicts), summary.
    """
    if param_db is None:
        param_db = load_param_db()
    rows = compare_params(
        user_params, param_db, mode,
        plane_type_id=plane_type_id,
        wingspan_m=wingspan_m,
        weight_kg=weight_kg,
    )
    ok = sum(1 for r in rows if r.get("severity") == "OK")
    warn = sum(1 for r in rows if r.get("severity") == "Warning")
    change = sum(1 for r in rows if r.get("severity") == "Change")
    return {
        "mode": mode,
        "plane_type_id": plane_type_id,
        "wingspan_m": wingspan_m,
        "weight_kg": weight_kg,
        "rows": rows,
        "summary": {
            "total": len(rows),
            "ok": ok,
            "warning": warn,
            "change": change,
        },
    }


def _rows_to_table_html(rows: List[Dict], mode: str) -> str:
    """Render report rows as HTML table."""
    lines = [
        f'<h2>Parameter report: {mode}</h2>',
        '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse: collapse;">',
        "<thead><tr><th>Parameter</th><th>Current</th><th>Recommended</th><th>Severity</th><th>Action</th></tr></thead>",
        "<tbody>",
    ]
    for r in rows:
        cur = r.get("current_value")
        cur_str = str(cur) if cur is not None else "—"
        sev = r.get("severity", "")
        lines.append(
            f'<tr><td>{r.get("parameter", "")}</td><td>{cur_str}</td>'
            f'<td>{r.get("recommended", "")}</td><td>{sev}</td><td>{r.get("action", "")}</td></tr>'
        )
    lines.append("</tbody></table>")
    return "\n".join(lines)


def export_report_html(
    report: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> str:
    """Export report to HTML. Returns HTML string; optionally writes to file."""
    mode = report.get("mode", "Report")
    rows = report.get("rows", [])
    table = _rows_to_table_html(rows, mode)
    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>ArduPilot report - {mode}</title></head>
<body>
{table}
</body>
</html>"""
    if output_path:
        Path(output_path).write_text(html, encoding="utf-8")
    return html


def export_report_txt(
    report: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> str:
    """Export report to plain text. Returns content; optionally writes to file."""
    mode = report.get("mode", "Report")
    rows = report.get("rows", [])
    lines = [f"ArduPilot parameter report: {mode}", "=" * 50, ""]
    for r in rows:
        cur = r.get("current_value")
        cur_str = str(cur) if cur is not None else "—"
        lines.append(f"Parameter: {r.get('parameter', '')}")
        lines.append(f"  Current: {cur_str}  Recommended: {r.get('recommended', '')}")
        lines.append(f"  Severity: {r.get('severity', '')}  Action: {r.get('action', '')}")
        lines.append("")
    text = "\n".join(lines)
    if output_path:
        Path(output_path).write_text(text, encoding="utf-8")
    return text


def export_report_pdf(
    report: Dict[str, Any],
    output_path: Optional[Path] = None,
) -> Optional[bytes]:
    """Export report to PDF using reportlab. Returns PDF bytes or None on failure."""
    try:
        import io
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        return None
    mode = report.get("mode", "Report")
    rows = report.get("rows", [])
    data = [["Parameter", "Current", "Recommended", "Severity", "Action"]]
    for r in rows:
        cur = r.get("current_value")
        cur_str = str(cur) if cur is not None else "—"
        data.append([
            r.get("parameter", ""),
            cur_str,
            str(r.get("recommended", ""))[:30],
            r.get("severity", ""),
            str(r.get("action", ""))[:40],
        ])
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [Paragraph(f"ArduPilot parameter report: {mode}", styles["Heading1"])]
    t = Table(data)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ("FONTSIZE", (0, 0), (-1, 0), 10),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
        ("BACKGROUND", (0, 1), (-1, -1), colors.beige),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
    ]))
    elements.append(t)
    doc.build(elements)
    pdf_bytes = buf.getvalue()
    if output_path:
        Path(output_path).write_bytes(pdf_bytes)
    return pdf_bytes
