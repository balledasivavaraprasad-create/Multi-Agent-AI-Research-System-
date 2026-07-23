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

def get_domain_tier_score(netloc: str):
    if any(suffix in netloc for suffix in [".gov", ".gov.in", ".gov.uk"]):
        return 10.0, "Government Primary Source (.gov)"
    if any(suffix in netloc for suffix in [".edu", ".ac.in", ".edu.cn"]):
        return 9.0, "Academic Institution (.edu)"
    
    high_trust_domains = [
        "arxiv.org", "sciencedirect.com", "springer.com", "nature.com",
        "pubmed", "ncbi.nlm.nih.gov", "researchgate.net", "ieee.org", "doi.org"
    ]
    if any(domain in netloc for domain in high_trust_domains):
        return 9.0, "Peer-Reviewed Scientific Repository"
        
    news_domains = [
        "reuters.com", "bloomberg.com", "bbc.com", "bbc.co.uk",
        "nytimes.com", "theguardian.com", "economist.com", "wsj.com"
    ]
    if any(domain in netloc for domain in news_domains):
        return 8.0, "Major News Organization"
        
    if "wikipedia.org" in netloc:
        return 7.0, "Community Encyclopedia (Wikipedia)"
        
    blog_platforms = ["medium.com", "blogspot.com", "wordpress.com", "substack.com"]
    if any(domain in netloc for domain in blog_platforms):
        return 5.0, "Self-Published Blog / Platform"
        
    return 4.0, "General Web Content"

def get_source_trust_score(url: str, snippet: str = "", outbound_links: list = None, publish_date: str = None, domain_frequency: int = 1) -> dict:
    """
    Multi-factor source trust scoring:
    - Domain Tier (40%): High credibility domains (.gov, .edu, arxiv, major news)
    - Recency (20%): Freshness decay for content older than 2 years
    - Cross-corroboration (20%): Boost for topics reported across multiple independent domains
    - Primary Citation Check (20%): Outbound links/references to .gov, .edu, arxiv, doi
    """
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
            
        domain_score, domain_label = get_domain_tier_score(netloc)
        
        # 1. Recency Score (20%)
        recency_score = 7.0
        recency_label = "Date Not Specified (Neutral)"
        current_year = 2026
        
        target_text = f"{publish_date or ''} {snippet or ''}"
        year_matches = re.findall(r'\b(20[0-2][0-9])\b', target_text)
        if year_matches:
            most_recent_year = max(int(y) for y in year_matches if int(y) <= current_year)
            age = current_year - most_recent_year
            if age <= 1:
                recency_score = 10.0
                recency_label = f"Recent ({most_recent_year}, <= 1 year old)"
            elif age == 2:
                recency_score = 8.0
                recency_label = f"Moderately Recent ({most_recent_year}, 2 years old)"
            else:
                recency_score = 5.0
                recency_label = f"Aged Content ({most_recent_year}, >2 years old)"
                
        # 2. Cross-Corroboration Score (20%)
        if domain_frequency >= 3:
            corroboration_score = 10.0
            corroboration_label = f"High Corroboration ({domain_frequency}+ sources match)"
        elif domain_frequency == 2:
            corroboration_score = 8.0
            corroboration_label = "Moderate Corroboration (2 sources match)"
        else:
            corroboration_score = 6.0
            corroboration_label = "Single Domain Reference"
            
        # 3. Citation / Primary Reference Check (20%)
        citation_count = 0
        search_target = " ".join(outbound_links or []) + " " + snippet
        primary_patterns = [r'\.gov\b', r'\.edu\b', r'arxiv\.org', r'doi\.org', r'ncbi\.nlm\.nih', r'ieee\.org']
        for pat in primary_patterns:
            if re.search(pat, search_target, re.IGNORECASE):
                citation_count += 1
                
        if citation_count >= 3:
            citation_score = 10.0
            citation_label = f"Strong Primary Citations ({citation_count}+ links to .gov/.edu/arxiv)"
        elif citation_count >= 1:
            citation_score = 8.0
            citation_label = f"Includes Primary Outbound Reference ({citation_count} link)"
        else:
            citation_score = 5.0
            citation_label = "No Primary Outbound Citations Detected"
            
        overall_score = round(
            (domain_score * 0.40) +
            (recency_score * 0.20) +
            (corroboration_score * 0.20) +
            (citation_score * 0.20),
            1
        )
        
        return {
            "score": overall_score,
            "domain_score": domain_score,
            "recency_score": recency_score,
            "corroboration_score": corroboration_score,
            "citation_score": citation_score,
            "domain": netloc,
            "url": url,
            "breakdown": {
                "domain_tier": domain_label,
                "recency": recency_label,
                "corroboration": corroboration_label,
                "primary_citations": citation_label
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
    tavily_key = os.getenv("TAVILY_API_KEY")
    if not tavily_key:
        return "Error: TAVILY_API_KEY is not set in the environment variables."
    tavily = TavilyClient(api_key=tavily_key)
    query = query.strip()
    if len(query) > 390:
        query = query[:390]
    try:
        results = tavily.search(query=query, max_results=5)
    except Exception as e:
        return f"Warning: Web search failed for query '{query}': {str(e)}"
    out = []
    for r in results.get("results", []):
        out.append(
            f"Title : {r.get('title', '')}\nURL : {r.get('url', '')}\nSnippet : {r.get('content', '')[:300]}\n"
        )
    return "\n-----\n".join(out)

@tool
def scrape_url(url: str) -> str:
    """Scrape and return clean text content from a given URL for deeper understanding."""
    try:
        resp = requests.get(url, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        return soup.get_text(separator=" ", strip=True)[:3000]
    except Exception as e:
        return f"Could not scrape URL : {str(e)}"

