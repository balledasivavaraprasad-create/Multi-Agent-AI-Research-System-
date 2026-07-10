from langchain.tools import tool
import requests
from bs4 import BeautifulSoup
from tavily import TavilyClient
import os
from dotenv import load_dotenv
from urllib.parse import urlparse

load_dotenv()

def get_source_trust_score(url):
    try:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        if netloc.startswith("www."):
            netloc = netloc[4:]
        if any(suffix in netloc for suffix in [".gov", ".gov.in", ".gov.uk"]):
            return 10
        if any(suffix in netloc for suffix in [".edu", ".ac.in", ".edu.cn"]):
            return 9
        high_trust_domains = [
            "arxiv.org", "sciencedirect.com", "springer.com", "nature.com",
            "pubmed", "ncbi.nlm.nih.gov", "researchgate.net", "ieee.org"
        ]
        if any(domain in netloc for domain in high_trust_domains):
            return 9
        news_domains = [
            "reuters.com", "bloomberg.com", "bbc.com", "bbc.co.uk",
            "nytimes.com", "theguardian.com", "economist.com", "wsj.com"
        ]
        if any(domain in netloc for domain in news_domains):
            return 8
        if "wikipedia.org" in netloc:
            return 7
        blog_platforms = ["medium.com", "blogspot.com", "wordpress.com", "substack.com"]
        if any(domain in netloc for domain in blog_platforms):
            return 5
        return 4
    except:
        return 3

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
