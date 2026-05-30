# ⚡ Nexus Lead Gen Intelligence

A state-of-the-art corporate discovery and prospecting platform designed to uncover deep organizational insights and compile ready-to-use outreach data. Built for high performance, Nexus validates target URLs, scrapes domain structures intelligently, and utilizes advanced LLM synthesis to produce structured value-propositions.

---

## 🌟 Features

- **Automated Domain Scanning**: Uses string similarity (RapidFuzz) to identify high-value subpages (e.g., `/contact`, `/about-us`, `/solutions`).
- **Resilient Web Extraction**: 
  - Employs a robust rotating extraction strategy.
  - Implements intelligent exponential backoffs to navigate blocks.
- **Precision Data Parsing**: Custom regular expressions and international formatters to reliably extract emails and direct lines.
- **LLM-Powered Insights**: Integrates with Groq (`llama-3.3-70b-versatile`) to read raw corporate text and produce nuanced, structured insights without hallucination.
- **Fail-safe Data Pipelines**: Enforces strict Pydantic models for data validation, automatically falling back on secure defaults on format errors.

---

## 📁 Repository Structure

- `app.py`: The beautiful, high-converting Streamlit interface.
- `api.py`: FastAPI backend offering microservices for programmatic access.
- `src/`: Core logic package.
  - `scraper.py`: Core web-crawling logic and fallback systems.
  - `agent.py`: Pydantic models and the Groq LLM integration pipeline.
  - `database.py`: SQLite wrapper for seamless lead storage.
  - `config.py`: Environment loader and system variables.
- `notebooks/`: Jupyter Notebooks & Google Colab scripts.
  - `AI_Prospect_Research_Agent.ipynb`: Interactive Jupyter Notebook.
- `style.css`: Premium "Vibrant Amethyst" styling for the dashboard.
- `requirements.txt`: Python package requirements.
- `.env`: Environment variables file (create this based on your configuration).

---

## 🛠️ Quick Start

We recommend using a virtual environment manager like `uv` or `venv` to keep your workspace clean.

### 1. Set Up the Environment
```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Mac/Linux
source .venv/bin/activate
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure Your Environment
Make sure you have created your `.env` file containing your API credentials:
```env
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Launch the Application
Run the visually stunning Streamlit dashboard:
```bash
streamlit run app.py
```
Or start the FastAPI backend server:
```bash
uvicorn api:app --port 8000
```
