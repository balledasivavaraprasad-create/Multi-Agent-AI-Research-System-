from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv
from urllib.parse import urlparse
import re
from datetime import datetime

load_dotenv()

def get_domain_tier_score(target_hostname: str):
    if any(suffix in target_hostname for suffix in [".gov", ".gov.in", ".gov.uk"]):
        return 10.0, "Government Primary Source (.gov)"
    if any(suffix in target_hostname for suffix in [".edu", ".ac.in", ".edu.cn"]):
        return 9.0, "Academic Institution (.edu)"
    
    academic_repositories = [
        "arxiv.org", "sciencedirect.com", "springer.com", "nature.com",
        "pubmed", "ncbi.nlm.nih.gov", "researchgate.net", "ieee.org", "doi.org"
    ]
    if any(domain in target_hostname for domain in academic_repositories):
        return 9.0, "Peer-Reviewed Scientific Repository"
        
    reputable_news_outlets = [
        "reuters.com", "bloomberg.com", "bbc.com", "bbc.co.uk",
        "nytimes.com", "theguardian.com", "economist.com", "wsj.com"
    ]
    if any(domain in target_hostname for domain in reputable_news_outlets):
        return 8.0, "Major News Organization"
        
    if "wikipedia.org" in target_hostname:
        return 7.0, "Community Encyclopedia (Wikipedia)"
        
    open_blog_platforms = ["medium.com", "blogspot.com", "wordpress.com", "substack.com"]
    if any(domain in target_hostname for domain in open_blog_platforms):
        return 5.0, "Self-Published Blog / Platform"
        
    return 4.0, "General Web Content"

def get_source_trust_score(url: str, snippet: str = "", outbound_links: list = None, publish_date: str = None, domain_frequency: int = 1) -> dict:
    try:
        parsed_url_components = urlparse(url)
        sanitized_hostname = parsed_url_components.netloc.lower()
        if sanitized_hostname.startswith("www."):
            sanitized_hostname = sanitized_hostname[4:]
            
        domain_tier_score, domain_classification_label = get_domain_tier_score(sanitized_hostname)
        
        recency_score_value = 7.0
        recency_description_label = "Date Not Specified (Neutral)"
        reference_current_year = 2026
        
        combined_text_corpus = f"{publish_date or ''} {snippet or ''}"
        extracted_year_matches = re.findall(r'\b(20[0-2][0-9])\b', combined_text_corpus)
        if extracted_year_matches:
            most_recent_extracted_year = max(int(y) for y in extracted_year_matches if int(y) <= reference_current_year)
            content_age_years = reference_current_year - most_recent_extracted_year
            if content_age_years <= 1:
                recency_score_value = 10.0
                recency_description_label = f"Recent ({most_recent_extracted_year}, <= 1 year old)"
            elif content_age_years == 2:
                recency_score_value = 8.0
                recency_description_label = f"Moderately Recent ({most_recent_extracted_year}, 2 years old)"
            else:
                recency_score_value = 5.0
                recency_description_label = f"Aged Content ({most_recent_extracted_year}, >2 years old)"
                
        if domain_frequency >= 3:
            corroboration_score_value = 10.0
            corroboration_description_label = f"High Corroboration ({domain_frequency}+ sources match)"
        elif domain_frequency == 2:
            corroboration_score_value = 8.0
            corroboration_description_label = "Moderate Corroboration (2 sources match)"
        else:
            corroboration_score_value = 6.0
            corroboration_description_label = "Single Domain Reference"
            
        detected_primary_citation_count = 0
        searchable_citation_text = " ".join(outbound_links or []) + " " + snippet
        primary_academic_patterns = [r'\.gov\b', r'\.edu\b', r'arxiv\.org', r'doi\.org', r'ncbi\.nlm\.nih', r'ieee\.org']
        for pattern in primary_academic_patterns:
            if re.search(pattern, searchable_citation_text, re.IGNORECASE):
                detected_primary_citation_count += 1
                
        if detected_primary_citation_count >= 3:
            citation_score_value = 10.0
            citation_description_label = f"Strong Primary Citations ({detected_primary_citation_count}+ links to .gov/.edu/arxiv)"
        elif detected_primary_citation_count >= 1:
            citation_score_value = 8.0
            citation_description_label = f"Includes Primary Outbound Reference ({detected_primary_citation_count} link)"
        else:
            citation_score_value = 5.0
            citation_description_label = "No Primary Outbound Citations Detected"
            
        composite_trust_score = round(
            (domain_tier_score * 0.40) +
            (recency_score_value * 0.20) +
            (corroboration_score_value * 0.20) +
            (citation_score_value * 0.20),
            1
        )
        
        return {
            "score": composite_trust_score,
            "domain_score": domain_tier_score,
            "recency_score": recency_score_value,
            "corroboration_score": corroboration_score_value,
            "citation_score": citation_score_value,
            "domain": sanitized_hostname,
            "url": url,
            "breakdown": {
                "domain_tier": domain_classification_label,
                "recency": recency_description_label,
                "corroboration": corroboration_description_label,
                "primary_citations": citation_description_label
            }
        }
    except Exception:
        return {
            "score": 4.0,
            "domain_score": 4.0,
            "recency_score": 5.0,
            "corroboration_score": 5.0,
            "citation_score": 5.0,
            "domain": "unknown",
            "url": url,
            "breakdown": {
                "domain_tier": "Unparsed Domain",
                "recency": "Unknown",
                "corroboration": "None",
                "primary_citations": "None"
            }
        }

@tool
def web_search(query: str) -> str:
    """Search the web for recent and reliable information on a topic. Returns Titles, URLs and snippets."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        return "Error: TAVILY_API_KEY is not set in the environment variables."
    tavily_client_instance = TavilyClient(api_key=tavily_api_key)
    query_string = query.strip()
    if len(query_string) > 390:
        query_string = query_string[:390]
    try:
        search_response = tavily_client_instance.search(query=query_string, max_results=5)
    except Exception as exc:
        return f"Warning: Web search failed for query '{query_string}': {str(exc)}"
    formatted_results_list = []
    for item in search_response.get("results", []):
        formatted_results_list.append(
            f"Title : {item.get('title', '')}\nURL : {item.get('url', '')}\nSnippet : {item.get('content', '')[:300]}\n"
        )
    return "\n-----\n".join(formatted_results_list)

@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper understanding."""
    try:
        http_response = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        document_soup = BeautifulSoup(http_response.text, "html.parser")
        for intrusive_tag in document_soup(["script", "style", "nav", "footer"]):
            intrusive_tag.decompose()
        return document_soup.get_text(separator=" ", strip=True)[:3000]
    except Exception as exc:
        return f"Could not scrape URL : {str(exc)}"
