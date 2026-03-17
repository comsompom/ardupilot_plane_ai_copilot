"""
AI assistant: OpenAI (when online + key set), local Ollama, or keyword fallback.
Uses OpenAI when OPENAI_API_KEY is set and request succeeds; else Ollama; else fallback.
"""
from typing import Any, Dict, List, Optional

_openai_available = None
_ollama_available = None
_embeddings_available = None


def _check_openai_key() -> bool:
    """True if OpenAI API key is configured."""
    try:
        from config import OPENAI_API_KEY
        return bool(OPENAI_API_KEY)
    except Exception:
        return False


def _check_ollama():
    global _ollama_available
    if _ollama_available is None:
        try:
            import ollama
            _ollama_available = True
        except ImportError:
            _ollama_available = False
    return _ollama_available


def _check_embeddings():
    global _embeddings_available
    if _embeddings_available is None:
        try:
            from sentence_transformers import SentenceTransformer
            _embeddings_available = True
        except ImportError:
            _embeddings_available = False
    return _embeddings_available


def _get_param_context(param_db: List[Dict], user_params: Dict[str, float], top_k: int = 10) -> str:
    """Build a short text context from param DB and user params for the LLM."""
    lines = ["ArduPilot Plane parameters (relevant):"]
    for p in param_db[:50]:  # limit size
        name = p.get("name", "")
        desc = p.get("description", "") or p.get("Description", "")
        default = p.get("default", p.get("Default", ""))
        if name:
            lines.append(f"- {name}: {desc} (default: {default})")
    lines.append("\nUser current parameters (sample):")
    for k, v in list(user_params.items())[:30]:
        lines.append(f"- {k} = {v}")
    return "\n".join(lines)


def _call_openai(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Call OpenAI API. Returns dict with response, source='openai', and optional error."""
    try:
        from openai import OpenAI
        from config import OPENAI_API_KEY, OPENAI_MODEL
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=1024,
        )
        text = (response.choices[0].message.content or "").strip()
        if text:
            return {"response": text, "source": "openai", "error": None}
        return {"response": "", "source": "openai", "error": "Empty response from OpenAI"}
    except Exception as e:
        return {"response": "", "source": "openai", "error": str(e)}


def _call_ollama(system_prompt: str, user_prompt: str) -> Dict[str, Any]:
    """Call Ollama API. Returns dict with response, source='ollama', and optional error."""
    try:
        import ollama
        from config import OLLAMA_MODEL, OLLAMA_BASE_URL
        client = ollama.Client(host=OLLAMA_BASE_URL)
        response = client.chat(
            model=OLLAMA_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        text = response.get("message", {}).get("content", "")
        if text:
            return {"response": text.strip(), "source": "ollama", "error": None}
        return {"response": "", "source": "ollama", "error": "Empty response from Ollama"}
    except Exception as e:
        return {"response": "", "source": "ollama", "error": str(e)}


def get_ai_response(
    user_question: str,
    plane_type_id: Optional[str] = None,
    plane_type_name: Optional[str] = None,
    user_params: Optional[Dict[str, float]] = None,
    report_summary: Optional[Dict[str, Any]] = None,
    param_db: Optional[List[Dict]] = None,
    use_rag: bool = True,
    prefer_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Get AI assistant response.
    prefer_provider: "openai" | "ollama" | None. If set, use only that provider (or fallback on failure).
    Otherwise: OpenAI (if key set and online), then Ollama (local), then keyword fallback.
    Returns dict: { "response": str, "source": "openai" | "ollama" | "fallback", "error": str | None }.
    """
    user_params = user_params or {}
    report_summary = report_summary or {}
    param_db = param_db or []

    context = _get_param_context(param_db, user_params)
    system_prompt = (
        "You are an ArduPilot Plane assistant. Help the pilot with parameter settings, "
        "flight modes (Manual, FBWA, AUTO, Autotune), and safety. Be concise and cite parameter names. "
        "If you don't know, say so. Answer in 2-4 short paragraphs."
    )
    if plane_type_name:
        system_prompt += f" The user's plane type is: {plane_type_name}."
    user_prompt = f"{user_question}\n\nContext:\n{context[:2000]}"

    # User chose a specific provider
    if prefer_provider == "openai" and _check_openai_key():
        result = _call_openai(system_prompt, user_prompt)
        if result.get("response"):
            return result
        return {"response": result.get("error") or "OpenAI failed.", "source": "fallback", "error": result.get("error")}
    if prefer_provider == "ollama" and _check_ollama():
        result = _call_ollama(system_prompt, user_prompt)
        if result.get("response"):
            return result
        return {"response": result.get("error") or "Ollama failed.", "source": "fallback", "error": result.get("error")}

    # Auto: try OpenAI then Ollama then fallback
    if _check_openai_key():
        result = _call_openai(system_prompt, user_prompt)
        if result.get("response") and not result.get("error"):
            return result

    if _check_ollama():
        result = _call_ollama(system_prompt, user_prompt)
        if result.get("response"):
            return result

    # Fallback: simple keyword-based answers when no LLM or both failed
    q = user_question.lower()
    if "fbwa" in q or "fly by wire" in q:
        fallback = (
            "For FBWA (Fly-By-Wire A), enable SERVO_AUTO_TRIM and set STALL_PREVENTION. "
            "Check LIM_ROLL_CD and LIM_PITCH_MAX/MIN for your plane. Use ARSPD_FBW_MIN/MAX for airspeed limits."
        )
    elif "auto" in q and "waypoint" in q:
        fallback = (
            "For AUTO (waypoints): set FS_THR_ENABLE and FS_THR_VALUE for failsafe. "
            "WP_RADIUS and WP_LOITER_RAD affect waypoint behavior. Set RTL_ALTITUDE and BATT_LOW_VOLT for safety."
        )
    elif "autotune" in q or "pid" in q:
        fallback = (
            "For Autotune: switch to Autotune mode (FLTMODE6=6). Use AUTOTUNE_LEVEL 5-8. "
            "STAB_PITCH_P/I/D and STAB_ROLL_P/I/D will be tuned. Ensure LIM_ROLL_CD is safe for oscillations."
        )
    elif "manual" in q:
        fallback = (
            "For Manual: set SERVO_AUTO_TRIM=0. Trim manually. LIM_ROLL_CD and LIM_PITCH_* define control limits."
        )
    else:
        fallback = (
            "I'm the ArduPilot assistant. Ask about Manual, FBWA, AUTO, or Autotune parameters. "
            "Set OPENAI_API_KEY (and be online) or run Ollama locally for full AI answers."
        )
    return {"response": fallback, "source": "fallback", "error": None}


def get_report_summary_ai(
    reports: Dict[str, Any],
    plane_type_name: Optional[str] = None,
    prefer_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ask the AI for a short summary of the parameter reports (for Compare & Generate Reports).
    reports: dict of mode -> { summary: { total, ok, warning, change }, rows: [...] }
    Returns same shape as get_ai_response: { "response": str, "source": str, "error": str | None }.
    """
    lines = []
    for mode, data in reports.items():
        s = (data or {}).get("summary", {})
        total = s.get("total", 0)
        ok = s.get("ok", 0)
        warning = s.get("warning", 0)
        change = s.get("change", 0)
        lines.append(f"{mode}: {total} params — OK: {ok}, Warning: {warning}, Change: {change}")
        rows = (data or {}).get("rows", [])[:15]
        for r in rows:
            if r.get("severity") and r.get("severity") != "OK":
                lines.append(f"  - {r.get('parameter', '')}: current {r.get('current_value')} → {r.get('recommended')} ({r.get('severity')})")
    context = "\n".join(lines)
    user_question = (
        "Summarize this parameter comparison report in 2-4 short sentences. "
        "Highlight the most important changes or warnings the pilot should address first. Be concise.\n\n"
        f"Report:\n{context[:2500]}"
    )
    return get_ai_response(
        user_question,
        plane_type_name=plane_type_name,
        param_db=[],
        prefer_provider=prefer_provider,
    )


def get_flight_log_ai_analysis(
    log_data: Dict[str, Any],
    prefer_provider: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ask the AI to interpret the parsed flight log for the pilot.
    log_data: from parse_flight_log (summary, message_counts, mode_changes, events).
    Returns { "response": str, "source": str, "error": str | None }.
    """
    if not log_data.get("ok"):
        return {"response": f"Log could not be parsed: {log_data.get('error', 'Unknown')}.", "source": "fallback", "error": log_data.get("error")}
    lines = ["=== Flight log parsing result ==="]
    s = log_data.get("summary", {})
    lines.append(f"Total messages: {s.get('total_messages', 0)}")
    lines.append(f"Message types: {s.get('message_types', 0)}")
    lines.append(f"Duration: {s.get('duration_seconds')} seconds" if s.get("duration_seconds") is not None else "Duration: unknown")
    lines.append(f"Mode changes: {s.get('mode_changes', 0)} | Events: {s.get('events', 0)}")
    counts = log_data.get("message_counts", {})
    if counts:
        lines.append("\nMessage breakdown (top 15):")
        for mtype, count in list(counts.items())[:15]:
            lines.append(f"  {mtype}: {count}")
    mode_changes = log_data.get("mode_changes", [])[:20]
    if mode_changes:
        lines.append("\nMode changes:")
        for mc in mode_changes:
            name = mc.get("mode_name", mc.get("mode", "?"))
            ts = mc.get("time_s") or mc.get("time_boot_ms")
            lines.append(f"  t={ts} → {name}")
    events = log_data.get("events", [])[:25]
    if events:
        lines.append("\nRecent events/status:")
        for ev in events:
            lines.append(f"  [{ev.get('type')}] {ev.get('text', '')[:80]}")
    context = "\n".join(lines)
    user_question = (
        "Interpret this ArduPilot flight log parsing result for the pilot in 3–6 short sentences. "
        "Explain what the log contains (message types, duration, mode changes, events), whether it looks normal, "
        "and any suggestions (e.g. what to check, or that more data would help). Be clear and concise.\n\n"
        f"{context[:3000]}"
    )
    return get_ai_response(
        user_question,
        param_db=[],
        prefer_provider=prefer_provider,
    )
