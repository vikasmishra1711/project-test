import json
import logging
import requests
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from .config import GROQ_API_KEY, GROQ_API_URL, GROQ_MODEL

# Setup logging
logger = logging.getLogger(__name__)

# ----------------- PYDANTIC SCHEMA -----------------
class CompanyProfile(BaseModel):
    website_name: str = Field(default="", description="Cleaned hostname or website identifier")
    company_name: str = Field(default="", description="The official name of the company")
    address: str = Field(default="", description="Physical location or mailing address, empty string if missing")
    mobile_number: str = Field(default="", description="Contact phone number in international format or best available")
    mail: List[str] = Field(default_factory=list, description="Unique, valid contact emails discovered")
    core_service: str = Field(default="", description="Detailed summary of the company's core services/products")
    target_customer: str = Field(default="", description="Detailed description of the company's target audience/customer base")
    probable_pain_point: str = Field(default="", description="Key business challenges or pain points the company's target customer experiences")
    outreach_opener: str = Field(default="", description="A highly personalized, custom sales cold email hook or intro sentence referencing their core service")

# Safe fallback utility
def get_safe_fallback(website_name: str = "", scraped_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Generates a safe fallback dictionary satisfying the required schema."""
    sd = scraped_data or {}
    return {
        "website_name": website_name or sd.get("website_name", ""),
        "company_name": sd.get("company_name", website_name.split(".")[0].title() if website_name else ""),
        "address": sd.get("address", ""),
        "mobile_number": sd.get("mobile_number", ""),
        "mail": sd.get("mail", []),
        "core_service": "",
        "target_customer": "",
        "probable_pain_point": "",
        "outreach_opener": ""
    }

# ----------------- SYSTEM PROMPT -----------------
SYSTEM_PROMPT = """You are a professional business information extraction engine.

Strictly adhere to the following rules:
1. Use ONLY the supplied website content. Do not assume or extrapolate beyond direct textual facts.
2. Never fabricate/hallucinate email addresses, phone numbers, or addresses.
3. If specific contact details (email, phone, address) are missing from the content, use the extracted contact details provided in the prompt. If still missing, return "".
4. If a field cannot be answered with absolute certainty from the text, return "".
5. For "core_service" and "target_customer", give high-quality concise descriptions based strictly on the text.
6. For "probable_pain_point", analyze the problems their clients solve with their services, referencing the text.
7. For "outreach_opener", construct an engaging, personalized cold outreach opener line suitable for sales development (e.g. "I noticed how your platform helps [target customer] streamline [core service]...").
8. Return ONLY valid JSON matching the exact schema. No markdown, no markdown backticks, no explanations, no prefix, and no extra keys.

Response Schema:
{
  "website_name": "string",
  "company_name": "string",
  "address": "string",
  "mobile_number": "string",
  "mail": ["string"],
  "core_service": "string",
  "target_customer": "string",
  "probable_pain_point": "string",
  "outreach_opener": "string"
}"""

def analyze_with_groq(website_url: str, cleaned_content: str, extracted_contacts: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sends cleaned content and extracted contact details to the Groq API.
    Uses strict system instructions and response validation.
    """
    user_prompt = f"""Target Website URL: {website_url}

=== SCRAPED WEBSITE CONTENT ===
{cleaned_content}

=== PRE-EXTRACTED CONTACT DETAILS ===
Address: {extracted_contacts.get('address', '')}
Phone: {extracted_contacts.get('mobile_number', '')}
Emails: {extracted_contacts.get('mail', [])}

Instructions: Analyze the website content and pre-extracted contact details. Populate the JSON schema. Use empty string or empty lists where facts are missing. Avoid fabrication of facts. Use exact keys.
"""

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}  # Request strict JSON Mode from Groq
    }

    # Attempt 1: Initial LLM API call
    try:
        logger.info(f"Sending request to Groq ({GROQ_MODEL}) for website: {website_url}")
        response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=20)
        
        if response.status_code != 200:
            logger.error(f"Groq API returned error: status_code={response.status_code}, response={response.text}")
            raise Exception(f"API HTTP error {response.status_code}")
            
        res_json = response.json()
        raw_text = res_json["choices"][0]["message"]["content"].strip()
        logger.debug(f"Raw Groq response: {raw_text}")
        
        # Parse and validate with Pydantic
        parsed_data = json.loads(raw_text)
        validated_profile = CompanyProfile.model_validate(parsed_data)
        logger.info(f"Successfully extracted and validated profile for {website_url}")
        return validated_profile.model_dump()
        
    except Exception as e:
        logger.warning(f"Attempt 1 failed with error: {e}. Initiating retry...")
        
        # Attempt 2: Retry with explicit error description
        retry_prompt = f"""The previous API call failed validation with error: {str(e)}.
Please fix the JSON output. Remember to output ONLY a valid JSON object matching the exact keys below.
Required JSON Schema:
{{
  "website_name": "string",
  "company_name": "string",
  "address": "string",
  "mobile_number": "string",
  "mail": ["string"],
  "core_service": "string",
  "target_customer": "string",
  "probable_pain_point": "string",
  "outreach_opener": "string"
}}
Ensure the JSON matches perfectly, without formatting wrappers or extra elements."""

        try:
            payload_retry = {
                "model": GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                    {"role": "assistant", "content": "Error during processing. Awaiting corrective instructions."},
                    {"role": "user", "content": retry_prompt}
                ],
                "temperature": 0.05,
                "response_format": {"type": "json_object"}
            }
            
            logger.info("Sending retry request to Groq...")
            response_retry = requests.post(GROQ_API_URL, headers=headers, json=payload_retry, timeout=20)
            
            if response_retry.status_code == 200:
                res_json_retry = response_retry.json()
                raw_text_retry = res_json_retry["choices"][0]["message"]["content"].strip()
                parsed_data_retry = json.loads(raw_text_retry)
                validated_profile = CompanyProfile.model_validate(parsed_data_retry)
                logger.info(f"Retry succeeded for {website_url}!")
                return validated_profile.model_dump()
            else:
                logger.error(f"Retry request failed with status: {response_retry.status_code}")
        except Exception as retry_err:
            logger.error(f"Retry also failed: {retry_err}")
            
    # Fallback structure (Never Crash)
    logger.warning(f"Using safe fallback profile for {website_url}")
    return get_safe_fallback(extracted_contacts.get("website_name", ""), extracted_contacts)
