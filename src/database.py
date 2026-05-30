import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Any
from .config import DB_NAME

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and create the companies table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                website_name TEXT,
                company_name TEXT,
                address TEXT,
                mobile_number TEXT,
                mail TEXT,  -- Saved as JSON array string
                core_service TEXT,
                target_customer TEXT,
                probable_pain_point TEXT,
                outreach_opener TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")
        raise e
    finally:
        conn.close()

def save_company_profile(profile: Dict[str, Any]) -> int:
    """
    Save or update a company profile in the database.
    If the website already exists, we will update the record. Otherwise, we insert a new one.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Standardize data type of mail
    mail_raw = profile.get("mail", [])
    if isinstance(mail_raw, list):
        mail_str = json.dumps(mail_raw)
    elif isinstance(mail_raw, str):
        try:
            # Check if it is a JSON array string already
            json.loads(mail_raw)
            mail_str = mail_raw
        except json.JSONDecodeError:
            mail_str = json.dumps([mail_raw] if mail_raw else [])
    else:
        mail_str = json.dumps([])

    try:
        # Check if record already exists by website_name
        cursor.execute("SELECT id FROM companies WHERE website_name = ?", (profile.get("website_name", ""),))
        row = cursor.fetchone()
        
        if row:
            # Update existing
            cursor.execute("""
                UPDATE companies 
                SET company_name = ?, address = ?, mobile_number = ?, mail = ?, 
                    core_service = ?, target_customer = ?, probable_pain_point = ?, 
                    outreach_opener = ?, created_at = ?
                WHERE id = ?
            """, (
                profile.get("company_name", ""),
                profile.get("address", ""),
                profile.get("mobile_number", ""),
                mail_str,
                profile.get("core_service", ""),
                profile.get("target_customer", ""),
                profile.get("probable_pain_point", ""),
                profile.get("outreach_opener", ""),
                datetime.utcnow().isoformat(),
                row["id"]
            ))
            conn.commit()
            logger.info(f"Updated company record for {profile.get('website_name')}")
            return row["id"]
        else:
            # Insert new
            cursor.execute("""
                INSERT INTO companies (
                    website_name, company_name, address, mobile_number, mail, 
                    core_service, target_customer, probable_pain_point, outreach_opener
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.get("website_name", ""),
                profile.get("company_name", ""),
                profile.get("address", ""),
                profile.get("mobile_number", ""),
                mail_str,
                profile.get("core_service", ""),
                profile.get("target_customer", ""),
                profile.get("probable_pain_point", ""),
                profile.get("outreach_opener", "")
            ))
            conn.commit()
            new_id = cursor.lastrowid
            logger.info(f"Inserted new company record for {profile.get('website_name')} with id {new_id}")
            return new_id
    except Exception as e:
        logger.error(f"Error saving company profile to database: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_all_companies() -> List[Dict[str, Any]]:
    """Retrieve all company profiles from the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    companies = []
    try:
        cursor.execute("SELECT * FROM companies ORDER BY created_at DESC")
        rows = cursor.fetchall()
        for row in rows:
            company = dict(row)
            # Parse mail back to list
            try:
                company["mail"] = json.loads(company["mail"])
            except Exception:
                company["mail"] = []
            companies.append(company)
    except Exception as e:
        logger.error(f"Error fetching companies: {e}")
    finally:
        conn.close()
    return companies
