"""
Standalone desktop application for ArduPilot AI Assistant.
Uses the same core as the Flask web app; runs as a native PC application (Tkinter).
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
from core.ai_assistant import get_ai_response, get_report_summary_ai
from core.mission_parser import parse_mission_file, analyze_mission
from core.log_parser import parse_flight_log, analyze_flight_log

MODES = ["Manual", "FBWA", "AUTO", "Autotune"]


class ArduPilotStandaloneApp:
    def __init__(self):
        self.win = tk.Tk()
        self.win.title("ArduPilot AI Assistant")
        self.win.minsize(800, 600)
        self.win.geometry("950x700")

        self.current_params: Dict[str, float] = {}
        self.current_reports: Dict[str, Dict[str, Any]] = {}
        self.param_file_path: Optional[Path] = None
        self.ai_summary_text: Optional[str] = None

        self._build_ui()

    def _build_ui(self):
        nb = ttk.Notebook(self.win)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)

        # Tab 1: Config & Compare
        config_frame = ttk.Frame(nb, padding=10)
        nb.add(config_frame, text="Config & Compare")
        self._build_config_tab(config_frame)

        # Tab 2: Reports
        reports_frame = ttk.Frame(nb, padding=10)
        nb.add(reports_frame, text="Reports")
        self._build_reports_tab(reports_frame)

        # Tab 3: Mission
        mission_frame = ttk.Frame(nb, padding=10)
        nb.add(mission_frame, text="Mission")
        self._build_mission_tab(mission_frame)

        # Tab 4: Flight log
        log_frame = ttk.Frame(nb, padding=10)
        nb.add(log_frame, text="Flight log")
        self._build_log_tab(log_frame)

        # Tab 5: AI Assistant
        assistant_frame = ttk.Frame(nb, padding=10)
        nb.add(assistant_frame, text="AI Assistant")
        self._build_assistant_tab(assistant_frame)

    def _build_config_tab(self, parent: ttk.Frame):
        row = 0
        ttk.Label(parent, text="Plane type").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.plane_type_var = tk.StringVar(value=PLANE_TYPES[0]["id"])
        plane_combo = ttk.Combobox(parent, textvariable=self.plane_type_var, width=45, state="readonly")
        plane_combo["values"] = [f"{t['id']}: {t['name']} — {t['description']}" for t in PLANE_TYPES]
        plane_combo.current(0)
        plane_combo.grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(parent, text="Wingspan (m)").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.wingspan_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.wingspan_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(parent, text="Weight (kg)").grid(row=row, column=0, sticky=tk.W, pady=2)
        self.weight_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.weight_var, width=15).grid(row=row, column=1, sticky=tk.W, pady=2)
        row += 1

        ttk.Label(parent, text="Parameters").grid(row=row, column=0, sticky=tk.W, pady=2)
        param_f = ttk.Frame(parent)
        param_f.grid(row=row, column=1, sticky=tk.W, pady=2)
        ttk.Button(param_f, text="Load from file…", command=self._on_load_param_file).pack(side=tk.LEFT, padx=(0, 8))
        self.param_file_label = ttk.Label(param_f, text="No file loaded", foreground="gray")
        self.param_file_label.pack(side=tk.LEFT)
        row += 1

        ttk.Label(parent, text="MAVLink connection").grid(row=row, column=0, sticky=tk.W, pady=2)
        mav_f = ttk.Frame(parent)
        mav_f.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.mavlink_var = tk.StringVar(value="udp:127.0.0.1:14550")
        ttk.Entry(mav_f, textvariable=self.mavlink_var, width=28).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(mav_f, text="Fetch via MAVLink", command=self._on_fetch_mavlink).pack(side=tk.LEFT)
        row += 1

        ttk.Label(parent, text="AI agent for reports").grid(row=row, column=0, sticky=tk.W, pady=2)
        agent_f = ttk.Frame(parent)
        agent_f.grid(row=row, column=1, sticky=tk.W, pady=2)
        self.agent_var = tk.StringVar(value="none")
        ttk.Radiobutton(agent_f, text="Online (OpenAI)", variable=self.agent_var, value="openai").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(agent_f, text="Local (Ollama)", variable=self.agent_var, value="ollama").pack(side=tk.LEFT, padx=(0, 12))
        ttk.Radiobutton(agent_f, text="No AI summary", variable=self.agent_var, value="none").pack(side=tk.LEFT)
        row += 1

        ttk.Button(parent, text="Compare & Generate Reports", command=self._on_compare).grid(row=row, column=1, sticky=tk.W, pady=8)
        row += 1

        self.config_status_var = tk.StringVar(value="Load parameters (file or MAVLink), then click Compare.")
        ttk.Label(parent, textvariable=self.config_status_var, foreground="gray", wraplength=500).grid(row=row, column=1, sticky=tk.W)

    def _on_load_param_file(self):
        path = filedialog.askopenfilename(
            title="Select parameter file",
            filetypes=[("Param files", "*.param *.parm *.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        self.param_file_path = Path(path)
        self.current_params = load_user_params_from_file(self.param_file_path)
        self.param_file_label.config(text=f"{self.param_file_path.name} ({len(self.current_params)} params)", foreground="")
        self.config_status_var.set(f"Loaded {len(self.current_params)} parameters from file.")

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

    def _apply_fetched_params(self, params: Dict[str, float], conn: str, error: Optional[str] = None):
        if error:
            self.config_status_var.set(f"Fetch failed: {error}")
            return
        self.current_params = params
        self.param_file_label.config(text=f"MAVLink ({len(params)} params)", foreground="")
        self.config_status_var.set(f"Fetched {len(params)} parameters via MAVLink.")

    def _on_compare(self):
        if not self.current_params:
            self.config_status_var.set("Load or fetch parameters first (file or MAVLink).")
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
        self.ai_summary_var = tk.StringVar(value="")
        ai_frame = ttk.LabelFrame(parent, text="AI summary (when generated)")
        ai_frame.pack(fill=tk.X, pady=(0, 8))
        self.ai_summary_label = ttk.Label(ai_frame, textvariable=self.ai_summary_var, wraplength=700)
        self.ai_summary_label.pack(anchor=tk.W, padx=6, pady=4)
        self.report_notebook = ttk.Notebook(parent)
        self.report_notebook.pack(fill=tk.BOTH, expand=True)
        self.report_treeviews: Dict[str, ttk.Treeview] = {}
        self.report_summary_vars: Dict[str, tk.StringVar] = {}
        for mode in MODES:
            frame = ttk.Frame(self.report_notebook, padding=5)
            self.report_notebook.add(frame, text=mode)
            # Export buttons
            btn_f = ttk.Frame(frame)
            btn_f.pack(fill=tk.X)
            ttk.Button(btn_f, text="Export HTML", command=lambda m=mode: self._export_report(m, "html")).pack(side=tk.LEFT, padx=(0, 4))
            ttk.Button(btn_f, text="Export PDF", command=lambda m=mode: self._export_report(m, "pdf")).pack(side=tk.LEFT, padx=(0, 4))
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
        f = ttk.Frame(parent)
        f.pack(fill=tk.X)
        ttk.Button(f, text="Select mission file…", command=self._on_select_mission).pack(side=tk.LEFT, padx=(0, 8))
        self.mission_path_var = tk.StringVar(value="No file selected")
        ttk.Label(f, textvariable=self.mission_path_var).pack(side=tk.LEFT)
        ttk.Button(parent, text="Analyze mission", command=self._on_analyze_mission).pack(anchor=tk.W, pady=(0, 4))
        self.mission_result = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=12, width=80)
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
        f = ttk.Frame(parent)
        f.pack(fill=tk.X)
        ttk.Button(f, text="Select log file…", command=self._on_select_log).pack(side=tk.LEFT, padx=(0, 8))
        self.log_path_var = tk.StringVar(value="No file selected")
        ttk.Label(f, textvariable=self.log_path_var).pack(side=tk.LEFT)
        ttk.Button(parent, text="Analyze log", command=self._on_analyze_log).pack(anchor=tk.W, pady=(0, 4))
        self.log_result = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=12, width=80)
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
        data = parse_flight_log(self.log_file_path)
        analysis = analyze_flight_log(data)
        self.log_result.delete("1.0", tk.END)
        self.log_result.insert(tk.END, analysis.get("summary", "") + "\n\n")
        for s in analysis.get("suggestions", []):
            self.log_result.insert(tk.END, "• " + s + "\n")

    def _build_assistant_tab(self, parent: ttk.Frame):
        self.chat_text = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=14, width=80)
        self.chat_text.pack(fill=tk.BOTH, expand=True, pady=(0, 8))
        f = ttk.Frame(parent)
        f.pack(fill=tk.X)
        self.assistant_entry = ttk.Entry(f, width=60)
        self.assistant_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        ttk.Button(f, text="Ask", command=self._on_ask_assistant).pack(side=tk.LEFT)
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
