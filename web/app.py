"""
Flask web app for ArduPilot AI Assistant.
"""
import io
import sys
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename

from config import PARAM_DB_PATH, DATA_DIR
from core.params import load_param_db, load_user_params_from_file, fetch_user_params_mavlink
from core.plane_types import PLANE_TYPES, get_plane_type_name
from core.reports import (
    generate_report,
    ReportMode,
    export_report_html,
    export_report_pdf,
    export_report_txt,
)
from core.ai_assistant import get_ai_response, get_report_summary_ai, get_flight_log_ai_analysis, get_mission_ai_analysis
from core.mission_parser import parse_mission_file, analyze_mission
from core.log_parser import parse_flight_log, analyze_flight_log

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "dev-secret-change-in-production"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
UPLOAD_FOLDER = DATA_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

MODES = [ReportMode.MANUAL.value, ReportMode.FBWA.value, ReportMode.AUTO.value, ReportMode.AUTOTUNE.value]


@app.route("/")
def index():
    return render_template("index.html", plane_types=PLANE_TYPES, modes=MODES)


@app.route("/api/params/upload", methods=["POST"])
def upload_params():
    """Upload param file; return parsed params as JSON."""
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    filename = secure_filename(f.filename) or "params.param"
    path = Path(app.config["UPLOAD_FOLDER"]) / filename
    f.save(str(path))
    params = load_user_params_from_file(path)
    return jsonify({"params": params, "count": len(params)})


@app.route("/api/params/analyze-file", methods=["POST"])
def analyze_param_file():
    """When a param file parses to 0 params, analyze file content with AI and return suggestions."""
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    agent = (request.form.get("agent") or "").strip().lower()
    prefer_provider = agent if agent in ("openai", "ollama") else None
    try:
        raw = f.read().decode("utf-8", errors="replace")
        if raw.startswith("\ufeff"):
            raw = raw[1:]
        snippet = raw[:2500].strip() or "(file empty or unreadable)"
    except Exception as e:
        return jsonify({"error": f"Could not read file: {e}"}), 400
    question = (
        "The user loaded this file as an ArduPilot Plane parameter file, but the parser found 0 parameters. "
        "Here is the start of the file:\n\n---\n" + snippet + "\n---\n\n"
        "What might be wrong? What format does ArduPilot expect for .param files? "
        "Give 2–4 short, actionable suggestions so the user can fix the file or get a valid parameter dump."
    )
    result = get_ai_response(question, param_db=[], prefer_provider=prefer_provider)
    return jsonify({
        "response": result.get("response", ""),
        "source": result.get("source", ""),
        "error": result.get("error"),
    })


@app.route("/api/params/fetch", methods=["POST"])
def fetch_params():
    """Fetch params via MAVLink from connection string."""
    data = request.get_json() or {}
    conn = data.get("connection", "").strip()
    if not conn:
        return jsonify({"error": "Connection string required"}), 400
    params = fetch_user_params_mavlink(conn)
    return jsonify({"params": params, "count": len(params)})


@app.route("/api/compare", methods=["POST"])
def compare():
    """Run comparison for all modes; optionally get AI summary. Returns reports and optionally ai_summary."""
    data = request.get_json() or {}
    params = data.get("params", {})
    if not params:
        return jsonify({"error": "No parameters. Upload a param file or fetch via MAVLink first."}), 400
    plane_type_id = data.get("plane_type_id")
    wingspan_m = data.get("wingspan_m")
    weight_kg = data.get("weight_kg")
    use_ai = data.get("use_ai", False)
    agent = (data.get("agent") or "").strip().lower()  # "openai" | "ollama"
    if wingspan_m is not None:
        try:
            wingspan_m = float(wingspan_m)
        except (TypeError, ValueError):
            wingspan_m = None
    if weight_kg is not None:
        try:
            weight_kg = float(weight_kg)
        except (TypeError, ValueError):
            weight_kg = None

    param_db = load_param_db()
    reports = {}
    for mode in MODES:
        reports[mode] = generate_report(
            params, param_db=param_db, mode=mode,
            plane_type_id=plane_type_id,
            wingspan_m=wingspan_m,
            weight_kg=weight_kg,
        )
    out = {"reports": reports}
    if use_ai and agent in ("openai", "ollama"):
        plane_type_name = get_plane_type_name(plane_type_id) if plane_type_id else None
        ai_result = get_report_summary_ai(reports, plane_type_name=plane_type_name, prefer_provider=agent)
        out["ai_summary"] = ai_result.get("response", "")
        out["ai_source"] = ai_result.get("source", "")
        out["ai_error"] = ai_result.get("error")
    return jsonify(out)


@app.route("/api/export/<mode>", methods=["POST"])
def export(mode):
    """Export report for mode as HTML, PDF, or TXT. Body: { format: 'html'|'pdf'|'txt', report: {...} }."""
    data = request.get_json() or {}
    report = data.get("report", {})
    fmt = (data.get("format") or "html").lower()
    if not report or not report.get("rows"):
        return jsonify({"error": "No report data"}), 400

    if fmt == "html":
        html = export_report_html(report)
        return send_file(
            io.BytesIO(html.encode("utf-8")),
            mimetype="text/html",
            as_attachment=True,
            download_name=f"ardupilot_report_{mode}.html",
        )
    if fmt == "txt":
        txt = export_report_txt(report)
        return send_file(
            io.BytesIO(txt.encode("utf-8")),
            mimetype="text/plain",
            as_attachment=True,
            download_name=f"ardupilot_report_{mode}.txt",
        )
    if fmt == "pdf":
        pdf_bytes = export_report_pdf(report)
        if pdf_bytes is None:
            return jsonify({"error": "PDF generation failed (reportlab required)"}), 500
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype="application/pdf",
            as_attachment=True,
            download_name=f"ardupilot_report_{mode}.pdf",
        )
    return jsonify({"error": "Unsupported format"}), 400


@app.route("/api/mission/analyze", methods=["POST"])
def mission_analyze():
    """Upload mission file; return parsing, analysis/suggestions, and optional AI interpretation."""
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(f.filename)
    f.save(str(path))
    data = parse_mission_file(path)
    plane_type_id = request.form.get("plane_type_id")
    plane_type_name = get_plane_type_name(plane_type_id) if plane_type_id else None
    analysis = analyze_mission(data, plane_type_id=plane_type_id)
    out = {"mission": data, "analysis": analysis}
    use_ai = request.form.get("use_ai", "").lower() in ("1", "true", "yes")
    agent = (request.form.get("agent") or "").strip().lower()
    agent = agent if agent in ("openai", "ollama") else None
    if use_ai and agent:
        ai_result = get_mission_ai_analysis(data, plane_type_name=plane_type_name, prefer_provider=agent)
        out["ai_interpretation"] = ai_result.get("response") or ai_result.get("error")
        out["ai_source"] = ai_result.get("source")
    return jsonify(out)


@app.route("/api/log/analyze", methods=["POST"])
def log_analyze():
    """Upload flight log; return parsing result, suggestions, and optional AI interpretation."""
    if "file" not in request.files:
        return jsonify({"error": "No file"}), 400
    f = request.files["file"]
    if f.filename == "":
        return jsonify({"error": "No file selected"}), 400
    use_ai = request.form.get("use_ai", "").lower() in ("1", "true", "yes")
    agent = (request.form.get("agent") or "").strip().lower()
    agent = agent if agent in ("openai", "ollama") else None
    path = Path(app.config["UPLOAD_FOLDER"]) / secure_filename(f.filename)
    f.save(str(path))
    data = parse_flight_log(path)
    analysis = analyze_flight_log(data)
    out = {"log": data, "analysis": analysis}
    if use_ai and agent:
        ai_result = get_flight_log_ai_analysis(data, prefer_provider=agent)
        out["ai_interpretation"] = ai_result.get("response", "")
        out["ai_source"] = ai_result.get("source", "")
    return jsonify(out)


@app.route("/api/assistant", methods=["POST"])
def assistant():
    """AI assistant: send question, get response. Optional agent: openai | ollama."""
    data = request.get_json() or {}
    question = (data.get("question") or "").strip()
    if not question:
        return jsonify({"error": "Question required"}), 400
    plane_type_id = data.get("plane_type_id")
    plane_type_name = get_plane_type_name(plane_type_id) if plane_type_id else None
    user_params = data.get("params", {})
    report_summary = data.get("report_summary", {})
    agent = (data.get("agent") or "").strip().lower()
    prefer_provider = agent if agent in ("openai", "ollama") else None
    param_db = load_param_db()
    result = get_ai_response(
        question,
        plane_type_id=plane_type_id,
        plane_type_name=plane_type_name,
        user_params=user_params,
        report_summary=report_summary,
        param_db=param_db,
        prefer_provider=prefer_provider,
    )
    return jsonify(result)


def main():
    from config import FLASK_DEBUG, FLASK_SECRET_KEY
    app.secret_key = FLASK_SECRET_KEY
    app.run(debug=FLASK_DEBUG, host="0.0.0.0", port=5000, use_reloader=False)


if __name__ == "__main__":
    main()
