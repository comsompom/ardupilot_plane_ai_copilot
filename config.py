"""
Configuration for ArduPilot AI Assistant.
"""
import os
from pathlib import Path

# Base paths
BASE_DIR = Path(__file__).resolve().parent

# Load .env if present (so OPENAI_API_KEY can be set without exporting)
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    pass
DATA_DIR = BASE_DIR / "data"
KNOWLEDGE_DIR = BASE_DIR / "knowledge_base"
CACHE_DIR = DATA_DIR / "cache"

# ArduPilot docs (configurable version)
ARDUPILOT_PARAMS_URL = os.getenv(
    "ARDUPILOT_PARAMS_URL",
    "https://ardupilot.org/plane/docs/parameters-Plane-stable-V4.6.2.html",
)
ARDUPLANE_VERSION = "4.6.2"

# Param DB
PARAM_DB_PATH = DATA_DIR / "params.json"
PARAM_DB_SQLITE = DATA_DIR / "params.db"

# RAG / AI
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "all-MiniLM-L6-v2")
# Local LLM: set in .env. See LOCAL_LLM_GUIDE.md for recommended models (llama3.2, qwen2.5:7b, mistral, phi3, etc.)
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "5"))

# OpenAI (used when connected to internet and key is set)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

# Flask
FLASK_SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "dev-secret-change-in-production")
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "1").lower() in ("1", "true", "yes")

# MAVLink
MAVLINK_CONNECTION = os.getenv("MAVLINK_CONNECTION", "")  # e.g. udp:127.0.0.1:14550

# Ensure dirs exist
for d in (DATA_DIR, CACHE_DIR, KNOWLEDGE_DIR):
    d.mkdir(parents=True, exist_ok=True)
