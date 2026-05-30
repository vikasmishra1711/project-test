import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.database import init_db, save_company_profile, get_all_companies
from src.scraper import run_enrichment_scraping_pipeline
from src.agent import analyze_with_groq

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI App
app = FastAPI(
    title="AI Prospect Research Agent API",
    description="High-performance prospect intelligence API for automated company profiling and lead enrichment.",
    version="1.0.0"
)

# Input Pydantic Model
class EnrichRequest(BaseModel):
    url: str

@app.on_event("startup")
def startup_event():
    """Initializes the database schema on service start."""
    init_db()

@app.get("/")
def read_root():
    """Welcome endpoint."""
    return {
        "status": "online",
        "message": "Welcome to the AI Prospect Research Agent API. Use POST /enrich to enrich a URL or GET /results to list profiles."
    }

@app.post("/enrich", response_model=dict)
def enrich_company_endpoint(request: EnrichRequest):
    """
    Enriches a company by scraping its website, performing contact discovery,
    running reasoning analysis via Groq, persisting it to SQLite, and returning results.
    """
    url = request.url.strip()
    if not url:
        raise HTTPException(status_code=400, detail="URL cannot be empty.")
        
    try:
        logger.info(f"Received API enrichment request for URL: {url}")
        
        # 1. Scraping and Contact Extraction
        scraped_data = run_enrichment_scraping_pipeline(url)
        
        # 2. LLM Reasoning and Profile Structuring
        profile = analyze_with_groq(
            website_url=url,
            cleaned_content=scraped_data.get("raw_scraped_content", ""),
            extracted_contacts=scraped_data
        )
        
        # 3. Save to Database
        db_id = save_company_profile(profile)
        profile["id"] = db_id
        
        return profile
        
    except Exception as e:
        logger.error(f"Failed to enrich company for URL {url}: {e}")
        # Always guarantee safe fallback even if top-level crashes
        from src.agent import get_safe_fallback
        fallback = get_safe_fallback(url)
        try:
            db_id = save_company_profile(fallback)
            fallback["id"] = db_id
            return fallback
        except Exception as db_err:
            logger.error(f"Fallback database save failed: {db_err}")
            return fallback

@app.get("/results", response_model=list)
def get_all_results_endpoint():
    """Fetches all enriched company profiles from the SQLite database."""
    try:
        companies = get_all_companies()
        return companies
    except Exception as e:
        logger.error(f"Failed to fetch results: {e}")
        raise HTTPException(status_code=500, detail=f"Database retrieval failed: {str(e)}")
