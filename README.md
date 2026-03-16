# ArduPilot AI Assistant

**HACKHAZARDS '26** — AI-powered assistant for ArduPilot Plane pilots: parameter comparison, flight-mode reports, mission & flight log analysis, and offline AI chat.

## Features

- **Parameter comparison**: Compare your current ArduPilot parameters against recommended sets for **Manual**, **FBWA**, **AUTO** (waypoints), and **Autotune** (PID).
- **Plane type & context**: Select plane type, wingspan, and weight for tailored suggestions.
- **User params**: Load parameters from a **param file** (upload) or **MAVLink** (live connection).
- **Reports**: One tab per flight mode with a table (Parameter, Current, Recommended, Severity, Action). Export as **HTML**, **PDF**, or **TXT**.
- **AI assistant**: Ask questions about params and flight modes. When connected to the internet and **OPENAI_API_KEY** is set, uses **OpenAI**; otherwise uses **Ollama** (local) when available; keyword fallback when both are unavailable.
- **Mission analysis**: Upload a mission file (e.g. from Mission Planner); get suggestions for your plane type.
- **Flight log analysis**: Upload a flight log; get suggestions for future flights.
- **Dual delivery**: **Standalone desktop app** (native PC application with Tkinter) and **Flask web app** (browser). Both use the same core.

## Tech stack (Built With)

- **Python 3.10+**
- **Tkinter** — standalone desktop app (stdlib)
- **Flask** — web application
- **pymavlink** — MAVLink connection and param fetch; flight log parsing
- **OpenAI API** — AI assistant when online (set `OPENAI_API_KEY`)
- **Ollama** — local LLM for AI assistant when offline (optional)
- **reportlab** — PDF export
- **Jinja2** — HTML templates
- **Requests / BeautifulSoup** — param scraper (scripts)

## Quick start

### 1. Clone and install

```bash
cd ardupilot_plane_ai_copilot
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/macOS
pip install -r requirements.txt
```

### 2. (Optional) Refresh parameter knowledge base

Scrape the latest ArduPilot Plane parameters into `data/params.json`:

```bash
python scripts/scrape_params.py
```

If you skip this, the app uses the built-in minimal param list in `data/params.json`.

### 3. (Optional) AI assistant: OpenAI and/or Ollama

- **OpenAI (when online)**  
  Set your API key (e.g. in a `.env` file or environment):
  ```bash
  set OPENAI_API_KEY=sk-your-key-here    # Windows
  export OPENAI_API_KEY=sk-your-key-here # Linux/macOS
  ```
  When the key is set and the app can reach the API, the assistant uses OpenAI (default model: `gpt-4o-mini`; override with `OPENAI_MODEL`).

- **Ollama (offline)**  
  Install [Ollama](https://ollama.com) and run a model, e.g. `ollama run llama3.2`. Leave it running; the app uses it when OpenAI is not used or fails (e.g. no internet).

Without either, the assistant uses a keyword-based fallback.

### 4. Run the application

**Standalone (desktop app on PC):**
```bash
python run_standalone.py
```
Opens the native desktop application (Tkinter). Same functionality as the web app: config, compare, reports, mission/log analysis, AI assistant.

**Web (Flask):**
```bash
python run_web.py
```
Open **http://127.0.0.1:5000** in your browser. Use the UI to:

1. Choose **plane type**, wingspan, weight.
2. **Upload a .param file** or enter a MAVLink connection (e.g. `udp:127.0.0.1:14550`) and click **Fetch via MAVLink**.
3. Click **Compare & Generate Reports**.
4. Switch tabs (Manual, FBWA, AUTO, Autotune) and **Export** as HTML/PDF/TXT.
5. Use **Mission analysis** and **Flight log analysis** to upload files and get suggestions.
6. Use **AI Assistant** to ask questions.

## Project structure

```
ardupilot_plane_ai_copilot/
├── config.py           # Paths, URLs, env config
├── data/
│   ├── params.json     # Parameter DB (built-in or from scraper)
│   └── uploads/        # Uploaded param/mission/log files
├── core/               # Shared engine
│   ├── params.py       # Load param DB, user params (file/MAVLink)
│   ├── plane_types.py  # Plane type list
│   ├── recommendations.py  # Recommended param sets per mode
│   ├── comparator.py   # Compare user vs recommended
│   ├── reports.py      # Generate report, export HTML/PDF/TXT
│   ├── ai_assistant.py # Ollama + fallback answers
│   ├── mission_parser.py
│   └── log_parser.py
├── standalone/
│   └── app_tk.py       # Standalone desktop app (Tkinter)
├── web/
│   ├── app.py          # Flask web application
│   ├── templates/
│   └── static/
├── scripts/
│   └── scrape_params.py
├── run_standalone.py   # Run standalone desktop app
├── run_web.py         # Run Flask web app
├── requirements.txt
├── PLAN.md
└── README.md
```

## Hackathon alignment

- **Track**: AI (LLM + knowledge base) and Software Engineering (full-stack, Flask).
- **Deliverables**: Working prototype (param comparison, 4 reports, export, AI assistant, mission/log analysis), public repo, demo video, Built With, team info.
- **Rules**: Built during hackathon period; no plagiarism; proper disclosure of used libraries.

## License

Use and modify as needed for the hackathon. See repository LICENSE if present.
