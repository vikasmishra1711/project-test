import os

# Manual .env parser to load configuration dynamically without dependencies
def _load_env_file():
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

_load_env_file()

# ========= CONFIG =========
# Try to load secrets from Streamlit Secrets (for Streamlit Cloud deployment), else fallback to environment
GROQ_API_KEY = None
try:
    import streamlit as st
    if hasattr(st, "secrets") and "GROQ_API_KEY" in st.secrets:
        GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
except Exception:
    pass

if not GROQ_API_KEY:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Groq endpoint configuration
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Model choice extracted safely from local environment/Streamlit secrets
GROQ_MODEL = None
try:
    import streamlit as st
    if hasattr(st, "secrets") and "GROQ_MODEL" in st.secrets:
        GROQ_MODEL = st.secrets["GROQ_MODEL"]
except Exception:
    pass

if not GROQ_MODEL:
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

# Scraping & Discovery Settings
TIMEOUT = 10
MAX_DISCOVERED_PAGES = 5

PRIORITY_KEYWORDS = [
    "about",
    "about-us",
    "company",
    "services",
    "solutions",
    "products",
    "contact",
    "contact-us",
    "who-we-are",
    "industries"
]

IGNORE_KEYWORDS = [
    "blog",
    "careers",
    "privacy",
    "terms",
    "news",
    "events"
]

# Database Config
DB_NAME = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prospects.db")
