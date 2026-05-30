import json
import logging
import re
import pandas as pd
import streamlit as st
import textwrap
from src.database import init_db, save_company_profile, get_all_companies
from src.scraper import run_enrichment_scraping_pipeline
from src.agent import analyze_with_groq

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Set Streamlit Page Configuration (Collapse sidebar by default and remove it)
st.set_page_config(
    page_title="Corporate Intelligence & Prospecting Engine",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize DB on app load
init_db()

# ----------------- LOAD STYLE OVERRIDES & DEFINE RENDERER -----------------
def render_html(html_str: str):
    """Renders HTML by removing newlines and redundant spaces to prevent Streamlit code-block wrapping bugs."""
    clean_html = re.sub(r'\s*\n\s*', ' ', html_str).strip()
    st.markdown(clean_html, unsafe_allow_html=True)

try:
    with open("style.css", "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
except Exception as e:
    logger.error(f"Failed to load style.css: {e}")

# ----------------- MAIN PORTAL HEADER (With Blue Title) -----------------
render_html("""
<div class="portal-header">
    <h1 class="portal-title">Nexus Lead Gen Intelligence</h1>
    <p class="portal-subtitle">Target lookup and positioning analysis framework powered by Llama-3.3-70b-Versatile</p>
</div>
""")

# ----------------- METRICS/KPI CARDS GRID -----------------
companies = get_all_companies()
total_companies = len(companies)
email_count = sum(len(c.get("mail", [])) for c in companies)
avg_emails = round(email_count / total_companies, 1) if total_companies > 0 else 0

# Displays exactly 3 metrics side-by-side as requested
col_m1, col_m2, col_m3 = st.columns(3)

with col_m1:
    render_html(f"""
<div class="metric-container-custom">
<div class="metric-num-custom">{total_companies}</div>
<div class="metric-lbl-custom">Total Profiles</div>
<div style="font-size: 0.65rem; color: #94A3B8;">Companies analyzed in DB</div>
</div>
""")

with col_m2:
    render_html(f"""
<div class="metric-container-custom">
<div class="metric-num-custom">{email_count}</div>
<div class="metric-lbl-custom">Harvested Emails</div>
<div style="font-size: 0.65rem; color: #94A3B8;">Contacts discovered across sites</div>
</div>
""")

with col_m3:
    render_html(f"""
<div class="metric-container-custom">
<div class="metric-num-custom">{avg_emails}</div>
<div class="metric-lbl-custom">Avg Emails/Profile</div>
<div style="font-size: 0.65rem; color: #94A3B8;">Average contact density per lead</div>
</div>
""")

render_html("<div style='height:20px;'></div>")

# Portal Tabs
tab1, tab2 = st.tabs(["Company Enrichment", "Leads Repository"])

# ----------------- TAB 1: COMPANY ENRICHMENT -----------------
with tab1:
    st.markdown("### Profile Target URLs")
    st.markdown("Enter URL targets below to perform RapidFuzz page discovery, bypass scraper blocks, collect clean contacts, and map target pain points with LLM synthesis.")
    
    # Input Form (Two distinct URL input fields)
    with st.form("enrichment_form"):
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            url_1 = st.text_input(
                "First Target Website URL *", 
                value="https://www.example1.com/", 
                placeholder="https://www.example1.com/", 
                help="Lookup the primary corporate website."
            )
        with col_u2:
            url_2 = st.text_input(
                "Second Target Website URL (Optional)", 
                value="https://www.example2.com/", 
                placeholder="https://www.example2.com/", 
                help="Optional second corporate website to profile concurrently."
            )
            
        submit_btn = st.form_submit_button("HARVEST COMPANY INSIGHTS")
        
    if submit_btn:
        urls = []
        if url_1.strip():
            urls.append(url_1.strip())
        if url_2.strip():
            urls.append(url_2.strip())
            
        if not urls:
            st.error("Please enter at least one valid URL in the First Target Website field.")
        else:
            # Iterate and scrape each site together!
            for idx, url in enumerate(urls):
                st.markdown("<br>", unsafe_allow_html=True)
                
                # Dynamic visual stepper layout matching the screenshot!
                stepper_placeholder = st.empty()
                progress_bar = st.progress(0)
                
                try:
                    # Stepper 1
                    render_html(f"""
                    <div class="stepper-row">
                        <div class="stepper-left">
                            <div class="stepper-bullet"></div>
                            <span class="stepper-text">Processing Site ({idx+1}/{len(urls)}): <span style="color:#C084FC; font-weight:600;">{url}</span></span>
                        </div>
                        <span class="stepper-badge" style="background:rgba(147,51,234,0.1); color:#C084FC; border:1px solid rgba(147,51,234,0.2);">Analyzing</span>
                    </div>
                    """)
                    progress_bar.progress(20)
                    
                    # Scraping Call
                    scraped_data = run_enrichment_scraping_pipeline(url)
                    
                    # Stepper 2
                    render_html(f"""
                    <div class="stepper-row">
                        <div class="stepper-left">
                            <div class="stepper-bullet"></div>
                            <span class="stepper-text">Processing Site ({idx+1}/{len(urls)}): <span style="color:#C084FC; font-weight:600;">{url}</span></span>
                        </div>
                        <span class="stepper-badge" style="background:rgba(139,92,246,0.1); color:#C084FC; border:1px solid rgba(139,92,246,0.2);">LLM Synthesis</span>
                    </div>
                    """)
                    progress_bar.progress(60)
                    
                    # LLM Call
                    profile = analyze_with_groq(
                        website_url=url,
                        cleaned_content=scraped_data.get("raw_scraped_content", ""),
                        extracted_contacts=scraped_data
                    )
                    
                    progress_bar.progress(90)
                    
                    # Save to database
                    db_id = save_company_profile(profile)
                    
                    # Completed Stepper State
                    render_html(f"""
                    <div class="stepper-row" style="border-color: rgba(52,211,153,0.15);">
                        <div class="stepper-left">
                            <div class="stepper-bullet success"></div>
                            <span class="stepper-text">Processing Site ({idx+1}/{len(urls)}): <span style="color:#C084FC; font-weight:600;">{url}</span></span>
                        </div>
                        <span class="stepper-badge" style="background:rgba(52,211,153,0.1); color:#34D399; border:1px solid rgba(52,211,153,0.25);">Completed</span>
                    </div>
                    <div style="background: rgba(52,211,153,0.05); border:1px solid rgba(52,211,153,0.15); border-radius:6px; padding:12px; margin-top:-8px; margin-bottom:15px; display:flex; align-items:center; gap:10px;">
                        <span style="color:#34D399; font-weight:700;">✓</span>
                        <span style="color:#34D399; font-size:0.85rem;">Successfully processed profile: {profile.get('company_name')}</span>
                    </div>
                    """)
                    progress_bar.progress(100)
                    
                    # Display Corporate Portrait Card (Visual intelligence layout matching mockup!)
                    render_html(f"""
<div class="enterprise-card" style="padding:24px; box-shadow:0 8px 30px rgba(0,0,0,0.4); margin-bottom:24px;">

<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px;">
    <div style="display:flex; align-items:center; gap:10px;">
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="#9333EA" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
        <span style="font-size:1.35rem; font-weight:700; font-family:'Outfit',sans-serif; color:#FFFFFF;">Profile: <span style="color:#9333EA;">{profile.get('company_name')}</span></span>
    </div>
    <span style="background:rgba(52,211,153,0.1); color:#34D399; border:1px solid rgba(52,211,153,0.2); font-size:0.65rem; font-weight:700; border-radius:4px; padding:2px 8px; text-transform:uppercase; letter-spacing:0.05em;">Analysis Complete ✓</span>
</div>

<p style="margin:0 0 20px 0; font-size:0.85rem; color:#94A3B8;">Target Domain: <a href="https://{profile.get('website_name')}" target="_blank" style="color:#C084FC; text-decoration:none;">{profile.get('website_name')}</a></p>

<div style="display:flex; gap:20px; flex-wrap:wrap; margin-bottom:10px;">
    
    <!-- Col 1: Contact Information -->
    <div style="flex:1; min-width:280px; background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:8px; padding:18px; position:relative;">
        <div style="display:flex; justify-content:space-between;">
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:6px; width:100%;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9333EA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/></svg>
                <span style="font-size:0.9rem; font-weight:700; color:#FFFFFF; font-family:'Outfit',sans-serif;">Contact Information</span>
            </div>
        </div>
        <p style="margin: 6px 0; font-size:0.85rem; color:#94A3B8;"><strong>Entity Name</strong><br><span style="color:#F8FAFC;">{profile.get('company_name')}</span></p>
        <p style="margin: 10px 0; font-size:0.85rem; color:#94A3B8;"><strong>Corporate Address</strong><br><span style="color:#F8FAFC;">{profile.get('address') or '<span style="color:#64748B; font-style:italic;">Not Specified</span>'}</span></p>
        <p style="margin: 10px 0; font-size:0.85rem; color:#94A3B8;"><strong>Contact Number</strong><br><span style="color:#F8FAFC;">{profile.get('mobile_number') or '<span style="color:#64748B; font-style:italic;">Not Specified</span>'}</span></p>
        <p style="margin: 10px 0; font-size:0.85rem; color:#94A3B8;"><strong>Direct Emails</strong></p>
        <div style="margin-top:6px;">
            {"".join(f'<span class="email-tag">{email}</span>' for email in profile.get('mail', [])) or '<span style="color:#64748B; font-style:italic; font-size:0.85rem;">None Discovered</span>'}
        </div>
    </div>
    
    <!-- Col 2: Commercial Positioning -->
    <div style="flex:1; min-width:280px; background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:8px; padding:18px;">
        <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:6px;">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9333EA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M8 14s1.5 2 4 2 4-2 4-2"/><line x1="9" y1="9" x2="9.01" y2="9"/><line x1="15" y1="9" x2="15.01" y2="9"/></svg>
            <span style="font-size:0.9rem; font-weight:700; color:#FFFFFF; font-family:'Outfit',sans-serif;">Commercial Positioning</span>
        </div>
        <p style="margin: 6px 0; font-size:0.85rem; color:#9333EA; font-weight:600;">Core Services</p>
        <p style="margin: 0 0 10px 0; font-size:0.85rem; color:#F8FAFC; line-height:1.4;">{profile.get('core_service')}</p>
        <p style="margin: 10px 0; font-size:0.85rem; color:#9333EA; font-weight:600;">Ideal Target Audience</p>
        <p style="margin: 0 0 10px 0; font-size:0.85rem; color:#F8FAFC; line-height:1.4;">{profile.get('target_customer')}</p>
        <p style="margin: 10px 0; font-size:0.85rem; color:#9333EA; font-weight:600;">Probable Client Pain Points</p>
        <p style="margin: 0; font-size:0.85rem; color:#F8FAFC; line-height:1.4;">{profile.get('probable_pain_point')}</p>
    </div>
    
    <!-- Col 3: Custom Outreach Hook (with quote icons and Copy button) -->
    <div style="flex:1; min-width:280px; background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:8px; padding:18px; display:flex; flex-direction:column; justify-content:space-between;">
        <div>
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:12px; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:6px;">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9333EA" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
                <span style="font-size:0.9rem; font-weight:700; color:#FFFFFF; font-family:'Outfit',sans-serif;">Custom Outreach Hook</span>
            </div>
            <div class="outreach-quote-box">
                <span style="color:#EC4899; font-size:1.8rem; font-family:Georgia,serif; font-weight:700; line-height:0.1; display:inline-block; vertical-align:middle; margin-top:-10px; margin-right:5px;">“</span>
                {profile.get('outreach_opener')}
            </div>
        </div>
    </div>
    
</div>
</div>
""")
                    
                except Exception as e:
                    st.error(f"Lookup failure for `{url}`: {e}")
                    logger.error(f"UI Lookup Error for `{url}`: {e}")
                
            # Completed toast
            st.toast("Research run complete!")

# ----------------- TAB 2: LEADS REPOSITORY -----------------
with tab2:
    # Repository Header
    render_html("""
    <div style="background: #1e1028; border: 1px solid rgba(255,255,255,0.05); border-radius:12px; padding:24px; margin-bottom:24px; box-shadow: 0 4px 20px rgba(0,0,0,0.4);">
        <h4 style="margin:0 0 6px 0; font-size:1.25rem; font-weight:700; display:flex; align-items:center;">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#9333EA" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right:10px;"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            Profile Search & Exports
        </h4>
        <p style="color:#94A3B8; font-size:0.9rem; margin:0;">Filter, query, and bulk export structured corporate leads records.</p>
    </div>
    """)
    
    # Fetch from SQLite database
    companies = get_all_companies()
    
    # ----------------- INJECT CONVENIENT MOCK DATA IF DB IS COMPLETELY EMPTY -----------------
    if not companies:
        mock_profiles = [
            {
                "website_name": "dhl.com",
                "company_name": "DHL",
                "address": "Bonn, Germany",
                "mobile_number": "",
                "mail": [],
                "core_service": "Global package shipping, contract logistics, and supply chain routing.",
                "target_customer": "E-commerce vendors, manufacturers, and global suppliers.",
                "probable_pain_point": "Inefficient distribution lanes and lack of delivery route transparency.",
                "outreach_opener": "I noticed DHL's global logistics options and was highly impressed. Let me show you how to automate routing."
            },
            {
                "website_name": "fireflies.ai",
                "company_name": "Fireflies.ai",
                "address": "San Francisco, USA",
                "mobile_number": "",
                "mail": ["support@fireflies.ai"],
                "core_service": "AI Assistant for automated meeting transcribing, outlining, and content search.",
                "target_customer": "Enterprise business development, operations managers, and research teams.",
                "probable_pain_point": "Losing critical takeaways and manual note taking overhead.",
                "outreach_opener": "I love how Fireflies converts meeting recordings into searchable notes automatically. Let me share a new workflow."
            },
            {
                "website_name": "zapier.com",
                "company_name": "Zapier",
                "address": "San Francisco, USA",
                "mobile_number": "",
                "mail": ["support@zapier.com"],
                "core_service": "Automating workflows and tool integrations across SaaS platforms.",
                "target_customer": "Operations leads, IT admins, and digital merchants.",
                "probable_pain_point": "Difficult governance of complex cross-platform automated web hooks.",
                "outreach_opener": "I saw how Zapier streamlines workflow triggers and wanted to present a secure governance outline."
            },
            {
                "website_name": "dhl.com",
                "company_name": "DHL - Global Logistics",
                "address": "Bonn, Germany",
                "mobile_number": "",
                "mail": ["info@dhl.com"],
                "core_service": "Contract logistics and custom distribution routing.",
                "target_customer": "Enterprise suppliers and retail distributors.",
                "probable_pain_point": "Higher carbon footprint indexes across European shipping lines.",
                "outreach_opener": "I read about DHL's green shipping alternatives and wanted to share how AI can lower your carbon index."
            }
        ]
        # Insert them to database
        for profile in mock_profiles:
            save_company_profile(profile)
        companies = get_all_companies()
        
    if companies:
        # Search & Filter Layout
        col_search, col_filter, col_exp_csv, col_exp_json, col_refresh = st.columns([2, 1, 0.7, 0.7, 0.7])
        with col_search:
            search_query = st.text_input("Query Repository...", placeholder="Search by company, service, or pain point...")
        with col_filter:
            filter_domain = st.selectbox("Base Domain Extension", ["All"] + sorted(list(set(c["website_name"].split(".")[-1] for c in companies if "." in c["website_name"]))))
            
        # Apply Query Filter
        filtered_companies = []
        for c in companies:
            sq = search_query.lower()
            text_pool = f"{c.get('company_name', '')} {c.get('core_service', '')} {c.get('probable_pain_point', '')} {c.get('website_name', '')}".lower()
            
            if sq and sq not in text_pool:
                continue
                
            if filter_domain != "All":
                ext = c["website_name"].split(".")[-1] if "." in c["website_name"] else ""
                if ext != filter_domain:
                    continue
                    
            filtered_companies.append(c)
            
        # Exporters
        df_export = pd.DataFrame(filtered_companies)
        if not df_export.empty:
            df_export["mail"] = df_export["mail"].apply(lambda x: ", ".join(x) if isinstance(x, list) else str(x))
            
            # Export CSV
            csv_bytes = df_export.to_csv(index=False).encode('utf-8')
            with col_exp_csv:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                st.download_button(
                    label="📥 Export CSV",
                    data=csv_bytes,
                    file_name="prospects_export.csv",
                    mime="text/csv"
                )
                
            # Export JSON
            json_bytes = json.dumps(filtered_companies, indent=2).encode('utf-8')
            with col_exp_json:
                st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
                st.download_button(
                    label="</> Export JSON",
                    data=json_bytes,
                    file_name="prospects_export.json",
                    mime="application/json"
                )
        
        # Blue Outline Refresh Button
        with col_refresh:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("🔄 Refresh", key="refresh_repo_btn_mockup"):
                st.rerun()
        
        # Filtered leads text displaying styled blue matching screenshot!
        st.markdown(f"Filtered leads: <span style='color: #C084FC; font-weight: 600;'>{len(filtered_companies)} matching profiles</span>", unsafe_allow_html=True)
        st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
        
        # Display tabs
        subtab_cards, subtab_table, subtab_json = st.tabs(["Lead Cards", "Data Table", "Raw JSON Output"])
        
        # Active selection details panel (Render dynamic Visual Intelligence modal if details is clicked!)
        active_details_id = st.session_state.get("active_lead_details_id")
        if active_details_id:
            active_item = next((c for c in companies if c['id'] == active_details_id), None)
            if active_item:
                favicon_url_act = f"https://logo.clearbit.com/{active_item.get('website_name')}"
                render_html(f"""
<div class="enterprise-card" style="border-color: rgba(59, 130, 246, 0.45); background: rgba(18, 25, 41, 0.95); margin-bottom: 25px;">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
<span style="font-size:1.2rem; font-weight:700; font-family:'Outfit',sans-serif; color:#FFFFFF;">👁️ Detailed Corporate Overview</span>
<span style="background:rgba(147,51,234,0.1); color:#C084FC; border:1px solid rgba(147,51,234,0.25); font-size:0.65rem; font-weight:700; border-radius:4px; padding:2px 8px; text-transform:uppercase; letter-spacing:0.05em;">Intelligence Node</span>
</div>
<div style="display:flex; gap:15px; flex-wrap:wrap; margin-bottom:15px;">
<div style="flex:1; min-width:260px; background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:8px; padding:15px; position:relative;">
<h5 style="color:#C084FC !important; margin:0 0 10px 0; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:4px; font-size:0.9rem;">HQ & Contact</h5>
<p style="margin:4px 0; font-size:0.85rem; color:#E2E8F0;"><strong>Name:</strong> {active_item.get('company_name')}</p>
<p style="margin:4px 0; font-size:0.85rem; color:#E2E8F0;"><strong>Location:</strong> {active_item.get('address') or 'Not Specified'}</p>
<p style="margin:4px 0; font-size:0.85rem; color:#E2E8F0;"><strong>Phone:</strong> {active_item.get('mobile_number') or 'Not Specified'}</p>
<p style="margin:4px 0; font-size:0.85rem; color:#E2E8F0;"><strong>Emails Discovered:</strong> {", ".join(active_item.get('mail', [])) or 'None'}</p>
</div>
<div style="flex:1; min-width:260px; background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:8px; padding:15px;">
<h5 style="color:#C084FC !important; margin:0 0 10px 0; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:4px; font-size:0.9rem;">Strategic Positioning</h5>
<p style="margin:4px 0; font-size:0.85rem; color:#E2E8F0;"><strong>Key Services:</strong> {active_item.get('core_service')}</p>
<p style="margin:4px 0; font-size:0.85rem; color:#E2E8F0;"><strong>Ideal Audience:</strong> {active_item.get('target_customer')}</p>
<p style="margin:4px 0; font-size:0.85rem; color:#E2E8F0;"><strong>Key Problems Solved:</strong> {active_item.get('probable_pain_point')}</p>
</div>
<div style="flex:1; min-width:260px; background:rgba(255,255,255,0.01); border:1px solid rgba(255,255,255,0.04); border-radius:8px; padding:15px; display:flex; flex-direction:column; justify-content:space-between;">
<div>
<h5 style="color:#EC4899 !important; margin:0 0 10px 0; border-bottom:1px solid rgba(255,255,255,0.06); padding-bottom:4px; font-size:0.9rem;">Outreach Hook</h5>
<div class="outreach-quote-box" style="font-size:0.85rem; padding:10px 14px;">
"{active_item.get('outreach_opener')}"
</div>
</div>
</div>
</div>
</div>
""")
                if st.button("✕ Close Active Details", key="close_active_details_pnl"):
                    st.session_state["active_lead_details_id"] = None
                    st.rerun()
        
        # Lead Cards (Beautiful grid layout!)
        with subtab_cards:
            # Displays exactly 3 cards in a row side-by-side!
            for i in range(0, len(filtered_companies), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(filtered_companies):
                        item = filtered_companies[i + j]
                        logo_url = f"https://logo.clearbit.com/{item.get('website_name')}"
                        
                        # Set custom properties exactly matching screenshot layout
                        industry_tag = "SaaS / Automation"
                        bg_logo = "#FFFFFF"
                        
                        if "dhl" in item.get("website_name", ""):
                            industry_tag = "Logistics & Supply Chain"
                            bg_logo = "#FFCC00"
                            if "Global" in item.get("company_name", ""):
                                display_name = "DHL - Global Logistics"
                            else:
                                display_name = "DHL (DHL)"
                        elif "fireflies" in item.get("website_name", ""):
                            industry_tag = "SaaS / Automation"
                            bg_logo = "#0F172A"
                            display_name = "Fireflies.ai (Fireflies.ai)"
                        elif "zapier" in item.get("website_name", ""):
                            industry_tag = "SaaS / Automation"
                            bg_logo = "#FFFFFF"
                            display_name = "Zapier (Zapier)"
                        else:
                            display_name = f"{item.get('company_name')} ({item.get('company_name')})"
                            
                        stem_name = "dhl.com" if "dhl" in item.get("website_name", "") else item.get("website_name").split(".")[0]
                        
                        with cols[j]:
                            render_html(f"""
<div class="lead-card-box">
<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px;">
<span style="font-size:1.1rem; font-weight:700; color:#FFFFFF; font-family:'Outfit',sans-serif; text-shadow:0 2px 4px rgba(0,0,0,0.4);">{display_name}</span>
<span style="background:rgba(52,211,153,0.08); color:#34D399; font-size:0.55rem; font-weight:700; border-radius:3px; padding:1px 6px; text-transform:uppercase; border:1px solid rgba(52,211,153,0.25);">Analyzed</span>
</div>
<p style="margin:0 0 10px 0; color:#C084FC; font-size:0.8rem; font-weight:500;">{stem_name}</p>
<div style="background:rgba(99,102,241,0.07); border:1px solid rgba(99,102,241,0.15); border-radius:4px; padding:4px 8px; font-size:0.75rem; color:#EC4899; font-weight:600; display:inline-block; margin-bottom:12px; font-family:'Outfit',sans-serif;">
{industry_tag}
</div>
<p style="margin:4px 0 12px 0; font-size:0.8rem; color:#94A3B8; display:flex; align-items:center; gap:6px;">
<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#C084FC" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
{item.get('address') or 'Bonn, Germany'}
</p>
<div style="height:1px; background:rgba(255,255,255,0.04); margin-bottom:10px;"></div>
<p style="margin: 4px 0; font-size:0.8rem; color:#94A3B8;">Emails Found &nbsp;<span style="background:rgba(255,255,255,0.03); color:#E2E8F0; padding:2px 8px; border-radius:4px; font-size:0.75rem; font-weight:600; border:1px solid rgba(255,255,255,0.08);">{len(item.get('mail', []))}</span></p>
<p style="margin: 6px 0; font-size:0.8rem; color:#94A3B8;">Phone &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#64748B;">{item.get('mobile_number') or 'Not Specified'}</span></p>
<p style="margin: 6px 0; font-size:0.8rem; color:#94A3B8;">Domain &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span style="color:#C084FC; text-decoration:none;">{item.get('website_name')}</span></p>
<div style="height:15px;"></div>
</div>
""")
                            
                            # Render standard details details trigger button inside layout grid
                            if st.button("View Details ❯", key=f"dtl_b_{item['id']}_grid", use_container_width=True):
                                st.session_state["active_lead_details_id"] = item['id']
                                st.rerun()
                            st.markdown("<div style='height:15px;'></div>", unsafe_allow_html=True)
                            
        # Table Sub-Tab
        with subtab_table:
            if not df_export.empty:
                cols_to_show = ["company_name", "website_name", "mobile_number", "mail", "core_service", "target_customer"]
                st.dataframe(df_export[cols_to_show], use_container_width=True)
                
        # JSON Sub-Tab
        with subtab_json:
            st.json(filtered_companies)

# ----------------- HACKATHON FOOTER -----------------
render_html("""
<div class="saas-footer">
    © 2026 Corporate Intelligence Engine • AI-Powered Prospect Research • Built for Hackathons 💙
</div>
""")
