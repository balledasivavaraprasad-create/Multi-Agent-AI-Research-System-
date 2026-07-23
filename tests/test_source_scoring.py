import pytest
import sys
import os

# Add root project directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import get_source_trust_score, get_domain_tier_score

def test_domain_tier_scores():
    assert get_domain_tier_score("cdc.gov")[0] == 10.0
    assert get_domain_tier_score("mit.edu")[0] == 9.0
    assert get_domain_tier_score("arxiv.org")[0] == 9.0
    assert get_domain_tier_score("reuters.com")[0] == 8.0
    assert get_domain_tier_score("wikipedia.org")[0] == 7.0
    assert get_domain_tier_score("medium.com")[0] == 5.0
    assert get_domain_tier_score("unknown-example-blog.io")[0] == 4.0

def test_multi_factor_scoring_breakdown():
    result = get_source_trust_score(
        url="https://www.reuters.com/technology/ai-update-2025",
        snippet="Published Jan 2025. According to studies on arxiv.org and cdc.gov...",
        domain_frequency=3
    )
    
    assert isinstance(result, dict)
    assert "score" in result
    assert "breakdown" in result
    assert result["domain_score"] == 8.0
    assert result["recency_score"] == 10.0  # 2025 (<= 1 yr)
    assert result["corroboration_score"] == 10.0  # 3+ sources
    assert result["citation_score"] == 8.0  # 2 primary links (arxiv.org & cdc.gov) found
    assert result["score"] >= 8.0


def test_aged_content_decay():
    result = get_source_trust_score(
        url="https://example.com/article",
        snippet="Published back in 2020 on general topics.",
        domain_frequency=1
    )
    assert result["recency_score"] == 5.0  # >2 years old decay

def test_unparsed_url_fallback():
    result = get_source_trust_score("not_a_valid_url")
    assert isinstance(result, dict)
    assert "score" in result
    assert result["score"] >= 3.0
