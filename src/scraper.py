import re
import time
import logging
import urllib.parse
import requests
from bs4 import BeautifulSoup
import phonenumbers
from rapidfuzz import fuzz
from typing import List, Dict, Set, Any, Tuple
from .config import TIMEOUT, MAX_DISCOVERED_PAGES, PRIORITY_KEYWORDS, IGNORE_KEYWORDS

# Setup logging
logger = logging.getLogger(__name__)

# List of rotating User-Agents for Method 2
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def validate_and_normalize_url(url: str) -> str:
    """Validate and normalize a URL, adding https:// if missing."""
    url = url.strip()
    if not url:
        return ""
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    
    # Check basic structure
    parsed = urllib.parse.urlparse(url)
    if not parsed.netloc:
        return ""
    return url

def get_base_domain(url: str) -> str:
    """Get the base domain of a URL (e.g. fireflies.ai from https://fireflies.ai/about)."""
    parsed = urllib.parse.urlparse(url)
    domain = parsed.netloc.lower()
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

def extract_links_from_html(html: str, base_url: str) -> Set[str]:
    """Extract all unique internal absolute links from raw HTML."""
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    base_domain = get_base_domain(base_url)
    parsed_base = urllib.parse.urlparse(base_url)
    
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        
        # Make absolute
        absolute_url = urllib.parse.urljoin(base_url, href)
        parsed_abs = urllib.parse.urlparse(absolute_url)
        
        # Verify it is on the same domain or subdomain
        abs_domain = parsed_abs.netloc.lower()
        if abs_domain.startswith("www."):
            abs_domain = abs_domain[4:]
            
        if abs_domain == base_domain or abs_domain.endswith("." + base_domain):
            # Clean url fragment
            cleaned_url = urllib.parse.urlunparse((
                parsed_abs.scheme,
                parsed_abs.netloc,
                parsed_abs.path,
                parsed_abs.params,
                "",  # Clear query parameters and fragment to prevent duplicate scraping of same pages
                ""
            ))
            links.add(cleaned_url)
            
    return links

def score_and_filter_links(links: Set[str], base_url: str) -> List[str]:
    """
    Score links using RapidFuzz based on similarity to priority keywords.
    Filter out ignored paths and return top priority pages.
    """
    scored_links = []
    base_domain = get_base_domain(base_url)
    
    for link in links:
        parsed = urllib.parse.urlparse(link)
        path = parsed.path.lower().strip("/")
        
        # If it's just the homepage, skip scoring (it will be included automatically)
        if not path:
            continue
            
        # Ignore check: If any ignore keyword is a substring of the path, skip
        if any(ignore in path for ignore in IGNORE_KEYWORDS):
            continue
            
        # Extract keywords or segments from path (e.g. /about-us -> 'about us')
        path_segment = path.replace("-", " ").replace("_", " ")
        
        # RapidFuzz Scoring against PRIORITY_KEYWORDS
        max_score = 0.0
        for priority in PRIORITY_KEYWORDS:
            # We calculate similarity scores
            # ratio is normal Levenshtein distance, partial_ratio is substring matching
            ratio = fuzz.ratio(priority, path_segment)
            partial_ratio = fuzz.partial_ratio(priority, path_segment)
            score = max(ratio, partial_ratio)
            if score > max_score:
                max_score = score
                
        # Only keep links with a reasonable similarity match (e.g. > 50) OR containing priority keywords
        if max_score > 50 or any(priority in path for priority in PRIORITY_KEYWORDS):
            # Boost score if there's an exact priority substring in the path
            boost = 30 if any(priority in path for priority in PRIORITY_KEYWORDS) else 0
            scored_links.append((link, max_score + boost))
            
    # Sort links descending by score
    scored_links.sort(key=lambda x: x[1], reverse=True)
    
    # Pick the top MAX_DISCOVERED_PAGES - 1 (default 4) unique links
    selected = [base_url]
    for link, score in scored_links:
        if link not in selected:
            selected.append(link)
            if len(selected) >= MAX_DISCOVERED_PAGES:
                break
                
    logger.info(f"Smart Page Discovery selected {len(selected)} pages: {selected}")
    return selected

def scrape_with_fallbacks(url: str) -> str:
    """
    Scrape a single URL using a 3-fallback pipeline:
    Method 1: Requests + BeautifulSoup (standard headers)
    Method 2: Alternate User-Agent
    Method 3: Backoff retries
    """
    # Method 1: Standard Requests
    logger.info(f"Method 1: Attempting standard request for {url}")
    headers_m1 = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5"
    }
    
    try:
        response = requests.get(url, headers=headers_m1, timeout=TIMEOUT)
        if response.status_code == 200:
            return response.text
        logger.warning(f"Method 1 failed with status code {response.status_code} for {url}")
    except Exception as e:
        logger.warning(f"Method 1 failed with exception: {e}")
        
    # Method 2: Alternate User-Agent (mobile / alternative browser)
    logger.info(f"Method 2: Attempting alternate User-Agent for {url}")
    for ua in USER_AGENTS:
        headers_m2 = {
            "User-Agent": ua,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Referer": "https://www.google.com/"
        }
        try:
            response = requests.get(url, headers=headers_m2, timeout=TIMEOUT)
            if response.status_code == 200:
                return response.text
            logger.warning(f"Method 2 (UA: {ua[:30]}...) failed with status code {response.status_code}")
        except Exception as e:
            logger.warning(f"Method 2 (UA: {ua[:30]}...) failed with exception: {e}")
            
    # Method 3: Retry Strategy with Backoff
    logger.info(f"Method 3: Attempting exponential backoff retries for {url}")
    backoffs = [2, 4, 8]
    for i, delay in enumerate(backoffs):
        time.sleep(delay)
        try:
            # Let's try a different request style, e.g., session
            session = requests.Session()
            response = session.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=TIMEOUT)
            if response.status_code == 200:
                return response.text
            logger.warning(f"Method 3 Retry {i+1} failed with status code {response.status_code}")
        except Exception as e:
            logger.warning(f"Method 3 Retry {i+1} failed with exception: {e}")
            
    # If all fail, return empty
    logger.error(f"All scraping fallbacks failed for {url}")
    return ""

def clean_html_content(html: str) -> str:
    """
    Clean HTML content by removing headers, footers, popups, styles, and scripts.
    Keep description, solutions, services, and core texts.
    Compresses whitespace and formats content.
    """
    if not html:
        return ""
        
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Remove non-content elements
    unwanted_tags = [
        "script", "style", "svg", "iframe", "footer", 
        "header", "nav", "noscript", "picture", "video"
    ]
    for tag in soup(unwanted_tags):
        tag.decompose()
        
    # Remove navigation, footers, cookie banners, popup elements by class/id keywords
    noise_patterns = [
        "cookie", "banner", "popup", "modal", "footer", "header", 
        "nav", "menu", "sidebar", "widget", "promo", "newsletter"
    ]
    for element in soup.find_all(True):
        attrs = str(element.attrs).lower()
        if any(pat in attrs for pat in noise_patterns):
            # Be careful not to delete main content that matches, but simple cookie/popup elements are safe
            if element.name in ["div", "section", "aside"]:
                # Check if it has text length that is very short (cookie banners usually have short text)
                text_len = len(element.get_text(strip=True))
                if text_len < 300:
                    element.decompose()
                    
    # 2. Extract textual data
    # Standard header and paragraph extractions, main body texts
    text_blocks = []
    
    # Grab headings and paragraphs
    for tag in soup.find_all(["h1", "h2", "h3", "h4", "p", "li"]):
        text = tag.get_text().strip()
        if text:
            # Simple deduplication or cleaning of long whitespaces
            text = re.sub(r'\s+', ' ', text)
            if text not in text_blocks:
                text_blocks.append(text)
                
    # Join clean text
    cleaned_text = "\n".join(text_blocks)
    return cleaned_text

def extract_emails(html: str) -> List[str]:
    """Extract all unique emails from HTML using regex."""
    if not html:
        return []
    # General email regex pattern
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    found = re.findall(email_pattern, html)
    
    # Deduplicate and filter out common image / asset email false positives
    unique_emails = set()
    for email in found:
        email = email.lower().strip()
        # Exclude obvious asset strings
        if not email.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg")):
            unique_emails.add(email)
            
    return list(unique_emails)

def extract_phone(html: str) -> str:
    """Extract and format the best phone number using the phonenumbers library."""
    if not html:
        return ""
    
    # Parse text from HTML to avoid tags breaking numbers
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text()
    
    best_phone = ""
    # Find all potential phone number blocks in the text
    # We will search with a relaxed regex first, then validate with phonenumbers
    # Matches patterns like +1-123-456-7890, (123) 456-7890, 123 456 7890, etc.
    phone_candidates = re.findall(r'\+?\b\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b', text)
    
    for candidate in phone_candidates:
        try:
            # We will parse assuming US or worldwide context.
            # Let's try parsing as international if starts with '+', else default to internationalized formats
            parsed = phonenumbers.parse(candidate, None)
            if phonenumbers.is_valid_number(parsed):
                formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                # Keep the first valid number or prefer longer format
                if not best_phone or len(formatted) > len(best_phone):
                    best_phone = formatted
        except Exception:
            # Try parsing with standard region fallback (e.g. US)
            try:
                parsed = phonenumbers.parse(candidate, "US")
                if phonenumbers.is_valid_number(parsed):
                    formatted = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                    best_phone = formatted
                    break
            except Exception:
                continue
                
    return best_phone

def extract_address(html: str) -> str:
    """
    Search for address details in the schema.org metadata, contact page, or footer text.
    """
    if not html:
        return ""
        
    soup = BeautifulSoup(html, "html.parser")
    
    # Strategy 1: Check microdata/json-ld for PostalAddress
    json_ld_tags = soup.find_all("script", type="application/ld+json")
    for tag in json_ld_tags:
        try:
            import json
            data = json.loads(tag.string)
            if isinstance(data, dict):
                # Search recursively for PostalAddress
                address = _find_address_in_json(data)
                if address:
                    return address
            elif isinstance(data, list):
                for item in data:
                    address = _find_address_in_json(item)
                    if address:
                        return address
        except Exception:
            continue
            
    # Strategy 2: Look in footer or elements with 'address' tags / classes
    address_tags = soup.find_all(["address", "div", "p", "span"])
    address_patterns = ["address", "office", "hq", "headquarters", "street", "postal"]
    
    for tag in address_tags:
        # Check tag name
        if tag.name == "address":
            text = tag.get_text(separator=" ").strip()
            if len(text) > 10 and len(text) < 200:
                return re.sub(r'\s+', ' ', text)
                
        # Check classes/ids
        attrs = str(tag.attrs).lower()
        if any(pat in attrs for pat in address_patterns):
            text = tag.get_text(separator=" ").strip()
            # Basic heuristic for addresses: digits + words + zip code
            if len(text) > 15 and len(text) < 150 and re.search(r'\d+', text) and (re.search(r'[A-Z]{2}\s+\d{5}', text) or re.search(r'\b[a-zA-Z]+\b', text)):
                cleaned = re.sub(r'\s+', ' ', text)
                # Ensure it is not a navigation menu
                if len(cleaned.split(",")) >= 2:
                    return cleaned
                    
    return ""

def _find_address_in_json(data: Any) -> str:
    """Helper to traverse JSON-LD and extract streetAddress, addressLocality, addressRegion, postalCode."""
    if not isinstance(data, dict):
        return ""
        
    # Check if this node is PostalAddress
    if data.get("@type") == "PostalAddress" or "streetAddress" in data:
        parts = []
        for key in ["streetAddress", "addressLocality", "addressRegion", "postalCode", "addressCountry"]:
            val = data.get(key)
            if val:
                if isinstance(val, dict):
                    name = val.get("name") or val.get("@value")
                    if name:
                        parts.append(str(name))
                else:
                    parts.append(str(val))
        if parts:
            return ", ".join(parts)
            
    # Otherwise search nested keys
    for k, v in data.items():
        if isinstance(v, dict):
            res = _find_address_in_json(v)
            if res:
                return res
        elif isinstance(v, list):
            for item in v:
                res = _find_address_in_json(item)
                if res:
                    return res
    return ""

def run_enrichment_scraping_pipeline(start_url: str) -> Dict[str, Any]:
    """
    Full scraping pipeline for a target URL:
    1. Normalizes the start URL.
    2. Scrapes the home page.
    3. Discovers up to 4 other highly relevant pages using RapidFuzz.
    4. Scrapes them in parallel / series using the 3-fallback engine.
    5. Cleans and condenses all scraped texts.
    6. Extracts emails, phone, and addresses across pages.
    7. Standardizes target LLM content length (< 5000 chars).
    """
    normalized_url = validate_and_normalize_url(start_url)
    if not normalized_url:
        logger.error(f"Invalid URL: {start_url}")
        return {
            "website_name": start_url,
            "company_name": "",
            "address": "",
            "mobile_number": "",
            "mail": [],
            "raw_scraped_content": ""
        }
        
    logger.info(f"Starting scraping pipeline for: {normalized_url}")
    
    # 1. Scrape the Homepage
    homepage_html = scrape_with_fallbacks(normalized_url)
    if not homepage_html:
        logger.error(f"Failed to scrape homepage for {normalized_url}")
        # Return empty/fallback scraper details
        return {
            "website_name": get_base_domain(normalized_url),
            "company_name": "",
            "address": "",
            "mobile_number": "",
            "mail": [],
            "raw_scraped_content": ""
        }
        
    # 2. Discover links from the homepage
    raw_links = extract_links_from_html(homepage_html, normalized_url)
    selected_pages = score_and_filter_links(raw_links, normalized_url)
    
    # 3. Scrape discovered pages
    scraped_pages_html = {normalized_url: homepage_html}
    for page in selected_pages:
        if page == normalized_url:
            continue
        html = scrape_with_fallbacks(page)
        if html:
            scraped_pages_html[page] = html
            
    # 4. Extract data and clean content
    combined_cleaned_texts = []
    all_emails = set()
    best_phone = ""
    best_address = ""
    
    # Process homepage first for emails/phone/address preference
    for page, html in scraped_pages_html.items():
        # Emails
        emails = extract_emails(html)
        all_emails.update(emails)
        
        # Phone
        phone = extract_phone(html)
        if phone and not best_phone:
            best_phone = phone
            
        # Address
        address = extract_address(html)
        if address and not best_address:
            best_address = address
            
        # Cleaned body content
        cleaned_body = clean_html_content(html)
        if cleaned_body:
            # Label the content for the LLM
            page_name = urllib.parse.urlparse(page).path.strip("/") or "Home"
            combined_cleaned_texts.append(f"--- PAGE: {page_name.upper()} ---\n{cleaned_body}")
            
    # Combine content and limit length
    full_content = "\n\n".join(combined_cleaned_texts)
    
    # Whitespace compression
    full_content = re.sub(r'\n{3,}', '\n\n', full_content)
    
    # Cap size to 4800 characters to leave safety margin under 5000 characters
    if len(full_content) > 4800:
        logger.info(f"Truncating content from {len(full_content)} to 4800 characters")
        # Find last newline before 4800 to truncate cleanly
        truncate_point = full_content.rfind("\n", 0, 4800)
        if truncate_point > 4000:
            full_content = full_content[:truncate_point] + "\n[Content Truncated...]"
        else:
            full_content = full_content[:4800] + "\n[Content Truncated...]"
            
    website_name = get_base_domain(normalized_url)
    
    # Get basic fallback company name from domain name
    company_name_fallback = website_name.split(".")[0].title()
    
    return {
        "website_name": website_name,
        "company_name": company_name_fallback,
        "address": best_address,
        "mobile_number": best_phone,
        "mail": list(all_emails),
        "raw_scraped_content": full_content
    }
