# Local LLM (Ollama) Guide — ArduPilot AI Assistant

This guide explains how to use a **local LLM** with the ArduPilot AI Assistant: which models work best, how to install and run them, how to build the **knowledge base** (parameter database), and how to use the app with Ollama.

---

## 1. Recommended Ollama models for this application

The app uses the LLM for:

- **Parameter Q&A** (Manual, FBWA, AUTO, Autotune)
- **Report summaries** (compare results in plain language)
- **Mission interpretation** (waypoints, commands, safety)
- **Flight log interpretation** (modes, events, suggestions)

You want a model that is **good at following instructions**, **technical text**, and **short, concise answers**. These models work with the app and are supported by Ollama:

| Model | Size (approx.) | RAM (min.) | Best for | Notes |
|-------|----------------|------------|----------|--------|
| **llama3.2** (default) | 2 GB (3B) | 4–6 GB | Balanced speed/quality, default in app | Fast, good for most use. 3B variant. |
| **llama3.2:1b** | ~1.3 GB | 2–4 GB | Low-resource PCs | Weaker reasoning, fastest. |
| **qwen2.5:7b** | ~4.7 GB | 8 GB | Better reasoning, still efficient | Strong for technical Q&A and summaries. |
| **qwen2.5:3b** | ~2 GB | 4–6 GB | Laptops / mid-range PCs | Good trade-off; often better than llama3.2 3B. |
| **mistral** | ~4.1 GB | 8 GB | High quality, concise answers | Very good for instructions and summaries. |
| **phi3** | ~2.3 GB | 4–6 GB | Low RAM, acceptable quality | Microsoft small model; runs on modest hardware. |
| **gemma2:2b** | ~1.6 GB | 4 GB | Lightweight | Google small model; fast. |

**Recommendation for this app:**

- **Default / good for most users:** `llama3.2` (already set in config) — no change needed.
- **Better quality (if you have 8 GB+ RAM):** `qwen2.5:7b` or `mistral` — set `OLLAMA_MODEL=qwen2.5:7b` or `OLLAMA_MODEL=mistral` in `.env`.
- **Limited RAM (4–6 GB free):** `llama3.2:1b`, `phi3`, or `gemma2:2b` — set e.g. `OLLAMA_MODEL=phi3` in `.env`.

The app does **not** require a specific model name; any Ollama chat model will work. Slower or smaller models may give shorter or less precise answers.

---

## 2. Step-by-step: Install Ollama and a model

### Step 1 — Download and install Ollama

1. Go to **https://ollama.com**.
2. Click **Download** and choose your OS (Windows, macOS, or Linux).
3. Run the installer and follow the prompts.
4. Ensure Ollama is **running** (on Windows it often runs in the system tray; on Mac/Linux you can run `ollama serve` in a terminal if it is not already running).

### Step 2 — Pull a model

Open a terminal (or PowerShell) and run one of these. Only the first run downloads the model; later runs use the cached copy.

**Option A — Use the app default (recommended to start):**

```bash
ollama pull llama3.2
```

**Option B — Use a model from the table above (examples):**

```bash
# Better quality (needs ~8 GB RAM)
ollama pull qwen2.5:7b
# or
ollama pull mistral

# Lighter (4–6 GB RAM)
ollama pull qwen2.5:3b
ollama pull phi3
ollama pull gemma2:2b
```

Check that the model is available:

```bash
ollama list
```

You should see your model (e.g. `llama3.2`, `qwen2.5:7b`) in the list.

### Step 3 — Configure the app to use your model

1. In the project folder, open or create the **`.env`** file (same folder as `config.py`).
2. Set the model and (optionally) Ollama URL:

```env
# Local LLM (Ollama)
OLLAMA_MODEL=llama3.2
OLLAMA_BASE_URL=http://localhost:11434
```

Replace `llama3.2` with the model you pulled (e.g. `qwen2.5:7b`, `mistral`, `phi3`).  
If Ollama runs on another machine or port, change `OLLAMA_BASE_URL` (e.g. `http://192.168.1.10:11434`).

3. Save `.env`. The app reads these variables on startup.

---

## 3. Build the knowledge base (parameter database)

The app’s “knowledge base” for the local LLM is the **ArduPilot parameter list** in `data/params.json`. The LLM does **not** get trained on this file; the app **injects** relevant parameters and your current values into each prompt. So “studying” = having an up-to-date `params.json` and using the app (which sends that data to Ollama automatically).

To refresh the parameter list from the official ArduPilot docs:

1. Open a terminal in the project root (where `scripts/scrape_params.py` is).
2. Activate your virtual environment if you use one:

   ```bash
   venv\Scripts\activate    # Windows
   # source venv/bin/activate  # Linux/macOS
   ```

3. Run the scraper:

   ```bash
   python scripts/scrape_params.py
   ```

4. You should see something like: `Found 4555 parameters. Saved to .../data/params.json`.  
   The app will then use this file when you run **Compare**, **AI Assistant**, **Mission**, or **Flight log** features.

You do **not** need to “train” or “fine-tune” Ollama. The knowledge base is used only by the app at runtime (it passes parameter names, descriptions, and your values in the prompt).

---

## 4. Use the app with the local LLM

### Standalone (desktop) app

1. Start Ollama (if not already running) and pull the model you set in `.env` (see Step 2).
2. Run:

   ```bash
   python run_standalone.py
   ```

3. In the **Config & Compare** tab, under **AI agent for reports**, choose **Local (Ollama)**.
4. Load your parameter file (or fetch via MAVLink), then click **Compare & Generate Reports** — the summary and report explanations use your local model.
5. In **Mission** and **Flight log** tabs, run **Analyze** — again the app will use Ollama for the interpretation.
6. In the **AI Assistant** tab, ask questions; the assistant uses the same **Local (Ollama)** agent when selected (or follows the global agent choice).

### Web app (Flask)

1. Start Ollama and ensure the model in `.env` is pulled.
2. Run:

   ```bash
   python run_web.py
   ```

3. Open **http://127.0.0.1:5000** in your browser.
4. In **Configuration**, select **Local (Ollama)** as the agent.
5. Use **Compare & Generate Reports**, **Mission analysis** (with “Analyze with AI” checked), and **Flight log analysis** (with “Analyze with AI” checked) — all will use your local model.
6. Use **AI Assistant** to ask questions; answers will come from Ollama when that agent is selected.

### If the app says “Ollama failed” or no answer

- Confirm Ollama is running: open **http://localhost:11434** in a browser; you should see a simple Ollama page or API response.
- Run `ollama list` and ensure the model name matches **exactly** what you put in `OLLAMA_MODEL` (e.g. `qwen2.5:7b` not `qwen2.5` if you pulled the 7b variant).
- Try in the terminal: `ollama run llama3.2` (or your model) and type a short question; if that works, the same model name in `.env` should work in the app.
- On another machine/port: set `OLLAMA_BASE_URL` in `.env` to that address (e.g. `http://192.168.1.10:11434`).

---

## 5. Summary checklist

| Step | Action |
|------|--------|
| 1 | Install Ollama from https://ollama.com |
| 2 | Run `ollama pull <model>` (e.g. `llama3.2` or `qwen2.5:7b`) |
| 3 | Set `OLLAMA_MODEL=<model>` and optionally `OLLAMA_BASE_URL` in `.env` |
| 4 | Run `python scripts/scrape_params.py` to refresh `data/params.json` |
| 5 | Start the app (`run_standalone.py` or `run_web.py`) and select **Local (Ollama)** |
| 6 | Use Compare, Mission, Flight log, and AI Assistant; the app sends the knowledge base (params + context) to the local model automatically |

No extra “study” or training step is required: the app uses the knowledge base by including it in the prompts sent to Ollama.
