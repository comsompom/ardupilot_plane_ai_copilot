"""
Standalone desktop application for ArduPilot AI Assistant.
NATO military defence style UI; uses the same core as the Flask web app (Tkinter).
"""
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Import core (shared with Flask web app)
from core.plane_types import PLANE_TYPES, get_plane_type_name
from core.params import load_param_db, load_user_params_from_file, fetch_user_params_mavlink
from core.reports import generate_report, export_report_html, export_report_pdf, export_report_txt
from core.ai_assistant import get_ai_response, get_report_summary_ai, get_flight_log_ai_analysis
from core.mission_parser import parse_mission_file, analyze_mission
from core.log_parser import parse_flight_log, analyze_flight_log

MODES = ["Manual", "FBWA", "AUTO", "Autotune"]

# NATO / military defence colour palette
NATO = {
    "bg_dark": "#1a1f1a",        # main window / darkest
    "bg_panel": "#252b24",       # panels, frames
    "bg_surface": "#2d352e",     # entries, listboxes
    "border": "#3d4a3a",         # borders
    "border_strong": "#4a5c45",  # emphasis borders
    "text": "#c5d0c4",           # primary text
    "text_dim": "#7d8b7a",       # secondary / hints
    "accent": "#b8860b",         # amber / NATO accent
    "accent_hover": "#d4a84b",   # amber highlight
    "go": "#5a7a5a",             # success / go
    "warn": "#a68b4a",           # warning
}


class ArduPilotStandaloneApp:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("ARDUPILOT AI ASSISTANT — PRE-FLIGHT PARAMETER AUDIT")
        self.win.minsize(800, 600)
        self.win.geometry("960x720")
        self.win.configure(bg=NATO["bg_dark"])

        self.current_params: Dict[str, float] = {}
        self.current_reports: Dict[str, Dict[str, Any]] = {}
        self.param_file_path: Optional[Path] = None
        self.ai_summary_text: Optional[str] = None

        self._setup_military_theme()
        self._build_ui()

    def _setup_military_theme(self):
        """Apply NATO / military defence style to ttk and root."""
        self.win.option_add("*Font", "Arial 9")
        self.win.option_add("*Background", NATO["bg_panel"])
        self.win.option_add("*Foreground", NATO["text"])
        self.win.option_add("*selectBackground", NATO["accent"])
        self.win.option_add("*selectForeground", NATO["bg_dark"])
        self.win.option_add("*insertBackground", NATO["text"])

        style = ttk.Style(self.win)
        style.theme_use("clam")

        # Frames
        style.configure("TFrame", background=NATO["bg_panel"])
        style.configure("TNotebook", background=NATO["bg_dark"])
        style.configure("TNotebook.Tab", background=NATO["bg_panel"], foreground=NATO["text"], padding=(14, 8), font="Arial 9 bold")
        style.map("TNotebook.Tab", background=[("selected", NATO["bg_surface"])], foreground=[("selected", NATO["accent"])])
        style.configure("TLabelframe", background=NATO["bg_panel"], foreground=NATO["accent"], borderwidth=1)
        style.configure("TLabelframe.Label", background=NATO["bg_panel"], foreground=NATO["accent"], font="Arial 9 bold")

        # Labels
        style.configure("TLabel", background=NATO["bg_panel"], foreground=NATO["text"], font="Arial 9")
        style.configure("Header.TLabel", background=NATO["bg_panel"], foreground=NATO["accent"], font="Arial 10 bold")

        # Buttons
        style.configure("TButton", background=NATO["bg_surface"], foreground=NATO["text"], borderwidth=1, padding=(10, 6), font="Arial 9")
        style.map("TButton", background=[("active", NATO["border"]), ("pressed", NATO["border_strong"])], foreground=[("active", NATO["accent"])])
        style.configure("Primary.TButton", background=NATO["accent"], foreground=NATO["bg_dark"], font="Arial 9 bold")
        style.map("Primary.TButton", background=[("active", NATO["accent_hover"]), ("pressed", NATO["warn"])])

        # Entry / Combobox
        style.configure("TEntry", fieldbackground=NATO["bg_surface"], foreground=NATO["text"], insertcolor=NATO["text"], borderwidth=1)
        style.configure("TCombobox", fieldbackground=NATO["bg_surface"], foreground=NATO["text"], background=NATO["bg_panel"], arrowcolor=NATO["accent"])
        style.map("TCombobox", fieldbackground=[("readonly", NATO["bg_surface"])], foreground=[("readonly", NATO["text"])])

        # Radiobutton
        style.configure("TRadiobutton", background=NATO["bg_panel"], foreground=NATO["text"])
        style.map("TRadiobutton", foreground=[("active", NATO["accent"])])

        # Treeview
        style.configure("Treeview", background=NATO["bg_surface"], foreground=NATO["text"], fieldbackground=NATO["bg_surface"], borderwidth=0, rowheight=22, font="Consolas 9")
        style.configure("Treeview.Heading", background=NATO["border"], foreground=NATO["accent"], font="Arial 9 bold", borderwidth=0)
        style.map("Treeview", background=[("selected", NATO["accent"])], foreground=[("selected", NATO["bg_dark"])])
        style.map("Treeview.Heading", background=[("active", NATO["border_strong"])])

        # Scrollbar
        style.configure("Vertical.TScrollbar", background=NATO["border"], troughcolor=NATO["bg_dark"], borderwidth=0, arrowsize=0)
        style.map("Vertical.TScrollbar", background=[("active", NATO["accent"])])

        # Optional: dim and warning labels (for status/hint)
        style.configure("Dim.TLabel", background=NATO["bg_panel"], foreground=NATO["text_dim"], font="Arial 8")
        style.configure("Warn.TLabel", background=NATO["bg_panel"], foreground=NATO["accent_hover"])

    def _build_ui(self):
        # Header bar (use Arial - no space in name, avoids Tk font parsing bug on Windows)
        header = tk.Frame(self.win, bg=NATO["bg_dark"], height=52, highlightthickness=0)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text="ARDUPILOT AI ASSISTANT", bg=NATO["bg_dark"], fg=NATO["accent"], font="Arial 14 bold").pack(side=tk.LEFT, padx=(16, 8), pady=10)
        tk.Label(header, text="PRE-FLIGHT PARAMETER AUDIT  |  NATO STYLE", bg=NATO["bg_dark"], fg=NATO["text_dim"], font="Arial 9").pack(side=tk.LEFT, pady=10)
        sep = tk.Frame(self.win, bg=NATO["border_strong"], height=2)
        sep.pack(fill=tk.X)

        nb = ttk.Notebook(self.win)
        nb.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Tab 1: Config & Compare
        config_frame = ttk.Frame(nb, padding=12)
        nb.add(config_frame, text="  CONFIG & COMPARE  ")
        self._build_config_tab(config_frame)

        # Tab 2: Reports
        reports_frame = ttk.Frame(nb, padding=12)
        nb.add(reports_frame, text="  REPORTS  ")
        self._build_reports_tab(reports_frame)

        # Tab 3: Mission
        mission_frame = ttk.Frame(nb, padding=12)
        nb.add(mission_frame, text="  MISSION  ")
        self._build_mission_tab(mission_frame)

        # Tab 4: Flight log
        log_frame = ttk.Frame(nb, padding=12)
        nb.add(log_frame, text="  FLIGHT LOG  ")
        self._build_log_tab(log_frame)

        # Tab 5: AI Assistant
        assistant_frame = ttk.Frame(nb, padding=12)
        nb.add(assistant_frame, text="  AI ASSISTANT  ")
        self._build_assistant_tab(assistant_frame)

    def _build_config_tab(self, parent: ttk.Frame):
        cap = ttk.Label(parent, text="PLATFORM CONFIGURATION", style="Header.TLabel")
        cap.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        row = 1
        ttk.Label(parent, text="Plane type").grid(row=row, column=0, sticky=tk.W, pady=3)
        self.plane_type_var = tk.StringVar(value=PLANE_TYPES[0]["id"])
        plane_combo = ttk.Combobox(parent, textvariable=self.plane_type_var, width=48, state="readonly")
        plane_combo["values"] = [f"{t['id']}: {t['name']} — {t['description']}" for t in PLANE_TYPES]
        plane_combo.current(0)
        plane_combo.grid(row=row, column=1, sticky=tk.W, pady=3, padx=(12, 0))
        row += 1

        ttk.Label(parent, text="Wingspan (m)").grid(row=row, column=0, sticky=tk.W, pady=3)
        self.wingspan_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.wingspan_var, width=18).grid(row=row, column=1, sticky=tk.W, pady=3, padx=(12, 0))
        row += 1

        ttk.Label(parent, text="Weight (kg)").grid(row=row, column=0, sticky=tk.W, pady=3)
        self.weight_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.weight_var, width=18).grid(row=row, column=1, sticky=tk.W, pady=3, padx=(12, 0))
        row += 1

        ttk.Label(parent, text="Parameters").grid(row=row, column=0, sticky=tk.W, pady=3)
        param_f = ttk.Frame(parent)
        param_f.grid(row=row, column=1, sticky=tk.W, pady=3, padx=(12, 0))
        ttk.Button(param_f, text="Load from file…", command=self._on_load_param_file).pack(side=tk.LEFT, padx=(0, 8))
        self.param_file_label = ttk.Label(param_f, text="No file loaded")
        self.param_file_label.pack(side=tk.LEFT)
        row += 1

        ttk.Label(parent, text="MAVLink connection").grid(row=row, column=0, sticky=tk.W, pady=3)
        mav_f = ttk.Frame(parent)
        mav_f.grid(row=row, column=1, sticky=tk.W, pady=3, padx=(12, 0))
        self.mavlink_var = tk.StringVar(value="udp:127.0.0.1:14550")
        ttk.Entry(mav_f, textvariable=self.mavlink_var, width=30).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(mav_f, text="Fetch via MAVLink", command=self._on_fetch_mavlink).pack(side=tk.LEFT)
        row += 1

        ttk.Label(parent, text="AI agent for reports").grid(row=row, column=0, sticky=tk.W, pady=3)
        agent_f = ttk.Frame(parent)
        agent_f.grid(row=row, column=1, sticky=tk.W, pady=3, padx=(12, 0))
        self.agent_var = tk.StringVar(value="none")
        ttk.Radiobutton(agent_f, text="Online (OpenAI)", variable=self.agent_var, value="openai").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(agent_f, text="Local (Ollama)", variable=self.agent_var, value="ollama").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(agent_f, text="No AI summary", variable=self.agent_var, value="none").pack(side=tk.LEFT)
        row += 1

        ttk.Button(parent, text="COMPARE & GENERATE REPORTS", style="Primary.TButton", command=self._on_compare).grid(row=row, column=1, sticky=tk.W, pady=12, padx=(12, 0))
        row += 1

        help_f = ttk.Frame(parent)
        help_f.grid(row=row, column=1, sticky=tk.W, padx=(12, 0))
        self.btn_ai_analysis = ttk.Button(help_f, text="Get AI analysis of file", command=self._on_ai_analysis_file, state=tk.DISABLED)
        self.btn_ai_analysis.pack(side=tk.LEFT, padx=(0, 8))
        row += 1

        self.config_status_var = tk.StringVar(value="Load a .param file or fetch via MAVLink, then click Compare to generate reports.")
        status_lbl = ttk.Label(parent, textvariable=self.config_status_var, style="Dim.TLabel", wraplength=540)
        status_lbl.grid(row=row, column=1, sticky=tk.W, padx=(12, 0))
        row += 1
        self.config_hint_var = tk.StringVar(value="What to expect: Load parameters → Compare → open Reports tab for results.")
        hint_lbl = ttk.Label(parent, textvariable=self.config_hint_var, style="Dim.TLabel", wraplength=540)
        hint_lbl.grid(row=row, column=1, sticky=tk.W, padx=(12, 0))

    def _update_config_hint(self):
        """Update the 'What to expect' hint based on current state."""
        if hasattr(self, "config_hint_var"):
            if self.current_params:
                self.config_hint_var.set("What to expect: Click Compare → open Reports tab. You can also ask the AI Assistant for help.")
            else:
                self.config_hint_var.set("What to expect: Load parameters (file or MAVLink) → Compare → Reports tab. If file has 0 params, use 'Get AI analysis of file'.")

    def _on_load_param_file(self):
        path = filedialog.askopenfilename(
            title="Select parameter file",
            filetypes=[("Param files", "*.param *.parm *.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        self.param_file_path = Path(path)
        self.current_params = load_user_params_from_file(self.param_file_path)
        n = len(self.current_params)
        self.param_file_label.config(text=f"{self.param_file_path.name} ({n} params)", style="Warn.TLabel" if n == 0 else "TLabel")
        if n == 0:
            self.config_status_var.set(
                "File loaded but no parameters were found. The file may use a different format. "
                "Use 'Get AI analysis of file' for suggestions, or try another file / MAVLink."
            )
            self.btn_ai_analysis.config(state=tk.NORMAL)
        else:
            self.config_status_var.set(f"Loaded {n} parameters from file. Next: click Compare to generate reports.")
            self.btn_ai_analysis.config(state=tk.DISABLED)
        self._update_config_hint()

    def _on_fetch_mavlink(self):
        conn = self.mavlink_var.get().strip()
        if not conn:
            self.config_status_var.set("Enter MAVLink connection (e.g. udp:127.0.0.1:14550)")
            return
        self.config_status_var.set("Fetching parameters via MAVLink…")
        self.win.update_idletasks()

        def do_fetch():
            try:
                params = fetch_user_params_mavlink(conn)
                self.win.after(0, lambda: self._apply_fetched_params(params, conn))
            except Exception as e:
                self.win.after(0, lambda: self._apply_fetched_params({}, conn, str(e)))

        threading.Thread(target=do_fetch, daemon=True).start()

    def _on_ai_analysis_file(self):
        """Run AI analysis on the loaded file when it has 0 params; show suggestions in a window."""
        if not self.param_file_path or not self.param_file_path.exists():
            self.config_status_var.set("Load a parameter file first (one that shows 0 params).")
            return
        self.config_status_var.set("Asking AI for analysis of your file…")
        self.win.update_idletasks()
        path = self.param_file_path
        agent = self.agent_var.get() if self.agent_var.get() in ("openai", "ollama") else None

        def do_analysis():
            try:
                raw = path.read_text(encoding="utf-8", errors="replace")
                snippet = raw[:2500].strip() or "(file empty or unreadable)"
            except Exception as e:
                self.win.after(0, lambda: self.config_status_var.set(f"Could not read file: {e}"))
                return
            question = (
                "The user loaded this file as an ArduPilot Plane parameter file, but the parser found 0 parameters. "
                "Here is the start of the file:\n\n---\n" + snippet + "\n---\n\n"
                "What might be wrong? What format does ArduPilot expect for .param files (e.g. PARAM_NAME, value)? "
                "Give 2–4 short, actionable suggestions so the user can fix the file or get a valid parameter dump."
            )
            result = get_ai_response(question, param_db=[], prefer_provider=agent)
            response = result.get("response") or result.get("error") or "No response."
            source = result.get("source", "")
            self.win.after(0, lambda: self._show_ai_analysis_result(response, source, path.name))
            self.win.after(0, lambda: self.config_status_var.set("AI analysis done. See the suggestions window."))

        threading.Thread(target=do_analysis, daemon=True).start()

    def _show_ai_analysis_result(self, text: str, source: str, filename: str):
        """Show AI analysis result in a separate window (NATO style)."""
        win = tk.Toplevel(self.win)
        win.title(f"AI ANALYSIS — {filename}")
        win.minsize(420, 320)
        win.geometry("580x420")
        win.configure(bg=NATO["bg_dark"])
        header = tk.Frame(win, bg=NATO["bg_dark"], height=44)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        tk.Label(header, text=f"SUGGESTIONS FOR PARAMETER FILE  |  {source.upper()}", bg=NATO["bg_dark"], fg=NATO["accent"], font="Arial 10 bold").pack(anchor=tk.W, padx=12, pady=10)
        txt = scrolledtext.ScrolledText(win, wrap=tk.WORD, width=72, height=18, bg=NATO["bg_surface"], fg=NATO["text"], insertbackground=NATO["text"], font="Consolas 9", borderwidth=0)
        txt.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))
        txt.insert(tk.END, text)
        txt.config(state=tk.DISABLED)
        btn_frame = tk.Frame(win, bg=NATO["bg_dark"])
        btn_frame.pack(fill=tk.X, pady=(0, 12))
        ttk.Button(btn_frame, text="CLOSE", style="Primary.TButton", command=win.destroy).pack()

    def _apply_fetched_params(self, params: Dict[str, float], conn: str, error: Optional[str] = None):
        if error:
            self.config_status_var.set(f"Fetch failed: {error}")
            self._update_config_hint()
            return
        self.current_params = params
        self.param_file_label.config(text=f"MAVLink ({len(params)} params)", style="TLabel")
        self.config_status_var.set(f"Fetched {len(params)} parameters. Next: click Compare to generate reports.")
        self.btn_ai_analysis.config(state=tk.DISABLED)
        self._update_config_hint()

    def _on_compare(self):
        if not self.current_params:
            self.config_status_var.set(
                "No parameters to compare. Load a valid .param file (PARAM_NAME and value per line) or fetch via MAVLink. "
                "If your file was loaded but shows 0 params, use 'Get AI analysis of file' for suggestions."
            )
            self._update_config_hint()
            return
        plane_id = self.plane_type_var.get().split(":")[0] if ":" in self.plane_type_var.get() else self.plane_type_var.get()
        try:
            wingspan = float(self.wingspan_var.get()) if self.wingspan_var.get().strip() else None
        except ValueError:
            wingspan = None
        try:
            weight = float(self.weight_var.get()) if self.weight_var.get().strip() else None
        except ValueError:
            weight = None
        agent = self.agent_var.get() if self.agent_var.get() in ("openai", "ollama") else None
        use_ai = agent is not None

        def do_compare():
            def status(msg: str):
                self.win.after(0, lambda: self.config_status_var.set(msg))

            status("Loading parameter database…")
            param_db = load_param_db()
            self.current_reports = {}
            for i, mode in enumerate(MODES):
                status(f"Comparing {mode}…")
                self.win.after(0, self.win.update_idletasks)
                self.current_reports[mode] = generate_report(
                    self.current_params, param_db=param_db, mode=mode,
                    plane_type_id=plane_id, wingspan_m=wingspan, weight_kg=weight,
                )
            self.win.after(0, self._refresh_report_tables)
            self.ai_summary_text = None
            if use_ai and agent:
                status("Generating AI summary…")
                self.win.after(0, self.win.update_idletasks)
                plane_name = get_plane_type_name(plane_id) if plane_id else None
                result = get_report_summary_ai(
                    self.current_reports, plane_type_name=plane_name, prefer_provider=agent
                )
                self.ai_summary_text = result.get("response") or result.get("error") or ""
                self.win.after(0, self._refresh_ai_summary_label)
            status("Done. Reports generated." + (" AI summary added." if self.ai_summary_text else " Open the Reports tab."))

        self.config_status_var.set("Comparing parameters and generating reports…")
        self.win.update_idletasks()
        threading.Thread(target=do_compare, daemon=True).start()

    def _build_reports_tab(self, parent: ttk.Frame):
        ttk.Label(parent, text="PARAMETER REPORTS", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))
        self.ai_summary_var = tk.StringVar(value="")
        ai_frame = ttk.LabelFrame(parent, text=" AI SUMMARY (WHEN GENERATED) ")
        ai_frame.pack(fill=tk.X, pady=(0, 10))
        self.ai_summary_label = ttk.Label(ai_frame, textvariable=self.ai_summary_var, wraplength=720)
        self.ai_summary_label.pack(anchor=tk.W, padx=8, pady=6)
        self.report_notebook = ttk.Notebook(parent)
        self.report_notebook.pack(fill=tk.BOTH, expand=True)
        self.report_treeviews: Dict[str, ttk.Treeview] = {}
        self.report_summary_vars: Dict[str, tk.StringVar] = {}
        for mode in MODES:
            frame = ttk.Frame(self.report_notebook, padding=5)
            self.report_notebook.add(frame, text=f"  {mode}  ")
            # Export buttons
            btn_f = ttk.Frame(frame)
            btn_f.pack(fill=tk.X)
            ttk.Button(btn_f, text="Export HTML", command=lambda m=mode: self._export_report(m, "html")).pack(side=tk.LEFT, padx=(0, 6))
            ttk.Button(btn_f, text="Export PDF", command=lambda m=mode: self._export_report(m, "pdf")).pack(side=tk.LEFT, padx=(0, 6))
            ttk.Button(btn_f, text="Export TXT", command=lambda m=mode: self._export_report(m, "txt")).pack(side=tk.LEFT)
            # Treeview
            tree = ttk.Treeview(frame, columns=("param", "current", "recommended", "severity", "action"), show="headings", height=12)
            tree.heading("param", text="Parameter")
            tree.heading("current", text="Current")
            tree.heading("recommended", text="Recommended")
            tree.heading("severity", text="Severity")
            tree.heading("action", text="Action")
            tree.column("param", width=160)
            tree.column("current", width=70)
            tree.column("recommended", width=100)
            tree.column("severity", width=70)
            tree.column("action", width=200)
            scroll = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscrollcommand=scroll.set)
            tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            self.report_treeviews[mode] = tree
            sv = tk.StringVar(value="Run Compare in Config tab to load report.")
            ttk.Label(frame, textvariable=sv).pack(anchor=tk.W)
            self.report_summary_vars[mode] = sv

    def _refresh_ai_summary_label(self):
        if self.ai_summary_text:
            self.ai_summary_var.set(self.ai_summary_text)
        else:
            self.ai_summary_var.set("Run Compare with Online or Local AI selected to see a summary here.")

    def _refresh_report_tables(self):
        self._refresh_ai_summary_label()
        for mode in MODES:
            tree = self.report_treeviews[mode]
            for item in tree.get_children():
                tree.delete(item)
            report = self.current_reports.get(mode, {})
            for row in report.get("rows", []):
                cur = row.get("current_value")
                cur_str = str(cur) if cur is not None else "—"
                tree.insert("", tk.END, values=(
                    row.get("parameter", ""), cur_str, str(row.get("recommended", "")), row.get("severity", ""), (row.get("action", "") or "")[:50]
                ))
            s = report.get("summary", {})
            self.report_summary_vars[mode].set(
                f"Total: {s.get('total', 0)} | OK: {s.get('ok', 0)} | Warning: {s.get('warning', 0)} | Change: {s.get('change', 0)}"
            )

    def _export_report(self, mode: str, fmt: str):
        report = self.current_reports.get(mode)
        if not report or not report.get("rows"):
            messagebox.showinfo("Export", "No report for " + mode + ". Run Compare first.")
            return
        path = filedialog.asksaveasfilename(
            title=f"Save report as {fmt.upper()}",
            defaultextension=f".{fmt}",
            filetypes=[(f"{fmt.upper()} files", f"*.{fmt}"), ("All files", "*.*")],
            initialfilename=f"ardupilot_report_{mode}.{fmt}",
        )
        if not path:
            return
        path = Path(path)
        if fmt == "html":
            export_report_html(report, path)
        elif fmt == "txt":
            export_report_txt(report, path)
        elif fmt == "pdf":
            export_report_pdf(report, path)
        messagebox.showinfo("Export", f"Saved to {path}")

    def _build_mission_tab(self, parent: ttk.Frame):
        ttk.Label(parent, text="MISSION BRIEFING", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))
        f = ttk.Frame(parent)
        f.pack(fill=tk.X)
        ttk.Button(f, text="Select mission file…", command=self._on_select_mission).pack(side=tk.LEFT, padx=(0, 8))
        self.mission_path_var = tk.StringVar(value="No file selected")
        ttk.Label(f, textvariable=self.mission_path_var).pack(side=tk.LEFT)
        ttk.Button(parent, text="Analyze mission", style="Primary.TButton", command=self._on_analyze_mission).pack(anchor=tk.W, pady=(0, 8))
        self.mission_result = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=14, width=88, bg=NATO["bg_surface"], fg=NATO["text"], insertbackground=NATO["text"], font="Consolas 9", borderwidth=2, relief=tk.GROOVE)
        self.mission_result.pack(fill=tk.BOTH, expand=True)
        self.mission_file_path: Optional[Path] = None

    def _on_select_mission(self):
        path = filedialog.askopenfilename(
            title="Select mission file",
            filetypes=[("Mission / waypoints", "*.waypoints *.plan *.txt"), ("All files", "*.*")],
        )
        if path:
            self.mission_file_path = Path(path)
            self.mission_path_var.set(self.mission_file_path.name)

    def _on_analyze_mission(self):
        if not self.mission_file_path or not self.mission_file_path.exists():
            messagebox.showinfo("Mission", "Select a mission file first.")
            return
        plane_id = self.plane_type_var.get().split(":")[0] if ":" in self.plane_type_var.get() else self.plane_type_var.get()
        data = parse_mission_file(self.mission_file_path)
        analysis = analyze_mission(data, plane_type_id=plane_id)
        self.mission_result.delete("1.0", tk.END)
        self.mission_result.insert(tk.END, analysis.get("summary", "") + "\n\n")
        for s in analysis.get("suggestions", []):
            self.mission_result.insert(tk.END, "• " + s + "\n")

    def _build_log_tab(self, parent: ttk.Frame):
        ttk.Label(parent, text="FLIGHT LOG ANALYSIS", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))
        f = ttk.Frame(parent)
        f.pack(fill=tk.X)
        ttk.Button(f, text="Select log file…", command=self._on_select_log).pack(side=tk.LEFT, padx=(0, 8))
        self.log_path_var = tk.StringVar(value="No file selected")
        ttk.Label(f, textvariable=self.log_path_var).pack(side=tk.LEFT)
        ttk.Button(parent, text="Analyze log", style="Primary.TButton", command=self._on_analyze_log).pack(anchor=tk.W, pady=(0, 8))
        self.log_result = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=14, width=88, bg=NATO["bg_surface"], fg=NATO["text"], insertbackground=NATO["text"], font="Consolas 9", borderwidth=2, relief=tk.GROOVE)
        self.log_result.pack(fill=tk.BOTH, expand=True)
        self.log_file_path: Optional[Path] = None

    def _on_select_log(self):
        path = filedialog.askopenfilename(
            title="Select flight log",
            filetypes=[("Log files", "*.bin *.log"), ("All files", "*.*")],
        )
        if path:
            self.log_file_path = Path(path)
            self.log_path_var.set(self.log_file_path.name)

    def _on_analyze_log(self):
        if not self.log_file_path or not self.log_file_path.exists():
            messagebox.showinfo("Log", "Select a log file first.")
            return
        self.log_result.delete("1.0", tk.END)
        self.log_result.insert(tk.END, "Parsing log file…\n")
        self.win.update_idletasks()
        agent = self.agent_var.get() if self.agent_var.get() in ("openai", "ollama") else None

        def do_log_analysis():
            data = parse_flight_log(self.log_file_path)
            self.win.after(0, lambda: self._display_log_parsed(data))
            analysis = analyze_flight_log(data)
            self.win.after(0, lambda: self._append_log_suggestions(analysis))
            self.win.after(0, lambda: self.log_result.insert(tk.END, "\nAsking AI for interpretation…\n"))
            self.win.after(0, self.win.update_idletasks)
            ai_result = get_flight_log_ai_analysis(data, prefer_provider=agent)
            self.win.after(0, lambda: self._append_log_ai(ai_result))

        threading.Thread(target=do_log_analysis, daemon=True).start()

    def _display_log_parsed(self, data: Dict[str, Any]):
        """Write parsing result (message counts, duration, mode changes, events) into log_result."""
        self.log_result.delete("1.0", tk.END)
        if not data.get("ok"):
            self.log_result.insert(tk.END, f"Parse failed: {data.get('error', 'Unknown')}\n")
            return
        s = data.get("summary", {})
        total = s.get("total_messages", 0)
        duration = s.get("duration_seconds")
        self.log_result.insert(tk.END, "——— PARSING RESULT ———\n\n")
        self.log_result.insert(tk.END, f"Total messages: {total}\n")
        self.log_result.insert(tk.END, f"Message types: {s.get('message_types', 0)}\n")
        if duration is not None:
            self.log_result.insert(tk.END, f"Duration: {duration:.1f} s\n")
        self.log_result.insert(tk.END, f"Mode changes: {s.get('mode_changes', 0)}  |  Events: {s.get('events', 0)}\n\n")
        counts = data.get("message_counts", {})
        if counts:
            self.log_result.insert(tk.END, "Message breakdown:\n")
            for mtype, count in list(counts.items())[:20]:
                self.log_result.insert(tk.END, f"  {mtype}: {count}\n")
            self.log_result.insert(tk.END, "\n")
        mode_changes = data.get("mode_changes", [])[:15]
        if mode_changes:
            self.log_result.insert(tk.END, "Mode changes:\n")
            for mc in mode_changes:
                name = mc.get("mode_name", mc.get("mode", "?"))
                ts = mc.get("time_s") or mc.get("time_boot_ms")
                self.log_result.insert(tk.END, f"  t={ts} → {name}\n")
            self.log_result.insert(tk.END, "\n")
        events = data.get("events", [])[:20]
        if events:
            self.log_result.insert(tk.END, "Events / status messages:\n")
            for ev in events:
                self.log_result.insert(tk.END, f"  [{ev.get('type')}] {ev.get('text', '')[:70]}\n")
            self.log_result.insert(tk.END, "\n")

    def _append_log_suggestions(self, analysis: Dict[str, Any]):
        self.log_result.insert(tk.END, "——— SUGGESTIONS ———\n")
        for s in analysis.get("suggestions", []):
            self.log_result.insert(tk.END, "• " + s + "\n")
        self.log_result.insert(tk.END, "\n")

    def _append_log_ai(self, ai_result: Dict[str, Any]):
        self.log_result.insert(tk.END, "——— AI INTERPRETATION ———\n\n")
        text = ai_result.get("response") or ai_result.get("error") or "No AI response."
        self.log_result.insert(tk.END, text + "\n")
        if ai_result.get("source"):
            self.log_result.insert(tk.END, f"\n(Source: {ai_result.get('source')})\n")

    def _build_assistant_tab(self, parent: ttk.Frame):
        ttk.Label(parent, text="AI TACTICAL ASSISTANT", style="Header.TLabel").pack(anchor=tk.W, pady=(0, 8))
        self.chat_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=14, width=88, bg=NATO["bg_surface"], fg=NATO["text"], insertbackground=NATO["text"], font="Consolas 9", borderwidth=2, relief=tk.GROOVE)
        self.chat_text.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        f = ttk.Frame(parent)
        f.pack(fill=tk.X)
        self.assistant_entry = ttk.Entry(f, width=62)
        self.assistant_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(f, text="SEND", style="Primary.TButton", command=self._on_ask_assistant).pack(side=tk.LEFT)
        self.assistant_entry.bind("<Return>", lambda e: self._on_ask_assistant())

    def _on_ask_assistant(self):
        question = self.assistant_entry.get().strip()
        if not question:
            return
        self._append_chat("You", question)
        self.assistant_entry.delete(0, tk.END)
        self.win.update_idletasks()

        def do_ask():
            plane_id = self.plane_type_var.get().split(":")[0] if ":" in self.plane_type_var.get() else None
            agent = self.agent_var.get() if self.agent_var.get() in ("openai", "ollama") else None
            param_db = load_param_db()
            result = get_ai_response(
                question,
                plane_type_id=plane_id,
                user_params=self.current_params,
                report_summary={m: r.get("summary") for m, r in self.current_reports.items()} if self.current_reports else {},
                param_db=param_db,
                prefer_provider=agent,
            )
            text = result.get("response") or result.get("error") or "No response."
            source = result.get("source", "")
            self.win.after(0, lambda: self._append_chat("Assistant" + (f" ({source})" if source else ""), text))

        threading.Thread(target=do_ask, daemon=True).start()

    def _append_chat(self, who: str, text: str):
        self.chat_text.insert(tk.END, f"{who}: {text}\n\n")
        self.chat_text.see(tk.END)

    def run(self):
        self.win.mainloop()


def main():
    app = ArduPilotStandaloneApp()
    app.run()


if __name__ == "__main__":
    main()
